import ReactECharts from 'echarts-for-react';
import { BacktestResult } from '../types';

interface EquityChartProps {
  result: BacktestResult;
}

export default function EquityChart({ result }: EquityChartProps) {
  const equityData = result.equity_curve.map(p => [p.datetime, p.equity]);
  const initialCapital = result.initial_capital;

  const option = {
    grid: { top: 20, right: 20, bottom: 50, left: 70 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#0f172a', fontSize: 12 },
      formatter: (params: any) => {
        const p = params[0];
        const dt = new Date(p.value[0]);
        return `<div style="font-size:11px;color:#64748b">${dt.toLocaleString('zh-CN')}</div>
                <div style="font-size:14px;font-weight:600;margin-top:2px">权益: <span style="color:#6366f1">${Number(p.value[1]).toLocaleString('en-US', {maximumFractionDigits: 2})}</span></div>`;
      }
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#94a3b8', fontSize: 11,
        formatter: (v: number) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v.toFixed(0)
      },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    series: [
      {
        name: '权益',
        type: 'line',
        data: equityData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 2, color: '#6366f1' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(99, 102, 241, 0.25)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.01)' }
            ]
          }
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#cbd5e1', type: 'dashed', width: 1 },
          data: [{ yAxis: initialCapital, label: { formatter: '初始资金', color: '#94a3b8', fontSize: 10 } }]
        }
      }
    ]
  };

  return (
    <div className="card" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>资金曲线</h3>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{result.symbol}</span>
      </div>
      <ReactECharts option={option} style={{ height: '300px' }} />
    </div>
  );
}
