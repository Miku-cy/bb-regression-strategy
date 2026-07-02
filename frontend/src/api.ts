import axios from 'axios';
import { StrategyParams, BacktestResponse, LocalDataItem } from './types';

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
});

// ===== CSV演示模式 =====
// 当后端不可用时（如GitHub Pages静态部署），读取本地CSV数据模拟API响应
const CSV_BASE = import.meta.env.BASE_URL + 'data/';

let _useCsvMode: boolean | null = null;

async function isCsvMode(): Promise<boolean> {
  if (_useCsvMode !== null) return _useCsvMode;
  try {
    await api.get('/health', { timeout: 2000 });
    _useCsvMode = false;
  } catch {
    _useCsvMode = true;
  }
  return _useCsvMode;
}

// CSV解析器
function parseCSV(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (lines.length === 0) return { headers: [], rows: [] };

  const parseLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        result.push(current);
        current = '';
      } else {
        current += ch;
      }
    }
    result.push(current);
    return result;
  };

  const headers = parseLine(lines[0]);
  const rows = lines.slice(1).map(line => {
    const values = parseLine(line);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => { row[h] = values[i] || ''; });
    return row;
  });
  return { headers, rows };
}

async function fetchCsv(filename: string): Promise<Record<string, string>[]> {
  const resp = await fetch(CSV_BASE + filename);
  if (!resp.ok) throw new Error(`CSV文件加载失败: ${filename}`);
  const text = await resp.text();
  const { rows } = parseCSV(text);
  return rows;
}

// 类型转换辅助
const toNum = (v: string, d = 0): number => {
  const n = parseFloat(v);
  return isNaN(n) ? d : n;
};
const toBool = (v: string): boolean => v === 'true' || v === '1' || v === 'True';

// 从CSV构建BacktestResponse
// 文件命名规则:
//   5m小周期(向后兼容): backtest_stats_{SYM}.csv / leverage_10.0x_stats_{SYM}_lev10.0x.csv
//   1m小周期: backtest_stats_{SYM}_1m.csv / leverage_10.0x_stats_{SYM}_1m_lev10.0x.csv
// SYM = symbol.replace('/', '_')，例如 BTC/USDT -> BTC_USDT
async function buildBacktestFromCsv(params: StrategyParams): Promise<BacktestResponse> {
  const symFile = params.symbol.replace('/', '_');

  // 小周期后缀：5m保持空(向后兼容)，1m加 _1m
  const smSuffix = params.small_timeframe === '1m' ? '_1m' : '';

  // 根据是否启用杠杆选择文件前缀
  let statsFile: string, equityFile: string, drawdownFile: string, tradesFile: string;
  let reportFile: string, eventsFile: string;

  if (params.use_leverage) {
    const lev = params.leverage || 10;
    const levStr = lev.toFixed(1);
    const p = `leverage_${levStr}x_`;
    const s = `${smSuffix}_lev${levStr}`;
    statsFile = `${p}stats_${symFile}${s}.csv`;
    equityFile = `${p}equity_${symFile}${s}.csv`;
    drawdownFile = `${p}drawdown_${symFile}${s}.csv`;
    tradesFile = `${p}trades_${symFile}${s}.csv`;
    reportFile = `leverage_report_${symFile}${s}.json`;
    eventsFile = `leverage_events_${symFile}${s}.csv`;
  } else {
    statsFile = `backtest_stats_${symFile}${smSuffix}.csv`;
    equityFile = `backtest_equity_${symFile}${smSuffix}.csv`;
    drawdownFile = `backtest_drawdown_${symFile}${smSuffix}.csv`;
    tradesFile = `backtest_trades_${symFile}${smSuffix}.csv`;
    reportFile = '';
    eventsFile = '';
  }

  // 并行加载所有CSV
  const [statsRows, equityRows, drawdownRows, tradeRows] = await Promise.all([
    fetchCsv(statsFile),
    fetchCsv(equityFile),
    fetchCsv(drawdownFile),
    fetchCsv(tradesFile),
  ]);

  const s = statsRows[0] || {};
  const result = {
    symbol: s.symbol || params.symbol,
    start_date: s.start_date || '',
    end_date: s.end_date || '',
    initial_capital: toNum(s.initial_capital, 100000),
    final_capital: toNum(s.final_capital),
    total_return: toNum(s.total_return),
    total_pnl: toNum(s.total_pnl),
    annual_return: toNum(s.annual_return),
    total_trades: toNum(s.total_trades, 0),
    win_trades: toNum(s.win_trades, 0),
    loss_trades: toNum(s.loss_trades, 0),
    win_rate: toNum(s.win_rate),
    avg_win: toNum(s.avg_win),
    avg_loss: toNum(s.avg_loss),
    profit_factor: toNum(s.profit_factor),
    max_win: toNum(s.max_win),
    max_loss: toNum(s.max_loss),
    avg_rr: toNum(s.avg_rr),
    max_drawdown: toNum(s.max_drawdown),
    sharpe_ratio: toNum(s.sharpe_ratio),
    sortino_ratio: toNum(s.sortino_ratio),
    avg_holding_bars: toNum(s.avg_holding_bars),
    long_trades: toNum(s.long_trades, 0),
    short_trades: toNum(s.short_trades, 0),
    use_leverage: toBool(s.use_leverage),
    leverage: toNum(s.leverage, 1),
    liquidation_count: toNum(s.liquidation_count, 0),
    total_funding_fees: toNum(s.total_funding_fees),
    total_liquidation_fees: toNum(s.total_liquidation_fees, 0),
    max_position_value: toNum(s.max_position_value),
    avg_margin_used: toNum(s.avg_margin_used, 0),
    max_margin_used: toNum(s.max_margin_used, 0),
    leverage_amplification: toNum(s.leverage_amplification, 1),
    risk_per_trade_pct: toNum(s.risk_per_trade_pct),
    equity_curve: equityRows.map(r => ({ datetime: r.datetime, equity: toNum(r.equity) })),
    drawdown_curve: drawdownRows.map(r => ({ datetime: r.datetime, drawdown: toNum(r.drawdown) })),
    trades: tradeRows.map(t => ({
      entry_time: t.entry_time,
      exit_time: t.exit_time || null,
      entry_price: toNum(t.entry_price),
      exit_price: t.exit_price ? toNum(t.exit_price) : null,
      direction: (t.side || t.direction) as 'long' | 'short',
      size: toNum(t.size),
      stop_loss: toNum(t.stop_loss, 0),
      initial_stop: toNum(t.initial_stop, 0),
      take_profit_1: toNum(t.take_profit_1, 0),
      pnl: toNum(t.pnl),
      pnl_pct: toNum(t.return_pct || t.pnl_pct),
      rr: toNum(t.rr, 0),
      exit_reason: t.exit_reason || '',
      tp1_hit: toBool(t.tp1_hit),
      breakeven_set: toBool(t.breakeven_set),
      signal_strength: toNum(t.signal_strength, 1),
      leverage: toNum(t.leverage, 1),
      margin: toNum(t.margin),
      position_value: toNum(t.position_value, 0),
      liquidation_price: toNum(t.liquidation_price, 0),
      funding_fees: toNum(t.funding_fees, 0),
      liquidation_fee: toNum(t.liquidation_fee, 0),
      is_liquidated: toBool(t.is_liquidated),
      margin_ratio_at_entry: toNum(t.margin_ratio_at_entry, 0),
      mmr_tier: toNum(t.mmr_tier, 1),
    })),
  };

  // 尝试加载杠杆报告（JSON格式）
  let leverageReport = null;
  if (params.use_leverage && reportFile) {
    try {
      const resp = await fetch(CSV_BASE + reportFile);
      if (resp.ok) {
        leverageReport = await resp.json();
      }
    } catch {
      // 杠杆报告加载失败，忽略
    }
  }

  return {
    success: true,
    result,
    charts: {},
    leverage_report: leverageReport,
  };
}

