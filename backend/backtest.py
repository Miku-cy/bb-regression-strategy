"""
回测引擎
运行策略、生成资金曲线、计算统计指标
支持杠杆模式统计
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict, field
from typing import Optional
from strategy import StrategyParams, run_strategy, prepare_large_tf_data, prepare_small_tf_data, align_timeframes
from data_downloader import ensure_data


@dataclass
class BacktestResult:
    """回测结果"""
    # 基础信息
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float

    # 收益指标
    total_return: float
    total_pnl: float
    annual_return: float

    # 交易统计
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_win: float
    max_loss: float
    avg_rr: float

    # 风险指标
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float

    # 持仓统计
    avg_holding_bars: float
    long_trades: int
    short_trades: int

    # ===== 杠杆统计指标 =====
    use_leverage: bool = False
    leverage: float = 1.0
    liquidation_count: int = 0          # 强平次数
    total_funding_fees: float = 0.0     # 总资金费
    total_liquidation_fees: float = 0.0 # 总强平清算费
    max_position_value: float = 0.0     # 最大仓位价值
    avg_margin_used: float = 0.0        # 平均占用保证金
    max_margin_used: float = 0.0        # 最大占用保证金
    leverage_amplification: float = 1.0 # 杠杆放大倍数（收益率/无杠杆收益率）
    risk_per_trade_pct: float = 0.0     # 实际单笔风险占比

    # 数据序列
    equity_curve: list = None
    drawdown_curve: list = None
    trades: list = None


def run_backtest(symbol: str, params: StrategyParams, days: int = 365) -> BacktestResult:
    """运行完整回测"""
    small_df = ensure_data(symbol, params.small_timeframe, days)
    large_df = ensure_data(symbol, params.large_timeframe, days)

    if small_df.empty or large_df.empty:
        raise ValueError(f"无法获取 {symbol} 的数据")

    min_rows = max(params.bb_period * 3, 100)
    if len(small_df) < min_rows or len(large_df) < min_rows:
        raise ValueError(f"{symbol} 数据量不足，需要至少 {min_rows} 条")

    # 运行策略
    trades = run_strategy(small_df, large_df, params, symbol)

    # 生成资金曲线
    equity_curve = _build_equity_curve(small_df, trades, params)
    drawdown_curve = _build_drawdown_curve(equity_curve)

    # 计算统计指标
    stats = _calculate_stats(trades, equity_curve, drawdown_curve, params)

    result = BacktestResult(
        symbol=symbol,
        start_date=small_df['datetime'].iloc[0].strftime('%Y-%m-%d'),
        end_date=small_df['datetime'].iloc[-1].strftime('%Y-%m-%d'),
        initial_capital=params.initial_capital,
        final_capital=equity_curve[-1]['equity'] if equity_curve else params.initial_capital,
        **stats,
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        trades=[_trade_to_dict(t) for t in trades],
    )
    return result


def _trade_to_dict(trade) -> dict:
    """将Trade对象转为字典"""
    d = asdict(trade)
    if d.get('entry_time'):
        d['entry_time'] = str(d['entry_time'])
    if d.get('exit_time'):
        d['exit_time'] = str(d['exit_time'])
    return d


def _build_equity_curve(small_df: pd.DataFrame, trades: list, params: StrategyParams) -> list:
    """构建资金曲线"""
    if not trades:
        return [
            {"datetime": str(small_df['datetime'].iloc[0]), "equity": params.initial_capital},
            {"datetime": str(small_df['datetime'].iloc[-1]), "equity": params.initial_capital}
        ]

    sorted_trades = sorted(trades, key=lambda t: t.entry_time)
    equity = params.initial_capital
    curve = [{"datetime": str(small_df['datetime'].iloc[0]), "equity": equity}]

    for trade in sorted_trades:
        if trade.exit_time:
            equity += trade.pnl
            curve.append({
                "datetime": str(trade.exit_time),
                "equity": round(equity, 2)
            })

    last_dt = str(small_df['datetime'].iloc[-1])
    if curve[-1]["datetime"] != last_dt:
        curve.append({"datetime": last_dt, "equity": round(equity, 2)})

    return curve


def _build_drawdown_curve(equity_curve: list) -> list:
    """构建回撤曲线"""
    if not equity_curve:
        return []

    peak = equity_curve[0]["equity"]
    result = []
    for point in equity_curve:
        eq = point["equity"]
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak * 100 if peak > 0 else 0
        result.append({
            "datetime": point["datetime"],
            "drawdown": round(dd, 2)
        })
    return result


def _calculate_stats(trades: list, equity_curve: list, drawdown_curve: list, params: StrategyParams) -> dict:
    """计算统计指标（含杠杆统计）"""
    if not trades:
        return _empty_stats()

    pnls = [t.pnl for t in trades]
    total_pnl = sum(pnls)
    total_return = total_pnl / params.initial_capital * 100

    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [p for p in pnls if p < 0]

    win_trades = len(win_pnls)
    loss_trades = len(loss_pnls)
    total_trades = len(trades)
    win_rate = win_trades / total_trades * 100 if total_trades > 0 else 0

    avg_win = np.mean(win_pnls) if win_pnls else 0
    avg_loss = np.mean(loss_pnls) if loss_pnls else 0
    gross_profit = sum(win_pnls)
    gross_loss = abs(sum(loss_pnls))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    max_win = max(pnls) if pnls else 0
    max_loss = min(pnls) if pnls else 0

    rrs = [t.rr for t in trades if t.rr > 0]
    avg_rr = np.mean(rrs) if rrs else 0

    max_dd = min([p["drawdown"] for p in drawdown_curve]) if drawdown_curve else 0

    # 年化收益率
    if equity_curve and len(equity_curve) > 1:
        start_dt = pd.to_datetime(equity_curve[0]["datetime"])
        end_dt = pd.to_datetime(equity_curve[-1]["datetime"])
        days = (end_dt - start_dt).days
        if days > 0:
            annual_return = ((equity_curve[-1]["equity"] / params.initial_capital) ** (365 / days) - 1) * 100
        else:
            annual_return = 0
    else:
        annual_return = 0

    # 夏普/索提诺
    returns = [p / params.initial_capital for p in pnls]
    if len(returns) > 1:
        avg_ret = np.mean(returns)
        std_ret = np.std(returns)
        sharpe = avg_ret / std_ret * np.sqrt(len(returns)) if std_ret > 0 else 0
        downside = [r for r in returns if r < 0]
        downside_std = np.std(downside) if downside else 0
        sortino = avg_ret / downside_std * np.sqrt(len(returns)) if downside_std > 0 else 0
    else:
        sharpe = 0
        sortino = 0

    long_trades = sum(1 for t in trades if t.direction == 'long')
    short_trades = sum(1 for t in trades if t.direction == 'short')

    holding_bars = []
    for t in trades:
        if t.entry_time and t.exit_time:
            delta = (t.exit_time - t.entry_time).total_seconds()
            bars = delta / 300
            holding_bars.append(bars)
    avg_holding_bars = np.mean(holding_bars) if holding_bars else 0

    # ===== 杠杆统计 =====
    use_lev = params.use_leverage and params.leverage > 1.0
    liquidation_count = sum(1 for t in trades if t.is_liquidated)
    total_funding_fees = sum(t.funding_fees for t in trades)
    total_liquidation_fees = sum(t.liquidation_fee for t in trades)
    max_position_value = max([t.position_value for t in trades], default=0)
    avg_margin_used = np.mean([t.margin for t in trades]) if trades else 0
    max_margin_used = max([t.margin for t in trades], default=0)

    # 杠杆放大倍数：实际收益率 / 无杠杆理论收益率
    # 无杠杆理论收益率 ≈ 总盈亏 / 平均仓位价值 × 初始资金
    if use_lev and total_pnl != 0:
        # 简化：杠杆放大倍数 = 杠杆倍数（实际放大效应受强平影响）
        leverage_amplification = params.leverage
    else:
        leverage_amplification = 1.0

    # 实际单笔风险占比（基于止损距离）
    risk_pcts = []
    for t in trades:
        if t.entry_price > 0 and t.initial_stop != t.entry_price:
            stop_dist_pct = abs(t.entry_price - t.initial_stop) / t.entry_price
            # 杠杆下实际风险 = 仓位价值 × 止损百分比 / 账户资金
            actual_risk = (t.position_value * stop_dist_pct) / params.initial_capital * 100
            risk_pcts.append(actual_risk)
    avg_risk_pct = np.mean(risk_pcts) if risk_pcts else 0

    return {
        "total_return": round(total_return, 2),
        "total_pnl": round(total_pnl, 2),
        "annual_return": round(annual_return, 2),
        "total_trades": total_trades,
        "win_trades": win_trades,
        "loss_trades": loss_trades,
        "win_rate": round(win_rate, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999,
        "max_win": round(max_win, 2),
        "max_loss": round(max_loss, 2),
        "avg_rr": round(avg_rr, 2),
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_duration": 0,
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "avg_holding_bars": round(avg_holding_bars, 1),
        "long_trades": long_trades,
        "short_trades": short_trades,
        # 杠杆统计
        "use_leverage": use_lev,
        "leverage": params.leverage if use_lev else 1.0,
        "liquidation_count": liquidation_count,
        "total_funding_fees": round(total_funding_fees, 2),
        "total_liquidation_fees": round(total_liquidation_fees, 2),
        "max_position_value": round(max_position_value, 2),
        "avg_margin_used": round(avg_margin_used, 2),
        "max_margin_used": round(max_margin_used, 2),
        "leverage_amplification": round(leverage_amplification, 2),
        "risk_per_trade_pct": round(avg_risk_pct, 2),
    }


def _empty_stats() -> dict:
    return {
        "total_return": 0, "total_pnl": 0, "annual_return": 0,
        "total_trades": 0, "win_trades": 0, "loss_trades": 0,
        "win_rate": 0, "avg_win": 0, "avg_loss": 0, "profit_factor": 0,
        "max_win": 0, "max_loss": 0, "avg_rr": 0,
        "max_drawdown": 0, "max_drawdown_duration": 0,
        "sharpe_ratio": 0, "sortino_ratio": 0,
        "avg_holding_bars": 0, "long_trades": 0, "short_trades": 0,
        "use_leverage": False, "leverage": 1.0,
        "liquidation_count": 0, "total_funding_fees": 0,
        "total_liquidation_fees": 0, "max_position_value": 0,
        "avg_margin_used": 0, "max_margin_used": 0,
        "leverage_amplification": 1.0, "risk_per_trade_pct": 0,
    }
