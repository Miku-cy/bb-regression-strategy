import { LeverageReport, RiskEvent } from '../types';

interface LeverageReportViewProps {
  report: LeverageReport;
}

const SEVERITY_CONFIG = {
  critical: { color: 'var(--danger)', bg: 'var(--danger-bg)', icon: '🚨', label: '严重' },
  warning: { color: 'var(--warning)', bg: 'var(--warning-bg)', icon: '⚠️', label: '警告' },
  info: { color: 'var(--info)', bg: 'var(--info-bg)', icon: 'ℹ️', label: '提示' },
};

const CATEGORY_LABELS: { [key: string]: string } = {
  liquidation: '强平爆仓',
  huge_loss: '重大亏损',
  over_leverage: '过度杠杆',
  concentration: '风险集中',
  funding: '资金费率',
  operation: '操作风险',
};

function RiskScoreGauge({ score, level }: { score: number; level: string }) {
  const getColor = () => {
    if (score >= 75) return 'var(--danger)';
    if (score >= 50) return 'var(--warning)';
    if (score >= 25) return '#f59e0b';
    return 'var(--success)';
  };

  const color = getColor();
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px' }}>
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="45" fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle
          cx="60" cy="60" r="45" fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
        <text x="60" y="56" textAnchor="middle" fontSize="24" fontWeight="700" fill={color} fontFamily="var(--font-mono)">
          {score}
        </text>
        <text x="60" y="76" textAnchor="middle" fontSize="11" fill="var(--text-muted)">/ 100</text>
      </svg>
      <div style={{
        marginTop: '8px',
        padding: '4px 14px',
        borderRadius: '12px',
        background: color,
        color: 'white',
        fontSize: '13px',
        fontWeight: 600,
      }}>
        风险等级: {level}
      </div>
    </div>
  );
}

function MetricCard({ label, value, unit, color }: { label: string; value: number | string; unit?: string; color?: string }) {
  return (
    <div className="card" style={{ padding: '12px 14px' }}>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>{label}</div>
      <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: color || 'var(--text-primary)' }}>
        {typeof value === 'number' ? value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : value}
        {unit && <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '2px' }}>{unit}</span>}
      </div>
    </div>
  );
}

function EventCard({ event, index }: { event: RiskEvent; index: number }) {
  const config = SEVERITY_CONFIG[event.severity] || SEVERITY_CONFIG.info;

  return (
    <div className="card" style={{
      padding: '14px 16px',
      borderLeft: `4px solid ${config.color}`,
      marginBottom: '10px',
      background: config.bg,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px' }}>{config.icon}</span>
          <span style={{ fontSize: '13px', fontWeight: 600, color: config.color }}>{event.title}</span>
        </div>
        <span style={{
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: 600,
          background: config.color,
          color: 'white',
        }}>
          {config.label} · {CATEGORY_LABELS[event.category] || event.category}
        </span>
      </div>

      <pre style={{
        fontSize: '12px',
        color: 'var(--text-secondary)',
        margin: '0 0 8px 0',
        whiteSpace: 'pre-wrap',
        fontFamily: 'var(--font-mono)',
        lineHeight: 1.6,
      }}>
        {event.description}
      </pre>

      <div style={{
        padding: '8px 12px',
        background: 'var(--bg-card)',
        borderRadius: 'var(--radius-sm)',
        fontSize: '12px',
        color: 'var(--text-primary)',
        borderLeft: `3px solid ${config.color}`,
      }}>
        <span style={{ fontWeight: 600 }}>💡 建议: </span>
        {event.suggestion}
      </div>
    </div>
  );
}

export default function LeverageReportView({ report }: LeverageReportViewProps) {
  const criticalCount = report.events.filter(e => e.severity === 'critical').length;
  const warningCount = report.events.filter(e => e.severity === 'warning').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* 风险评分总览 */}
      <div className="card" style={{ padding: '16px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>杠杆风险评估</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '16px', alignItems: 'center' }}>
          <RiskScoreGauge score={report.risk_score} level={report.risk_level} />
          <div>
            <div style={{
              padding: '12px 14px',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius)',
              fontSize: '13px',
              color: 'var(--text-primary)',
              lineHeight: 1.7,
              marginBottom: '10px',
            }}>
              {report.summary}
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {criticalCount > 0 && (
                <span style={{ padding: '4px 10px', background: 'var(--danger-bg)', color: 'var(--danger)', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>
                  🚨 严重事件 {criticalCount}
                </span>
              )}
              {warningCount > 0 && (
                <span style={{ padding: '4px 10px', background: 'var(--warning-bg)', color: 'var(--warning)', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>
                  ⚠️ 警告事件 {warningCount}
                </span>
              )}
              {criticalCount === 0 && warningCount === 0 && (
                <span style={{ padding: '4px 10px', background: 'var(--success-bg)', color: 'var(--success)', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>
                  ✅ 无风险事件
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 关键指标 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '10px' }}>
        <MetricCard label="最大单笔亏损占比" value={report.max_loss_per_trade_pct} unit="%" color="var(--danger)" />
        <MetricCard label="平均单笔亏损占比" value={report.avg_loss_per_trade_pct} unit="%" color="var(--warning)" />
        <MetricCard label="强平率" value={report.liquidation_rate} unit="%" color={report.liquidation_rate > 0 ? 'var(--danger)' : 'var(--success)'} />
        <MetricCard label="资金费占比" value={report.funding_fee_ratio} unit="%" color="var(--warning)" />
        <MetricCard label="保证金利用率" value={report.margin_utilization} unit="%" color={report.margin_utilization > 70 ? 'var(--danger)' : 'var(--success)'} />
        <MetricCard label="杠杆盈亏比" value={report.risk_reward_with_lev} color={report.risk_reward_with_lev >= 1 ? 'var(--success)' : 'var(--danger)'} />
      </div>

      {/* 风险事件列表 */}
      {report.events.length > 0 && (
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px', color: 'var(--text-primary)' }}>
            ⚠ 风险事件明细（{report.events.length}）
          </h3>
          {report.events.map((event, i) => (
            <EventCard key={i} event={event} index={i} />
          ))}
        </div>
      )}

      {/* 改进建议 */}
      <div className="card" style={{ padding: '16px', background: 'var(--info-bg)', borderColor: 'var(--info)' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px', color: 'var(--info)' }}>
          💡 改进建议
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {report.recommendations.map((rec, i) => (
            <div key={i} style={{
              padding: '10px 12px',
              background: 'var(--bg-card)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              color: 'var(--text-primary)',
              lineHeight: 1.6,
            }}>
              {rec}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
