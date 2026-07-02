import { useState, useMemo } from 'react';
import { LocalDataItem } from '../types';
import { downloadData, deleteLocalData, getLocalData } from '../api';

interface DataManagementProps {
  localData: LocalDataItem[];
  onRefresh: () => void;
  isDemoMode?: boolean;
}

const SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT', 'LTC/USDT', 'TRX/USDT', 'ATOM/USDT', 'NEAR/USDT'];
const TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d'];

const TF_LABELS: Record<string, string> = {
  '5m': '5分钟线',
  '15m': '15分钟线',
  '30m': '30分钟线',
  '1h': '1小时线',
  '4h': '4小时线',
  '1d': '日线',
};

const RAW_BASE = 'https://raw.githubusercontent.com/Miku-cy/bb-regression-strategy/main/data/';

function formatSize(kb: number): string {
  if (kb >= 1024) return (kb / 1024).toFixed(1) + 'MB';
  return kb.toFixed(0) + 'KB';
}

export default function DataManagement({ localData, onRefresh, isDemoMode }: DataManagementProps) {
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [days, setDays] = useState(365);
  const [downloading, setDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState('');
  const [filterSymbol, setFilterSymbol] = useState('ALL');

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadStatus(`正在下载 ${symbol} ${timeframe}...`);
    try {
      const result = await downloadData(symbol, timeframe, days);
      setDownloadStatus(`✓ 下载完成: ${result.rows} 条数据 (${result.start} ~ ${result.end})`);
      onRefresh();
    } catch (e: any) {
      setDownloadStatus(`✗ 下载失败: ${e.response?.data?.detail || e.message}`);
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async (sym: string, tf: string) => {
    if (!confirm(`确认删除 ${sym} ${tf} 的本地数据？`)) return;
    await deleteLocalData(sym, tf);
    onRefresh();
  };

  // CSV演示模式：显示所有K线数据下载列表 + 支持按币种筛选
  const filteredData = useMemo(() => {
    if (filterSymbol === 'ALL') return localData;
    return localData.filter(d => d.symbol === filterSymbol);
  }, [localData, filterSymbol]);

  // 按币种分组统计
  const symbolStats = useMemo(() => {
    const map = new Map<string, number>();
    localData.forEach(d => map.set(d.symbol, (map.get(d.symbol) || 0) + 1));
    return Array.from(map.entries()).sort();
  }, [localData]);

  if (isDemoMode) {
    return (
      <div className="card" style={{ padding: '16px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px' }}>数据管理</h3>
        <div style={{ fontSize: '11px', color: 'var(--info)', marginBottom: '16px', padding: '8px 12px', background: 'var(--info-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--info)' }}>
          📊 CSV演示模式 · 共 {localData.length} 个K线数据文件，覆盖 {symbolStats.length} 个币种，点击下载后可用于本地回测
        </div>

        {/* 币种筛选 */}
        <div style={{ marginBottom: '12px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setFilterSymbol('ALL')}
            style={{
              padding: '4px 10px', fontSize: '11px', fontWeight: 600, cursor: 'pointer',
              borderRadius: 'var(--radius-sm)', border: '1px solid',
              background: filterSymbol === 'ALL' ? 'var(--primary)' : 'transparent',
              color: filterSymbol === 'ALL' ? 'white' : 'var(--text-secondary)',
              borderColor: filterSymbol === 'ALL' ? 'var(--primary)' : 'var(--border)',
            }}
          >
            全部 ({localData.length})
          </button>
          {symbolStats.map(([sym, count]) => (
            <button
              key={sym}
              onClick={() => setFilterSymbol(sym)}
              style={{
                padding: '4px 10px', fontSize: '11px', fontWeight: 600, cursor: 'pointer',
                borderRadius: 'var(--radius-sm)', border: '1px solid',
                background: filterSymbol === sym ? 'var(--primary)' : 'transparent',
                color: filterSymbol === sym ? 'white' : 'var(--text-secondary)',
                borderColor: filterSymbol === sym ? 'var(--primary)' : 'var(--border)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {sym} ({count})
            </button>
          ))}
        </div>

        {/* K线数据下载列表 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '16px' }}>
          {filteredData.map((item, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 12px', background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-light)',
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                  {item.symbol} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>{TF_LABELS[item.timeframe] || item.timeframe}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {item.rows ? `${item.rows.toLocaleString()} 行 · ` : ''}{formatSize(item.size_kb)}
                </div>
              </div>
              <a
                href={RAW_BASE + item.file}
                download={item.file}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: '6px 14px', fontSize: '12px', fontWeight: 600, color: 'white',
                  background: 'var(--primary)', borderRadius: 'var(--radius-sm)',
                  textDecoration: 'none', whiteSpace: 'nowrap',
                }}
              >
                ⬇ 下载
              </a>
            </div>
          ))}
          {filteredData.length === 0 && (
            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '12px' }}>
              暂无数据
            </div>
          )}
        </div>

        {/* 数据格式说明 */}
        <div style={{
          padding: '12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)',
          fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.8,
        }}>
          <div style={{ fontWeight: 600, marginBottom: '6px', color: 'var(--text-primary)' }}>📋 CSV数据格式</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', background: 'var(--bg-card)', padding: '6px 8px', borderRadius: '4px', marginBottom: '6px' }}>
            timestamp,datetime,open,high,low,close,volume
          </div>
          <div>• <strong>timestamp</strong>: 毫秒级时间戳</div>
          <div>• <strong>datetime</strong>: 格式化时间 (YYYY-MM-DD HH:MM:SS)</div>
          <div>• <strong>open/high/low/close</strong>: 开高低收价格</div>
          <div>• <strong>volume</strong>: 成交量</div>
          <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-light)' }}>
            💡 本地部署后，将下载的CSV放入 <code style={{ background: 'var(--bg-card)', padding: '1px 4px', borderRadius: '3px' }}>data/</code> 目录即可用于回测
          </div>
        </div>
      </div>
    );
  }

  // 本地部署模式：支持下载/删除
  return (
    <div className="card" style={{ padding: '16px' }}>
      <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>数据管理</h3>

      {/* 下载区域 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '8px', marginBottom: '12px' }}>
        <select className="select" value={symbol} onChange={e => setSymbol(e.target.value)}>
          {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select className="select" value={timeframe} onChange={e => setTimeframe(e.target.value)}>
          {TIMEFRAMES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="select" value={days} onChange={e => setDays(parseInt(e.target.value))}>
          <option value={90}>90天</option>
          <option value={180}>180天</option>
          <option value={365}>1年</option>
          <option value={730}>2年</option>
        </select>
        <button className="btn btn-primary" onClick={handleDownload} disabled={downloading} style={{ whiteSpace: 'nowrap' }}>
          {downloading ? <><span className="spinner" /> 下载中</> : '⬇ 下载'}
        </button>
      </div>

      {downloadStatus && (
        <div style={{
          padding: '8px 12px', marginBottom: '12px', borderRadius: 'var(--radius-sm)',
          background: downloadStatus.startsWith('✓') ? 'var(--success-bg)' : downloadStatus.startsWith('✗') ? 'var(--danger-bg)' : 'var(--info-bg)',
          color: downloadStatus.startsWith('✓') ? 'var(--success)' : downloadStatus.startsWith('✗') ? 'var(--danger)' : 'var(--info)',
          fontSize: '12px',
        }}>
          {downloadStatus}
        </div>
      )}

      {/* 本地数据列表 */}
      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {localData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '12px' }}>
            暂无本地数据，请先下载
          </div>
        ) : (
          <table style={{ width: '100%', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>交易对</th>
                <th style={{ padding: '6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>周期</th>
                <th style={{ padding: '6px', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>大小</th>
                <th style={{ padding: '6px', textAlign: 'center', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {localData.map((d, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                  <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>{d.symbol}</td>
                  <td style={{ padding: '6px' }}>{d.timeframe}</td>
                  <td style={{ padding: '6px', textAlign: 'right', color: 'var(--text-muted)' }}>{formatSize(d.size_kb)}</td>
                  <td style={{ padding: '6px', textAlign: 'center' }}>
                    <button
                      onClick={() => handleDelete(d.symbol, d.timeframe)}
                      style={{ border: 'none', background: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '12px' }}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