// ===== 公共API =====

export async function getSymbols(): Promise<string[]> {
  if (await isCsvMode()) {
    return ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT'];
  }
  const { data } = await api.get('/symbols');
  return data.symbols;
}

export async function getTimeframes(): Promise<string[]> {
  if (await isCsvMode()) return ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];
  const { data } = await api.get('/timeframes');
  return data.timeframes;
}

export async function getLocalData(): Promise<LocalDataItem[]> {
  if (await isCsvMode()) {
    // CSV演示模式：从 kline_manifest.json 加载所有可用的K线数据
    try {
      const resp = await fetch(CSV_BASE + 'kline_manifest.json');
      if (resp.ok) {
        const items = await resp.json();
        return items.map((item: any) => ({
          symbol: item.symbol,
          timeframe: item.timeframe,
          file: item.file,
          size_kb: item.size_kb,
          rows: item.rows,
        }));
      }
    } catch {
      // 忽略
    }
    return [];
  }
  const { data } = await api.get('/local-data');
  return data.data;
}

export async function downloadData(symbol: string, timeframe: string, days: number) {
  if (await isCsvMode()) {
    throw new Error('CSV演示模式下不支持下载数据。请部署后端服务以使用完整功能。');
  }
  const { data } = await api.post('/download', { symbol, timeframe, days });
  return data;
}

export async function deleteLocalData(symbol: string, timeframe: string) {
  if (await isCsvMode()) {
    throw new Error('CSV演示模式下不支持删除数据。');
  }
  const { data } = await api.delete(`/local-data/${symbol.replace('/', '_')}/${timeframe}`);
  return data;
}

export async function runBacktest(params: StrategyParams): Promise<BacktestResponse> {
  if (await isCsvMode()) {
    // 模拟延迟
    await new Promise(r => setTimeout(r, 500));
    return buildBacktestFromCsv(params);
  }
  const { data } = await api.post('/backtest', params);
  return data;
}

export async function exportReport(params: StrategyParams) {
  if (await isCsvMode()) {
    throw new Error('CSV演示模式下不支持导出报告图片。请部署后端服务。');
  }
  const { data } = await api.post('/export-report', params);
  return data;
}

export async function getKlines(symbol: string, timeframe: string, days: number = 365) {
  if (await isCsvMode()) {
    throw new Error('CSV演示模式下不支持获取K线数据。');
  }
  const { data } = await api.get(`/klines/${symbol.replace('/', '_')}/${timeframe}`, {
    params: { days }
  });
  return data;
}

export async function checkHealth() {
  if (await isCsvMode()) {
    return { status: 'demo', message: 'CSV演示模式（GitHub Pages静态部署）' };
  }
  const { data } = await api.get('/health');
  return data;
}
