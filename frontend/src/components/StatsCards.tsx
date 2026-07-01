import { BacktestResult } from '../types';

interface StatsCardsProps {
  result: BacktestResult;
}

function StatCard({ label, value, sublabel, color, isPercent }: {
  label: string; value: number | string; sublabel?: string; color?: string; isPercent?: boolean;
}) {
  const isPositive = typeof value === 'number' && value > 0;
  const isNegative = typeof value === 'number' && value < 0;
  const displayColor = color || (isPositive ? 'var(--success)' : isNegative ? 'var(--danger)' : 'var(--text-primary)');

  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        {label}
      </div>
      <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: displayColor, lineHeight: 1.2 }}>
        {typeof value === 'number' ? (isPercent ? `${value > 0 ? '+' : ''}${value}%` : value.toLocaleString('en-US', { maximumFractionDigits: 2 })) : value}
      </div>
      {sublabel && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{sublabel}</div>}
    </div>
  );
}

export default function StatsCards({ result }: StatsCardsProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '10px' }}>
      <StatCard label="总收益率" value={result.total_return} isPercent color={result.total_return >= 0 ? 'var(--success)' : 'var(--danger)'} />
      <StatCard label="最终权益" value={result.final_capital} sublabel={`初始 ${result.initial_capital.toLocaleString()}`} />
      <StatCard label="年化收益" value={result.annual_return} isPercent color={result.annual_return >= 0 ? 'var(--success)' : 'var(--danger)'} />
      <StatCard label="总盈亏" value={result.total_pnl} sublabel={`${result.total_trades} 笔交易`} color={result.total_pnl >= 0 ? 'var(--success)' : 'var(--danger)'} />
      <StatCard label="胜率" value={`${result.win_rate}%`} sublabel={`盈${result.win_trades} / 亏${result.loss_trades}`} color={result.win_rate >= 50 ? 'var(--success)' : 'var(--warning)'} />
      <StatCard label="盈亏比" value={result.profit_factor} sublabel={`均盈 ${result.avg_win.toFixed(0)}`} color={result.profit_factor >= 1 ? 'var(--success)' : 'var(--danger)'} />
      <StatCard label="最大回撤" value={`${result.max_drawdown}%`} color="var(--danger)" />
      <StatCard label="夏普比率" value={result.sharpe_ratio} color={result.sharpe_ratio >= 1 ? 'var(--success)' : 'var(--warning)'} />
      <StatCard label="索提诺比率" value={result.sortino_ratio} color={result.sortino_ratio >= 1 ? 'var(--success)' : 'var(--warning)'} />
      <StatCard label="多空比" value={`${result.long_trades}/${result.short_trades}`} sublabel="多/空" />
      {result.use_leverage && (
        <>
          <StatCard label="杠杆倍数" value={`${result.leverage}x`} sublabel={`放大${result.leverage_amplification}x`} color="var(--primary)" />
          <StatCard label="强平次数" value={result.liquidation_count} sublabel={result.liquidation_count > 0 ? "⚠ 发生爆仓" : "无爆仓"} color={result.liquidation_count > 0 ? 'var(--danger)' : 'var(--success)'} />
          <StatCard label="资金费总额" value={result.total_funding_fees} sublabel="8h结算一次" color={result.total_funding_fees < 0 ? 'var(--danger)' : 'var(--success)'} />
          <StatCard label="最大仓位价值" value={result.max_position_value} sublabel={`保证金 ${result.max_margin_used.toFixed(0)}`} color="var(--info)" />
          <StatCard label="单笔风险占比" value={`${result.risk_per_trade_pct}%`} sublabel="安全线≤2%" color={result.risk_per_trade_pct > 2 ? 'var(--danger)' : 'var(--success)'} />
        </>
      )}
    </div>
  );
}
