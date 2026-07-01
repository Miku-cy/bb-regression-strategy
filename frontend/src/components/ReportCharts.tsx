interface ReportChartsProps {
  charts: { [key: string]: string };
}

const CHART_TITLES: { [key: string]: string } = {
  equity_curve: '资金曲线',
  drawdown: '回撤曲线',
  pnl_distribution: '盈亏分布',
  cumulative_pnl: '累积盈亏',
  monthly_returns: '月度收益',
};

export default function ReportCharts({ charts }: ReportChartsProps) {
  const entries = Object.entries(charts);
  if (entries.length === 0) return null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '12px' }}>
      {entries.map(([key, src]) => (
        <div key={key} className="card" style={{ padding: '12px', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 600 }}>{CHART_TITLES[key] || key}</h4>
            <a
              href={src}
              download={`${key}.png`}
              style={{
                fontSize: '11px',
                color: 'var(--primary)',
                textDecoration: 'none',
                padding: '2px 8px',
                border: '1px solid var(--primary)',
                borderRadius: '4px',
              }}
            >
              下载
            </a>
          </div>
          <img src={src} alt={key} style={{ width: '100%', height: 'auto', borderRadius: 'var(--radius-sm)' }} />
        </div>
      ))}
    </div>
  );
}
