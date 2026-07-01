"""
布林带回归策略引擎
多周期信号：大周期(1H/4H)布林带触轨定方向，小周期(5m/15m)MACD+突破进场
支持币安USDT永续合约杠杆交易：保证金、强平、资金费率
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from indicators import bollinger_bands, macd, atr, find_swing_high_low, detect_macd_cross
from leverage_rules import (
    calc_initial_margin, calc_liquidation_price_cross,
    calc_funding_fee, is_funding_time, get_default_funding_rate,
    get_maintenance_margin_rate, calc_liquidation_fee, validate_leverage
)


@dataclass
class StrategyParams:
    """策略参数 - 所有参数均可通过前端滑条调整"""
    # 大周期参数
    large_timeframe: str = "1h"
    bb_period: int = 20
    bb_std: float = 2.0

    # 小周期参数
    small_timeframe: str = "5m"
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    swing_lookback: int = 10

    # 风险管理
    atr_period: int = 14
    stop_atr_mult: float = 2.0
    stop_atr_buffer: float = 0.5
    risk_percent: float = 2.0

    # 止盈参数
    tp1_ratio: float = 1.0       # 第一目标盈亏比
    tp1_close_ratio: float = 0.5  # 第一目标平仓比例
    tp2_ratio: float = 2.0       # 第二目标盈亏比（触发保本止损）
    use_bb_mid_exit: bool = True  # 是否使用布林带中轨止盈

    # 信号过滤
    use_near_zero_filter: bool = True  # MACD近零轴信号增强
    use_wm_filter: bool = False        # W底M顶过滤（简化版）

    # 资金管理
    initial_capital: float = 100000.0
    fee_rate: float = 0.0004  # Taker手续费率 0.04%
    slippage: float = 0.0002  # 滑点 0.02%

    # ===== 杠杆参数（币安USDT永续合约）=====
    use_leverage: bool = False  # 是否启用杠杆
    leverage: float = 10.0      # 杠杆倍数 1-125
    margin_mode: str = "cross"  # 保证金模式: 'cross'(全仓) 或 'isolated'(逐仓)
    use_funding_rate: bool = True  # 是否计算资金费率
    funding_rate_override: float = -1  # 自定义资金费率，-1表示使用默认


def prepare_large_tf_data(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """计算大周期布林带指标"""
    df = bollinger_bands(df, params.bb_period, params.bb_std)
    df['touch_upper'] = (df['high'] >= df['bb_upper']) & df['bb_upper'].notna()
    df['touch_lower'] = (df['low'] <= df['bb_lower']) & df['bb_lower'].notna()
    return df


def prepare_small_tf_data(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """计算小周期技术指标"""
    df = macd(df, params.macd_fast, params.macd_slow, params.macd_signal)
    df = atr(df, params.atr_period)
    df = find_swing_high_low(df, params.swing_lookback)
    df = detect_macd_cross(df)
    return df


def align_timeframes(small_df: pd.DataFrame, large_df: pd.DataFrame, large_tf: str) -> pd.DataFrame:
    """将大周期信号对齐到小周期"""
    large_cols = ['datetime', 'bb_mid', 'bb_upper', 'bb_lower', 'touch_upper', 'touch_lower']
    large_signal = large_df[large_cols].copy()
    large_signal = large_signal.rename(columns={
        'bb_mid': 'large_bb_mid',
        'bb_upper': 'large_bb_upper',
        'bb_lower': 'large_bb_lower',
        'touch_upper': 'large_touch_upper',
        'touch_lower': 'large_touch_lower',
    })
    small_df = small_df.sort_values('datetime').reset_index(drop=True)
    large_signal = large_signal.sort_values('datetime').reset_index(drop=True)
    merged = pd.merge_asof(small_df, large_signal, on='datetime', direction='backward')
    return merged


@dataclass
class Trade:
    """交易记录"""
    entry_time: pd.Timestamp
    entry_price: float
    direction: str  # 'long' or 'short'
    size: float
    stop_loss: float
    initial_stop: float
    take_profit_1: float
    risk_amount: float
    # 出场信息
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    rr: float = 0.0
    tp1_hit: bool = False
    breakeven_set: bool = False
    signal_strength: int = 1
    # ===== 杠杆相关字段 =====
    leverage: float = 1.0
    margin: float = 0.0           # 占用保证金
    position_value: float = 0.0   # 仓位价值
    liquidation_price: float = 0.0  # 强平价
    funding_fees: float = 0.0     # 累计资金费
    liquidation_fee: float = 0.0  # 强平清算费
    is_liquidated: bool = False   # 是否被强平
    margin_ratio_at_entry: float = 0.0  # 入场时保证金率
    mmr_tier: int = 1             # 维持保证金阶梯


def _get_funding_rate(params: StrategyParams, symbol: str) -> float:
    """获取资金费率"""
    if params.funding_rate_override >= 0:
        return params.funding_rate_override
    return get_default_funding_rate(symbol)


def _calc_position_size_with_leverage(
    capital: float, risk_amount: float, stop_distance: float,
    entry_price: float, leverage: float, symbol: str
) -> tuple:
    """
    计算带杠杆的仓位大小
    杠杆模式下：仓位价值 = 保证金 × 杠杆
    但风险仍由止损距离控制（risk_amount不变）
    :return: (仓位数量, 仓位价值, 保证金, 实际杠杆, 是否被限制, 限制说明)
    """
    # 基于风险的仓位数量（与无杠杆时相同）
    size_by_risk = risk_amount / stop_distance if stop_distance > 0 else 0
    position_value = size_by_risk * entry_price

    # 检查杠杆是否在允许范围内
    actual_lev, limited, reason = validate_leverage(symbol, leverage, position_value)

    # 保证金 = 仓位价值 / 杠杆
    margin = position_value / actual_lev if actual_lev > 0 else position_value

    # 检查保证金是否超过可用资金（全仓模式下不能超过总资金）
    if margin > capital:
        # 保证金不足，按可用资金重新计算
        margin = capital * 0.95  # 保留5%作为缓冲
        position_value = margin * actual_lev
        size_by_risk = position_value / entry_price

    return size_by_risk, position_value, margin, actual_lev, limited, reason


def run_strategy(small_df: pd.DataFrame, large_df: pd.DataFrame, params: StrategyParams, symbol: str = "BTC/USDT") -> list:
    """
    运行策略，生成交易信号和交易记录
    支持杠杆模式
    """
    large_df = prepare_large_tf_data(large_df.copy(), params)
    small_df = prepare_small_tf_data(small_df.copy(), params)
    merged = align_timeframes(small_df, large_df, params.large_timeframe)

    trades = []
    current_trade: Optional[Trade] = None
    large_signal_active = None

    capital = params.initial_capital
    funding_rate = _get_funding_rate(params, symbol)

    # 杠杆模式判断
    use_lev = params.use_leverage and params.leverage > 1.0

    for i in range(len(merged)):
        row = merged.iloc[i]
        prev_row = merged.iloc[i - 1] if i > 0 else None

        # === 更新大周期信号 ===
        if pd.notna(row['large_touch_upper']) and row['large_touch_upper']:
            large_signal_active = 'short'
        elif pd.notna(row['large_touch_lower']) and row['large_touch_lower']:
            large_signal_active = 'long'

        # === 管理持仓 ===
        if current_trade is not None:
            trade = current_trade
            high = row['high']
            low = row['low']
            close = row['close']

            # === 杠杆模式：检查资金费率（每8小时结算）===
            if use_lev and params.use_funding_rate and is_funding_time(row['datetime']):
                current_pos_value = abs(trade.size) * close
                fee = calc_funding_fee(current_pos_value, funding_rate, trade.direction)
                trade.funding_fees += fee
                capital -= fee  # 资金费从账户扣除

            # === 杠杆模式：检查强平 ===
            if use_lev and not trade.is_liquidated:
                # 全仓模式：动态计算强平价（考虑当前账户余额）
                if params.margin_mode == 'cross':
                    # 可用余额 = 总资金 - 已占用保证金 + 当前仓位未实现盈亏
                    unrealized_pnl = _calc_unrealized_pnl(trade, close)
                    available_balance = capital - trade.margin + unrealized_pnl
                    trade.liquidation_price = calc_liquidation_price_cross(
                        trade.entry_price, abs(trade.size), trade.direction,
                        trade.leverage, symbol, max(0, available_balance), params.fee_rate
                    )

                # 检查是否触发强平
                if trade.direction == 'long' and low <= trade.liquidation_price:
                    # 强平
                    trade.is_liquidated = True
                    trade.exit_time = row['datetime']
                    trade.exit_price = trade.liquidation_price
                    trade.exit_reason = "⚠ 强制平仓(爆仓)"
                    # 强平清算费
                    trade.liquidation_fee = calc_liquidation_fee(abs(trade.size) * trade.liquidation_price)
                    # 注意：用 += 保留TP1已实现盈亏；size是剩余仓位
                    trade.pnl += (trade.exit_price - trade.entry_price) * trade.size
                    trade.pnl -= trade.liquidation_fee
                    trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
                    capital += trade.pnl
                    trade.pnl_pct = trade.pnl / params.initial_capital * 100
                    trades.append(trade)
                    current_trade = None
                    continue

                elif trade.direction == 'short' and high >= trade.liquidation_price:
                    trade.is_liquidated = True
                    trade.exit_time = row['datetime']
                    trade.exit_price = trade.liquidation_price
                    trade.exit_reason = "⚠ 强制平仓(爆仓)"
                    trade.liquidation_fee = calc_liquidation_fee(abs(trade.size) * trade.liquidation_price)
                    trade.pnl += (trade.entry_price - trade.exit_price) * trade.size
                    trade.pnl -= trade.liquidation_fee
                    trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
                    capital += trade.pnl
                    trade.pnl_pct = trade.pnl / params.initial_capital * 100
                    trades.append(trade)
                    current_trade = None
                    continue

            # === 正常止损/止盈逻辑 ===
            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    trade.exit_time = row['datetime']
                    trade.exit_price = trade.stop_loss
                    trade.exit_reason = "止损" if not trade.breakeven_set else "保本止损"
                    trade.pnl += (trade.exit_price - trade.entry_price) * trade.size
                    trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
                    capital += trade.pnl
                    trade.pnl_pct = trade.pnl / params.initial_capital * 100
                    trades.append(trade)
                    current_trade = None

                elif not trade.tp1_hit and high >= trade.take_profit_1:
                    trade.tp1_hit = True
                    half_size = trade.size * params.tp1_close_ratio
                    tp1_pnl = (trade.take_profit_1 - trade.entry_price) * half_size
                    tp1_pnl -= trade.take_profit_1 * half_size * params.fee_rate
                    capital += tp1_pnl
                    trade.size -= half_size
                    trade.pnl += tp1_pnl
                    # 杠杆模式：平半仓后释放部分保证金
                    if use_lev:
                        released_margin = trade.margin * params.tp1_close_ratio
                        trade.margin -= released_margin

                elif not trade.breakeven_set and trade.tp1_hit:
                    current_rr = (high - trade.entry_price) / (trade.entry_price - trade.initial_stop)
                    if current_rr >= params.tp2_ratio:
                        trade.breakeven_set = True
                        trade.stop_loss = trade.entry_price

                elif params.use_bb_mid_exit and pd.notna(row['large_bb_mid']) and high >= row['large_bb_mid']:
                    trade.exit_time = row['datetime']
                    trade.exit_price = close
                    trade.exit_reason = "布林带中轨止盈"
                    trade.pnl += (trade.exit_price - trade.entry_price) * trade.size
                    trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
                    capital += trade.pnl
                    trade.pnl_pct = trade.pnl / params.initial_capital * 100
                    trade.rr = (trade.exit_price - trade.entry_price) / (trade.entry_price - trade.initial_stop) if (trade.entry_price - trade.initial_stop) != 0 else 0
                    trades.append(trade)
                    current_trade = None

            elif trade.direction == 'short':
                if high >= trade.stop_loss:
                    trade.exit_time = row['datetime']
                    trade.exit_price = trade.stop_loss
                    trade.exit_reason = "止损" if not trade.breakeven_set else "保本止损"
                    trade.pnl += (trade.entry_price - trade.exit_price) * trade.size
                    trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
                    capital += trade.pnl
                    trade.pnl_pct = trade.pnl / params.initial_capital * 100
                    trades.append(trade)
                    current_trade = None

                elif not trade.tp1_hit and low <= trade.take_profit_1:
                    trade.tp1_hit = True
                    half_size = trade.size * params.tp1_close_ratio
                    tp1_pnl = (trade.entry_price - trade.take_profit_1) * half_size
                    tp1_pnl -= trade.take_profit_1 * half_size * params.fee_rate
                    capital += tp1_pnl
                    trade.size -= half_size
                    trade.pnl += tp1_pnl
                    if use_lev:
                        released_margin = trade.margin * params.tp1_close_ratio
                        trade.margin -= released_margin

                elif not trade.breakeven_set and trade.tp1_hit:
                    current_rr = (trade.entry_price - low) / (trade.initial_stop - trade.entry_price)
                    if current_rr >= params.tp2_ratio:
                        trade.breakeven_set = True
                        trade.stop_loss = trade.entry_price

                elif params.use_bb_mid_exit and pd.notna(row['large_bb_mid']) and low <= row['large_bb_mid']:
                    trade.exit_time = row['datetime']
                    trade.exit_price = close
                    trade.exit_reason = "布林带中轨止盈"
                    trade.pnl += (trade.entry_price - trade.exit_price) * trade.size
                    trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
                    capital += trade.pnl
                    trade.pnl_pct = trade.pnl / params.initial_capital * 100
                    trade.rr = (trade.entry_price - trade.exit_price) / (trade.initial_stop - trade.entry_price) if (trade.initial_stop - trade.entry_price) != 0 else 0
                    trades.append(trade)
                    current_trade = None

        # === 检查进场信号 ===
        if current_trade is None and large_signal_active is not None and prev_row is not None:
            if large_signal_active == 'long':
                golden_cross = prev_row['macd_golden_cross'] if 'macd_golden_cross' in prev_row else False
                breakout = row['close'] > prev_row['swing_high']

                signal_strength = 2 if (params.use_near_zero_filter and prev_row.get('macd_near_zero', False)) else 1

                if golden_cross and breakout and pd.notna(prev_row['atr']):
                    entry_price = row['close'] * (1 + params.slippage)
                    atr_val = prev_row['atr']

                    stop_atr = entry_price - params.stop_atr_mult * atr_val
                    stop_swing = prev_row['swing_low']
                    stop_loss = min(stop_atr, stop_swing) - params.stop_atr_buffer * atr_val

                    risk_amount = capital * params.risk_percent / 100
                    stop_distance = entry_price - stop_loss

                    if stop_distance > 0:
                        if use_lev:
                            # 杠杆模式
                            size, pos_value, margin, actual_lev, limited, reason = _calc_position_size_with_leverage(
                                capital, risk_amount, stop_distance, entry_price, params.leverage, symbol
                            )
                            leverage_used = actual_lev
                            # 计算强平价
                            liq_price = calc_liquidation_price_cross(
                                entry_price, abs(size), 'long', actual_lev, symbol, 0, params.fee_rate
                            )
                            # 获取维持保证金阶梯
                            _, _, tier = get_maintenance_margin_rate(symbol, pos_value)
                        else:
                            # 无杠杆
                            size = risk_amount / stop_distance
                            pos_value = size * entry_price
                            margin = pos_value
                            leverage_used = 1.0
                            liq_price = 0.0
                            tier = 1

                        tp1 = entry_price + stop_distance * params.tp1_ratio

                        current_trade = Trade(
                            entry_time=row['datetime'],
                            entry_price=entry_price,
                            direction='long',
                            size=size,
                            stop_loss=stop_loss,
                            initial_stop=stop_loss,
                            take_profit_1=tp1,
                            risk_amount=risk_amount,
                            signal_strength=signal_strength,
                            leverage=leverage_used,
                            margin=margin,
                            position_value=pos_value,
                            liquidation_price=liq_price,
                            margin_ratio_at_entry=margin / pos_value if pos_value > 0 else 0,
                            mmr_tier=tier,
                        )
                        # 进场手续费
                        capital -= entry_price * abs(size) * params.fee_rate
                        # 杠杆模式：扣除保证金（全仓模式下保证金仍属于账户，但锁定）
                        large_signal_active = None

            elif large_signal_active == 'short':
                death_cross = prev_row['macd_death_cross'] if 'macd_death_cross' in prev_row else False
                breakout = row['close'] < prev_row['swing_low']

                signal_strength = 2 if (params.use_near_zero_filter and prev_row.get('macd_near_zero', False)) else 1

                if death_cross and breakout and pd.notna(prev_row['atr']):
                    entry_price = row['close'] * (1 - params.slippage)
                    atr_val = prev_row['atr']

                    stop_atr = entry_price + params.stop_atr_mult * atr_val
                    stop_swing = prev_row['swing_high']
                    stop_loss = max(stop_atr, stop_swing) + params.stop_atr_buffer * atr_val

                    risk_amount = capital * params.risk_percent / 100
                    stop_distance = stop_loss - entry_price

                    if stop_distance > 0:
                        if use_lev:
                            size, pos_value, margin, actual_lev, limited, reason = _calc_position_size_with_leverage(
                                capital, risk_amount, stop_distance, entry_price, params.leverage, symbol
                            )
                            leverage_used = actual_lev
                            liq_price = calc_liquidation_price_cross(
                                entry_price, abs(size), 'short', actual_lev, symbol, 0, params.fee_rate
                            )
                            _, _, tier = get_maintenance_margin_rate(symbol, pos_value)
                        else:
                            size = risk_amount / stop_distance
                            pos_value = size * entry_price
                            margin = pos_value
                            leverage_used = 1.0
                            liq_price = 0.0
                            tier = 1

                        tp1 = entry_price - stop_distance * params.tp1_ratio

                        current_trade = Trade(
                            entry_time=row['datetime'],
                            entry_price=entry_price,
                            direction='short',
                            size=size,
                            stop_loss=stop_loss,
                            initial_stop=stop_loss,
                            take_profit_1=tp1,
                            risk_amount=risk_amount,
                            signal_strength=signal_strength,
                            leverage=leverage_used,
                            margin=margin,
                            position_value=pos_value,
                            liquidation_price=liq_price,
                            margin_ratio_at_entry=margin / pos_value if pos_value > 0 else 0,
                            mmr_tier=tier,
                        )
                        capital -= entry_price * abs(size) * params.fee_rate
                        large_signal_active = None

    # 回测结束时还有持仓，按最后收盘价平仓
    if current_trade is not None:
        trade = current_trade
        last_row = merged.iloc[-1]
        trade.exit_time = last_row['datetime']
        trade.exit_price = last_row['close']
        trade.exit_reason = "回测结束平仓"
        if trade.direction == 'long':
            trade.pnl += (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.pnl += (trade.entry_price - trade.exit_price) * trade.size
        trade.pnl -= trade.exit_price * abs(trade.size) * params.fee_rate
        trade.pnl_pct = trade.pnl / params.initial_capital * 100
        trades.append(trade)

    return trades


def _calc_unrealized_pnl(trade: Trade, current_price: float) -> float:
    """计算未实现盈亏"""
    if trade.direction == 'long':
        return (current_price - trade.entry_price) * trade.size
    else:
        return (trade.entry_price - current_price) * trade.size
