import Slider from './Slider';
import { StrategyParams } from '../types';

interface ParameterPanelProps {
  params: StrategyParams;
  onChange: (key: keyof StrategyParams, value: number | boolean) => void;
  onRunBacktest: () => void;
  onExportReport: () => void;
  loading: boolean;
  exporting: boolean;
}

function Toggle({ label, value, onChange, description }: {
  label: string; value: boolean; onChange: (v: boolean) => void; description?: string;
}) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>{label}</label>
        <div
          onClick={() => onChange(!value)}
          style={{
            width: '36px',
            height: '20px',
            borderRadius: '10px',
            background: value ? 'var(--primary)' : 'var(--border)',
            cursor: 'pointer',
            transition: 'var(--transition)',
            position: 'relative',
            flexShrink: 0,
          }}
        >
          <div style={{
            position: 'absolute',
            top: '2px',
            left: value ? '18px' : '2px',
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            background: 'white',
            transition: 'var(--transition)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
          }} />
        </div>
      </div>
      {description && <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '3px' }}>{description}</div>}
    </div>
  );
}

function GroupTitle({ title, icon }: { title: string; icon: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      marginTop: '18px',
      marginBottom: '10px',
      paddingBottom: '6px',
      borderBottom: '1px solid var(--border-light)',
    }}>
      <span style={{ fontSize: '14px' }}>{icon}</span>
      <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {title}
      </span>
    </div>
  );
}

