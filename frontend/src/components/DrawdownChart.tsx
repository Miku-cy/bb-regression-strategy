import ReactECharts from 'echarts-for-react';
import { BacktestResult } from '../types';

interface DrawdownChartProps {
  result: BacktestResult;
}

export default function DrawdownChart({ result }: DrawdownChartProps) {
  const ddData = result.drawdown_curve.map(p => [p.datetime, p.drawdown]);

  const option = {
    grid: { top: 20, right: 20, bottom: 50, left: 50 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#0f172a', fontSize: 12 },
      formatter: (params: any) => {
        const p = params[0];
        return `<div style="font-size:11px;color:#64748b">${new Date(p.value[0]).toLocaleString('zh-CN')}</div>
                <div style="font-size:14px;font-weight:600;margin-top:2px">回撤: <span style="color:#ef4444">${p.value[1]}%</span></div>`;
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
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    series: [
      {
        name: '回撤',
        type: 'line',
        data: ddData,
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#ef4444' },
        areaStyle: { color: 'rgba(239, 68, 68, 0.15)' }
      }
    ]
  };

  return (
    <div className="card" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>回撤曲线</h3>
        <span style={{ fontSize: '11px', color: 'var(--danger)', fontWeight: 600 }}>最大回撤: {result.max_drawdown}%</span>
      </div>
      <ReactECharts option={option} style={{ height: '220px' }} />
    </div>
  );
}
