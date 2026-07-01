import { useState } from 'react';
import { Trade } from '../types';

interface TradeTableProps {
  trades: Trade[];
}

export default function TradeTable({ trades }: TradeTableProps) {
  const [filter, setFilter] = useState<'all' | 'long' | 'short' | 'win' | 'loss'>('all');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const filtered = trades.filter(t => {
    if (filter === 'long') return t.direction === 'long';
    if (filter === 'short') return t.direction === 'short';
    if (filter === 'win') return t.pnl > 0;
    if (filter === 'loss') return t.pnl < 0;
    return true;
  });

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const filters = [
    { key: 'all', label: `全部 (${trades.length})` },
    { key: 'long', label: `多单 (${trades.filter(t => t.direction === 'long').length})` },
    { key: 'short', label: `空单 (${trades.filter(t => t.direction === 'short').length})` },
    { key: 'win', label: `盈利 (${trades.filter(t => t.pnl > 0).length})` },
    { key: 'loss', label: `亏损 (${trades.filter(t => t.pnl < 0).length})` },
  ] as const;

  return (
    <div className="card" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600 }}>交易记录</h3>
        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {filters.map(f => (
            <button
              key={f.key}
              onClick={() => { setFilter(f.key); setPage(0); }}
              style={{
                padding: '4px 10px',
                fontSize: '11px',
                fontWeight: 500,
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                background: filter === f.key ? 'var(--primary)' : 'var(--bg-card)',
                color: filter === f.key ? 'white' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'var(--transition)',
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>#</th>
              <th style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>方向</th>
              <th style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>进场时间</th>
              <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>进场价</th>
              <th style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>出场时间</th>
              <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>出场价</th>
              <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>盈亏</th>
              <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>收益率</th>
              <th style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>出场原因</th>
              <th style={{ padding: '8px 6px', textAlign: 'center', fontWeight: 600, color: 'var(--text-muted)', fontSize: '11px' }}>信号</th>
            </tr>
          </thead>
          <tbody>
            {pageData.map((t, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                <td style={{ padding: '7px 6px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{page * pageSize + i + 1}</td>
                <td style={{ padding: '7px 6px' }}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    background: t.direction === 'long' ? 'var(--success-bg)' : 'var(--danger-bg)',
                    color: t.direction === 'long' ? 'var(--success)' : 'var(--danger)',
                  }}>
                    {t.direction === 'long' ? '多' : '空'}
                  </span>
                </td>
                <td style={{ padding: '7px 6px', color: 'var(--text-secondary)', fontSize: '11px' }}>{t.entry_time ? new Date(t.entry_time).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}</td>
                <td style={{ padding: '7px 6px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{t.entry_price.toFixed(2)}</td>
                <td style={{ padding: '7px 6px', color: 'var(--text-secondary)', fontSize: '11px' }}>{t.exit_time ? new Date(t.exit_time).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}</td>
                <td style={{ padding: '7px 6px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{t.exit_price ? t.exit_price.toFixed(2) : '-'}</td>
                <td style={{ padding: '7px 6px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, color: t.pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}
                </td>
                <td style={{ padding: '7px 6px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: t.pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                  {t.pnl >= 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%
                </td>
                <td style={{ padding: '7px 6px', color: 'var(--text-secondary)', fontSize: '11px' }}>{t.exit_reason}</td>
                <td style={{ padding: '7px 6px', textAlign: 'center' }}>
                  {t.signal_strength === 2 && <span style={{ fontSize: '10px', padding: '1px 5px', borderRadius: '3px', background: 'var(--warning-bg)', color: 'var(--warning)', fontWeight: 600 }}>强</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
          <button className="btn" onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0} style={{ padding: '4px 10px', fontSize: '11px' }}>上一页</button>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{page + 1} / {totalPages}</span>
          <button className="btn" onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page === totalPages - 1} style={{ padding: '4px 10px', fontSize: '11px' }}>下一页</button>
        </div>
      )}
    </div>
  );
}