export default function ParameterPanel({ params, onChange, onRunBacktest, onExportReport, loading, exporting }: ParameterPanelProps) {
  return (
    <div style={{ padding: '16px', height: '100%', overflowY: 'auto' }}>
      {/* 交易标的 */}
      <GroupTitle title="交易标的" icon="🎯" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '10px' }}>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>交易对</label>
          <select
            className="select"
            value={params.symbol}
            onChange={(e) => onChange('symbol', e.target.value as any)}
          >
            {['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT', 'LTC/USDT', 'TRX/USDT', 'ATOM/USDT', 'NEAR/USDT'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>回测天数</label>
          <select
            className="select"
            value={params.days}
            onChange={(e) => onChange('days', parseInt(e.target.value))}
          >
            <option value={90}>90天</option>
            <option value={180}>180天</option>
            <option value={365}>1年</option>
            <option value={730}>2年</option>
          </select>
        </div>
      </div>

      {/* 大周期参数 */}
      <GroupTitle title="大周期 · 布林带" icon="📊" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '10px' }}>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>大周期</label>
          <select className="select" value={params.large_timeframe} onChange={(e) => onChange('large_timeframe', e.target.value as any)}>
            <option value="1h">1H</option>
            <option value="4h">4H</option>
            <option value="1d">1D</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>小周期</label>
          <select className="select" value={params.small_timeframe} onChange={(e) => onChange('small_timeframe', e.target.value as any)}>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="30m">30m</option>
          </select>
        </div>
      </div>
      <Slider label="布林带周期" value={params.bb_period} min={5} max={50} step={1} onChange={(v) => onChange('bb_period', v)} description="BB计算周期" />
      <Slider label="标准差倍数" value={params.bb_std} min={1} max={3} step={0.1} onChange={(v) => onChange('bb_std', v)} description="BB宽度倍数" />

      {/* 小周期参数 */}
      <GroupTitle title="小周期 · MACD" icon="📈" />
      <Slider label="MACD快线" value={params.macd_fast} min={5} max={20} step={1} onChange={(v) => onChange('macd_fast', v)} />
      <Slider label="MACD慢线" value={params.macd_slow} min={15} max={40} step={1} onChange={(v) => onChange('macd_slow', v)} />
      <Slider label="MACD信号线" value={params.macd_signal} min={5} max={15} step={1} onChange={(v) => onChange('macd_signal', v)} />
      <Slider label="震荡区域回看" value={params.swing_lookback} min={5} max={30} step={1} onChange={(v) => onChange('swing_lookback', v)} description="寻找高低点的K线根数" />

      {/* 风险管理 */}
      <GroupTitle title="风险管理" icon="🛡️" />
      <Slider label="ATR周期" value={params.atr_period} min={7} max={28} step={1} onChange={(v) => onChange('atr_period', v)} />
      <Slider label="止损ATR倍数" value={params.stop_atr_mult} min={1} max={4} step={0.1} onChange={(v) => onChange('stop_atr_mult', v)} description="2倍ATR止损" />
      <Slider label="止损缓冲ATR" value={params.stop_atr_buffer} min={0} max={1.5} step={0.1} onChange={(v) => onChange('stop_atr_buffer', v)} description="额外缓冲距离" />
      <Slider label="单次风险比例" value={params.risk_percent} min={0.5} max={5} step={0.1} unit="%" onChange={(v) => onChange('risk_percent', v)} description="单笔最大亏损占总资金" />

      {/* 止盈参数 */}
      <GroupTitle title="止盈策略" icon="💰" />
      <Slider label="第一目标盈亏比" value={params.tp1_ratio} min={0.5} max={2} step={0.1} onChange={(v) => onChange('tp1_ratio', v)} description="达到后平仓比例" />
      <Slider label="第一目标平仓比例" value={params.tp1_close_ratio} min={0.2} max={0.8} step={0.05} onChange={(v) => onChange('tp1_close_ratio', v)} />
      <Slider label="保本触发盈亏比" value={params.tp2_ratio} min={1.5} max={4} step={0.1} onChange={(v) => onChange('tp2_ratio', v)} description="达到后设置成本线止损" />
      <Toggle label="布林带中轨止盈" value={params.use_bb_mid_exit} onChange={(v) => onChange('use_bb_mid_exit', v)} description="价格回到大周期BB中轨时平仓" />

      {/* 信号过滤 */}
      <GroupTitle title="信号过滤" icon="🔍" />
      <Toggle label="MACD近零轴增强" value={params.use_near_zero_filter} onChange={(v) => onChange('use_near_zero_filter', v)} description="MACD交叉近0轴时信号更强" />

      {/* 资金管理 */}
      <GroupTitle title="资金管理" icon="🏦" />
      <Slider label="初始资金" value={params.initial_capital} min={10000} max={1000000} step={10000} unit="U" onChange={(v) => onChange('initial_capital', v)} />
      <Slider label="手续费率" value={params.fee_rate} min={0} max={0.002} step={0.0001} onChange={(v) => onChange('fee_rate', v)} description="单边手续费" />
      <Slider label="滑点" value={params.slippage} min={0} max={0.001} step={0.0001} onChange={(v) => onChange('slippage', v)} />

      {/* 杠杆设置 */}
      <GroupTitle title="杠杆 · 币安永续" icon="⚡" />
      <Toggle label="启用杠杆" value={params.use_leverage} onChange={(v) => onChange('use_leverage', v)} description="启用币安USDT永续合约杠杆交易" />
      {params.use_leverage && (
        <>
          <Slider label="杠杆倍数" value={params.leverage} min={1} max={125} step={1} unit="x" onChange={(v) => onChange('leverage', v)} description="1-125x，仓位越大允许杠杆越低" />
          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>保证金模式</label>
            <select className="select" value={params.margin_mode} onChange={(e) => onChange('margin_mode', e.target.value as any)}>
              <option value="cross">全仓交叉（共享保证金）</option>
              <option value="isolated">逐仓孤立（风险隔离）</option>
            </select>
          </div>
          <Toggle label="计算资金费率" value={params.use_funding_rate} onChange={(v) => onChange('use_funding_rate', v)} description="每8小时结算资金费（0.01%默认）" />
          <Slider label="自定义资金费率" value={params.funding_rate_override < 0 ? 0.0001 : params.funding_rate_override} min={0} max={0.001} step={0.00005} onChange={(v) => onChange('funding_rate_override', v)} description="-1表示使用默认，0.0001=0.01%" />
          <div style={{
            padding: '10px 12px',
            background: 'var(--warning-bg)',
            border: '1px solid var(--warning)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '11px',
            color: 'var(--warning)',
            marginTop: '8px',
            lineHeight: 1.6,
          }}>
            ⚠ 杠杆交易风险提示：<br/>
            • {params.leverage}x杠杆下，价格反向波动 {(100/params.leverage).toFixed(2)}% 即爆仓<br/>
            • 强平将收取仓位价值0.5%的清算费<br/>
            • 资金费率每8小时结算，长期持仓成本累积
          </div>
        </>
      )}

      {/* 操作按钮 */}
      <div style={{ display: 'flex', gap: '8px', marginTop: '20px', position: 'sticky', bottom: '0', background: 'var(--bg-card)', padding: '12px 0', borderTop: '1px solid var(--border-light)' }}>
        <button
          className="btn btn-primary"
          onClick={onRunBacktest}
          disabled={loading}
          style={{ flex: 1, padding: '10px', fontSize: '14px', fontWeight: 600 }}
        >
          {loading ? <><span className="spinner" /> 回测中...</> : '▶ 运行回测'}
        </button>
        <button
          className="btn"
          onClick={onExportReport}
          disabled={exporting || loading}
          style={{ padding: '10px 14px', fontSize: '14px' }}
          title="导出报告图片到本地"
        >
          {exporting ? <span className="spinner" /> : '📥'}
        </button>
      </div>
    </div>
  );
}
