import { useState } from 'react';
import { LocalDataItem } from '../types';
import { downloadData, deleteLocalData, getLocalData } from '../api';

interface DataManagementProps {
  localData: LocalDataItem[];
  onRefresh: () => void;
}

const SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT', 'LTC/USDT', 'TRX/USDT', 'ATOM/USDT', 'NEAR/USDT'];
const TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d'];

export default function DataManagement({ localData, onRefresh }: DataManagementProps) {
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [days, setDays] = useState(365);
  const [downloading, setDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState('');

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
          padding: '8px 12px',
          marginBottom: '12px',
          borderRadius: 'var(--radius-sm)',
          background: downloadStatus.startsWith('✓') ? 'var(--success-bg)' : downloadStatus.startsWith('✗') ? 'var(--danger-bg)' : 'var(--info-bg)',
          color: downloadStatus.startsWith('✓') ? 'var(--success)' : downloadStatus.startsWith('✗') ? 'var(--danger)' : 'var(--info)',
          fontSize: '12px',
        }}>
          {downloadStatus}
        </div>
      )}

      {/* 本地数据列表 */}
      <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
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
                  <td style={{ padding: '6px', textAlign: 'right', color: 'var(--text-muted)' }}>{d.size_kb}KB</td>
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
