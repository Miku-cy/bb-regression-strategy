import { useState, useEffect, useCallback } from 'react';
import { StrategyParams, BacktestResponse, LocalDataItem } from './types';
import { runBacktest, exportReport, getLocalData, checkHealth } from './api';
import ParameterPanel from './components/ParameterPanel';
import StatsCards from './components/StatsCards';
import EquityChart from './components/EquityChart';
import DrawdownChart from './components/DrawdownChart';
import TradeTable from './components/TradeTable';
import DataManagement from './components/DataManagement';
import ReportCharts from './components/ReportCharts';
import LeverageReportView from './components/LeverageReport';

const DEFAULT_PARAMS: StrategyParams = {
  symbol: 'BTC/USDT',
  days: 365,
  large_timeframe: '1h',
  bb_period: 20,
  bb_std: 2.0,
  small_timeframe: '5m',
  macd_fast: 12,
  macd_slow: 26,
  macd_signal: 9,
  swing_lookback: 10,
  atr_period: 14,
  stop_atr_mult: 2.0,
  stop_atr_buffer: 0.5,
  risk_percent: 2.0,
  tp1_ratio: 1.0,
  tp1_close_ratio: 0.5,
  tp2_ratio: 2.0,
  use_bb_mid_exit: true,
  use_near_zero_filter: true,
  initial_capital: 100000,
  fee_rate: 0.0004,
  slippage: 0.0002,
  // 杠杆默认参数
  use_leverage: false,
  leverage: 10,
  margin_mode: 'cross',
  use_funding_rate: true,
  funding_rate_override: -1,
};

type Tab = 'backtest' | 'data' | 'report' | 'leverage';

