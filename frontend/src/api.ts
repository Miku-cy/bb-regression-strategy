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
async function buildBacktestFromCsv(params: StrategyParams): Promise<BacktestResponse> {
  const prefix = params.use_leverage ? 'leverage' : 'backtest';

  const [statsRows, equityRows, drawdownRows, tradeRows] = await Promise.all([
    fetchCsv(`${prefix}_stats.csv`),
    fetchCsv(`${prefix}_equity.csv`),
    fetchCsv(`${prefix}_drawdown.csv`),
    fetchCsv(`${prefix}_trades.csv`),
  ]);

  const s = statsRows[0];
  const result = {
    symbol: s.symbol || 'BTC/USDT',
    start_date: s.start_date || '',
    end_date: s.end_date || '',
    initial_capital: toNum(s.initial_capital),
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
    total_liquidation_fees: toNum(s.total_liquidation_fees),
    max_position_value: toNum(s.max_position_value),
    avg_margin_used: toNum(s.avg_margin_used),
    max_margin_used: toNum(s.max_margin_used),
    leverage_amplification: toNum(s.leverage_amplification, 1),
    risk_per_trade_pct: toNum(s.risk_per_trade_pct),
    equity_curve: equityRows.map(r => ({ datetime: r.datetime, equity: toNum(r.equity) })),
    drawdown_curve: drawdownRows.map(r => ({ datetime: r.datetime, drawdown: toNum(r.drawdown) })),
    trades: tradeRows.map(t => ({
      entry_time: t.entry_time,
      exit_time: t.exit_time || null,
      entry_price: toNum(t.entry_price),
      exit_price: t.exit_price ? toNum(t.exit_price) : null,
      direction: t.direction as 'long' | 'short',
      size: toNum(t.size),
      stop_loss: toNum(t.stop_loss),
      initial_stop: toNum(t.initial_stop),
      take_profit_1: toNum(t.take_profit_1),
      pnl: toNum(t.pnl),
      pnl_pct: toNum(t.pnl_pct),
      rr: toNum(t.rr),
      exit_reason: t.exit_reason,
      tp1_hit: toBool(t.tp1_hit),
      breakeven_set: toBool(t.breakeven_set),
      signal_strength: toNum(t.signal_strength, 1),
      leverage: toNum(t.leverage, 1),
      margin: toNum(t.margin),
      position_value: toNum(t.position_value),
      liquidation_price: toNum(t.liquidation_price),
      funding_fees: toNum(t.funding_fees),
      liquidation_fee: toNum(t.liquidation_fee),
      is_liquidated: toBool(t.is_liquidated),
      margin_ratio_at_entry: toNum(t.margin_ratio_at_entry),
      mmr_tier: toNum(t.mmr_tier, 1),
    })),
  };

  // 尝试加载杠杆报告
  let leverageReport = null;
  if (params.use_leverage) {
    try {
      const [summaryRows, eventRows, recRows] = await Promise.all([
        fetchCsv('leverage_summary.csv'),
        fetchCsv('leverage_events.csv'),
        fetchCsv('leverage_recommendations.csv'),
      ]);
      const ls = summaryRows[0] || {};
      leverageReport = {
        risk_level: ls.risk_level || '中',
        risk_score: toNum(ls.risk_score),
        max_loss_per_trade_pct: toNum(ls.max_loss_per_trade_pct),
        avg_loss_per_trade_pct: toNum(ls.avg_loss_per_trade_pct),
        liquidation_rate: toNum(ls.liquidation_rate),
        funding_fee_ratio: toNum(ls.funding_fee_ratio),
        margin_utilization: toNum(ls.margin_utilization),
        risk_reward_with_lev: toNum(ls.risk_reward_with_lev),
        events: eventRows.map(e => ({
          severity: e.severity as 'critical' | 'warning' | 'info',
          category: e.category,
          title: e.title,
          description: e.description,
          trade_index: toNum(e.trade_index, -1),
          value: toNum(e.value),
          suggestion: e.suggestion,
        })),
        summary: ls.summary || '',
        recommendations: recRows.map(r => r.recommendation),
      };
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
  if (await isCsvMode()) return ['5m', '15m', '30m', '1h', '4h', '1d'];
  const { data } = await api.get('/timeframes');
  return data.timeframes;
}

export async function getLocalData(): Promise<LocalDataItem[]> {
  if (await isCsvMode()) {
    try {
      const rows = await fetchCsv('local_data.csv');
      return rows.map(r => ({
        symbol: r.symbol,
        timeframe: r.timeframe,
        file: r.file,
        size_kb: toNum(r.size_kb),
      }));
    } catch {
      return [];
    }
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
