// 策略参数类型
export interface StrategyParams {
  symbol: string;
  days: number;
  // 大周期
  large_timeframe: string;
  bb_period: number;
  bb_std: number;
  // 小周期
  small_timeframe: string;
  macd_fast: number;
  macd_slow: number;
  macd_signal: number;
  swing_lookback: number;
  // 风险管理
  atr_period: number;
  stop_atr_mult: number;
  stop_atr_buffer: number;
  risk_percent: number;
  // 止盈
  tp1_ratio: number;
  tp1_close_ratio: number;
  tp2_ratio: number;
  use_bb_mid_exit: boolean;
  // 信号过滤
  use_near_zero_filter: boolean;
  // 资金
  initial_capital: number;
  fee_rate: number;
  slippage: number;
  // ===== 杠杆参数 =====
  use_leverage: boolean;
  leverage: number;
  margin_mode: string;
  use_funding_rate: boolean;
  funding_rate_override: number;
}

// 回测结果
export interface BacktestResult {
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  total_pnl: number;
  annual_return: number;
  total_trades: number;
  win_trades: number;
  loss_trades: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  max_win: number;
  max_loss: number;
  avg_rr: number;
  max_drawdown: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  avg_holding_bars: number;
  long_trades: number;
  short_trades: number;
  // 杠杆统计
  use_leverage: boolean;
  leverage: number;
  liquidation_count: number;
  total_funding_fees: number;
  total_liquidation_fees: number;
  max_position_value: number;
  avg_margin_used: number;
  max_margin_used: number;
  leverage_amplification: number;
  risk_per_trade_pct: number;
  // 数据序列
  equity_curve: { datetime: string; equity: number }[];
  drawdown_curve: { datetime: string; drawdown: number }[];
  trades: Trade[];
}

export interface Trade {
  entry_time: string;
  exit_time: string | null;
  entry_price: number;
  exit_price: number | null;
  direction: 'long' | 'short';
  size: number;
  stop_loss: number;
  initial_stop: number;
  take_profit_1: number;
  pnl: number;
  pnl_pct: number;
  rr: number;
  exit_reason: string;
  tp1_hit: boolean;
  breakeven_set: boolean;
  signal_strength: number;
  // 杠杆字段
  leverage: number;
  margin: number;
  position_value: number;
  liquidation_price: number;
  funding_fees: number;
  liquidation_fee: number;
  is_liquidated: boolean;
  margin_ratio_at_entry: number;
  mmr_tier: number;
}

// 杠杆分析报告
export interface LeverageReport {
  risk_level: string;          // '极高' | '高' | '中' | '低'
  risk_score: number;          // 0-100
  max_loss_per_trade_pct: number;
  avg_loss_per_trade_pct: number;
  liquidation_rate: number;
  funding_fee_ratio: number;
  margin_utilization: number;
  risk_reward_with_lev: number;
  events: RiskEvent[];
  summary: string;
  recommendations: string[];
}

export interface RiskEvent {
  severity: 'critical' | 'warning' | 'info';
  category: string;
  title: string;
  description: string;
  trade_index: number;
  value: number;
  suggestion: string;
}

export interface BacktestResponse {
  success: boolean;
  result: BacktestResult;
  charts: { [key: string]: string };
  leverage_report: LeverageReport | null;
}

export interface LocalDataItem {
  symbol: string;
  timeframe: string;
  file: string;
  size_kb: number;
  rows?: number;
}