export default function App() {
  const [params, setParams] = useState<StrategyParams>(DEFAULT_PARAMS);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [localData, setLocalData] = useState<LocalDataItem[]>([]);
  const [tab, setTab] = useState<Tab>('backtest');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline' | 'demo'>('checking');
  const [isDemoMode, setIsDemoMode] = useState(false);

  const handleParamChange = (key: keyof StrategyParams, value: number | boolean | string) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  const refreshLocalData = useCallback(async () => {
    try {
      const data = await getLocalData();
      setLocalData(data);
    } catch (e) {
      // 忽略
    }
  }, []);

  const checkBackend = useCallback(async () => {
    try {
      const res = await checkHealth();
      if (res.status === 'demo') {
        setBackendStatus('demo');
        setIsDemoMode(true);
      } else {
        setBackendStatus('online');
        setIsDemoMode(false);
      }
    } catch {
      setBackendStatus('offline');
      setIsDemoMode(false);
    }
  }, []);

  useEffect(() => {
    checkBackend();
    refreshLocalData();
  }, [checkBackend, refreshLocalData]);

  const handleRunBacktest = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await runBacktest(params);
      setResult(res);
      setTab('backtest');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '回测失败');
    } finally {
      setLoading(false);
    }
  };

  const handleExportReport = async () => {
    setExporting(true);
    setError('');
    try {
      const res = await exportReport(params);
      alert(`报告已导出到:\n${res.files.join('\n')}`);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '导出失败');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
      {/* 顶部导航 */}
      <header style={{
        height: '56px',
        background: 'var(--bg-card)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        flexShrink: 0,
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
              <path d="M3 17 Q7 8 12 12 T21 6" />
            </svg>
          </div>
          <div>
            <h1 style={{ fontSize: '15px', fontWeight: 700, fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
              布林带回归策略
            </h1>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.5px' }}>
              CRYPTO QUANTITATIVE BACKTEST SYSTEM
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* 后端状态 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px' }}>
            <div style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: backendStatus === 'online' ? 'var(--success)' : backendStatus === 'demo' ? 'var(--info)' : backendStatus === 'offline' ? 'var(--danger)' : 'var(--warning)',
              animation: backendStatus === 'checking' ? 'pulse 1s infinite' : 'none',
            }} />
            <span style={{ color: 'var(--text-muted)' }}>
              {backendStatus === 'online' ? '后端已连接' : backendStatus === 'demo' ? 'CSV演示模式' : backendStatus === 'offline' ? '后端未连接' : '连接中...'}
            </span>
          </div>

          {/* Tab 切换 */}
          <div style={{ display: 'flex', gap: '2px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', padding: '2px' }}>
            {([
              { key: 'backtest', label: '回测结果' },
              { key: 'leverage', label: '杠杆分析' },
              { key: 'data', label: '数据管理' },
              { key: 'report', label: '报告图表' },
            ] as const).map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                style={{
                  padding: '5px 14px',
                  fontSize: '12px',
                  fontWeight: 500,
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  background: tab === t.key ? 'var(--bg-card)' : 'transparent',
                  color: tab === t.key ? 'var(--primary)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  transition: 'var(--transition)',
                  boxShadow: tab === t.key ? 'var(--shadow-sm)' : 'none',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* 主体内容 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 左侧参数面板 */}
        <aside style={{
          width: '320px',
          flexShrink: 0,
          background: 'var(--bg-card)',
          borderRight: '1px solid var(--border)',
          overflow: 'hidden',
        }}>
          <ParameterPanel
            params={params}
            onChange={handleParamChange}
            onRunBacktest={handleRunBacktest}
            onExportReport={handleExportReport}
            loading={loading}
            exporting={exporting}
          />
        </aside>

        {/* 右侧主内容 */}
        <main style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          {isDemoMode && (
            <div style={{
              padding: '10px 16px',
              marginBottom: '12px',
              borderRadius: 'var(--radius)',
              background: 'var(--info-bg)',
              color: 'var(--info)',
              fontSize: '12px',
              border: '1px solid var(--info)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <span style={{ fontSize: '16px' }}>📊</span>
              <span>
                <strong>CSV演示模式</strong> · 当前使用预导出的回测数据（BTC/USDT 365天）。
                切换「启用杠杆」可对比10x杠杆回测结果。完整功能请部署后端服务。
              </span>
            </div>
          )}

          {error && (
            <div style={{
              padding: '12px 16px',
              marginBottom: '12px',
              borderRadius: 'var(--radius)',
              background: 'var(--danger-bg)',
              color: 'var(--danger)',
              fontSize: '13px',
              border: '1px solid var(--danger)',
            }}>
              ⚠ {error}
            </div>
          )}

          {tab === 'backtest' && (
            <div className="fade-in">
              {!result ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--text-muted)',
                  gap: '16px',
                }}>
                  <div style={{
                    width: '80px', height: '80px', borderRadius: '50%',
                    background: 'var(--primary-bg)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '36px',
                  }}>
                    📈
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      准备开始回测
                    </div>
                    <div style={{ fontSize: '13px' }}>
                      在左侧调整策略参数，点击「运行回测」开始
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <StatsCards result={result.result} />
                  <EquityChart result={result.result} />
                  <DrawdownChart result={result.result} />
                  <TradeTable trades={result.result.trades} />
                </div>
              )}
            </div>
          )}

          {tab === 'data' && (
            <div className="fade-in" style={{ maxWidth: '800px' }}>
              <DataManagement localData={localData} onRefresh={refreshLocalData} isDemoMode={isDemoMode} />
            </div>
          )}

          {tab === 'leverage' && (
            <div className="fade-in">
              {!result ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--text-muted)',
                  gap: '16px',
                }}>
                  <div style={{
                    width: '80px', height: '80px', borderRadius: '50%',
                    background: 'var(--warning-bg)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '36px',
                  }}>
                    ⚡
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      杠杆分析报告
                    </div>
                    <div style={{ fontSize: '13px' }}>
                      请先在左侧启用杠杆并运行回测
                    </div>
                  </div>
                </div>
              ) : !result.result.use_leverage ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--text-muted)',
                  gap: '16px',
                }}>
                  <div style={{
                    width: '80px', height: '80px', borderRadius: '50%',
                    background: 'var(--bg-secondary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '36px',
                  }}>
                    🔒
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      当前回测未启用杠杆
                    </div>
                    <div style={{ fontSize: '13px' }}>
                      请在左侧参数面板「杠杆 · 币安永续」中开启杠杆后重新回测
                    </div>
                  </div>
                </div>
              ) : result.leverage_report ? (
                <LeverageReportView report={result.leverage_report} />
              ) : (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--text-muted)',
                  fontSize: '14px',
                }}>
                  杠杆报告生成失败
                </div>
              )}
            </div>
          )}

          {tab === 'report' && (
            <div className="fade-in">
              {result ? (
                <ReportCharts charts={result.charts} />
              ) : (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--text-muted)',
                  fontSize: '14px',
                }}>
                  请先运行回测生成报告
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
