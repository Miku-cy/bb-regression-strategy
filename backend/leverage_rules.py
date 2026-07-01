"""
币安USDT永续合约规则模块
实现真实的杠杆规则：阶梯维持保证金率、强平价计算、资金费率
参考: https://www.binance.com/zh-CN/futures/funding-history/perpetual/quarterly
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ===== 币安USDT永续合约阶梯维持保证金率 =====
# 数据来源: Binance Futures 官方规则 (2024-2025)
# 每个币种有不同的阶梯，这里使用通用阶梯 + BTC/ETH专用阶梯

# BTCUSDT 维持保证金阶梯 (仓位价值 USDT)
BTC_MMR_TIERS = [
    {"bracket": 1, "notional_floor": 0,         "notional_cap": 50_000,      "maintenance_margin_rate": 0.004, "max_leverage": 125},
    {"bracket": 2, "notional_floor": 50_000,    "notional_cap": 250_000,     "maintenance_margin_rate": 0.005, "max_leverage": 100},
    {"bracket": 3, "notional_floor": 250_000,   "notional_cap": 1_000_000,   "maintenance_margin_rate": 0.010, "max_leverage": 50},
    {"bracket": 4, "notional_floor": 1_000_000, "notional_cap": 5_000_000,   "maintenance_margin_rate": 0.025, "max_leverage": 20},
    {"bracket": 5, "notional_floor": 5_000_000, "notional_cap": 20_000_000,  "maintenance_margin_rate": 0.050, "max_leverage": 10},
    {"bracket": 6, "notional_floor": 20_000_000,"notional_cap": 50_000_000,  "maintenance_margin_rate": 0.100, "max_leverage": 5},
    {"bracket": 7, "notional_floor": 50_000_000,"notional_cap": 100_000_000, "maintenance_margin_rate": 0.150, "max_leverage": 4},
    {"bracket": 8, "notional_floor": 100_000_000,"notional_cap": 200_000_000,"maintenance_margin_rate": 0.250, "max_leverage": 3},
    {"bracket": 9, "notional_floor": 200_000_000,"notional_cap": float('inf'),"maintenance_margin_rate": 0.500, "max_leverage": 2},
]

# ETHUSDT 维持保证金阶梯
ETH_MMR_TIERS = [
    {"bracket": 1, "notional_floor": 0,         "notional_cap": 50_000,      "maintenance_margin_rate": 0.005, "max_leverage": 75},
    {"bracket": 2, "notional_floor": 50_000,    "notional_cap": 250_000,     "maintenance_margin_rate": 0.006, "max_leverage": 50},
    {"bracket": 3, "notional_floor": 250_000,   "notional_cap": 1_000_000,   "maintenance_margin_rate": 0.012, "max_leverage": 25},
    {"bracket": 4, "notional_floor": 1_000_000, "notional_cap": 5_000_000,   "maintenance_margin_rate": 0.025, "max_leverage": 10},
    {"bracket": 5, "notional_floor": 5_000_000, "notional_cap": 20_000_000,  "maintenance_margin_rate": 0.050, "max_leverage": 5},
    {"bracket": 6, "notional_floor": 20_000_000,"notional_cap": float('inf'),"maintenance_margin_rate": 0.100, "max_leverage": 2},
]

# 通用币种维持保证金阶梯 (适用于其他山寨币)
DEFAULT_MMR_TIERS = [
    {"bracket": 1, "notional_floor": 0,         "notional_cap": 5_000,       "maintenance_margin_rate": 0.012, "max_leverage": 50},
    {"bracket": 2, "notional_floor": 5_000,     "notional_cap": 25_000,      "maintenance_margin_rate": 0.025, "max_leverage": 25},
    {"bracket": 3, "notional_floor": 25_000,    "notional_cap": 100_000,     "maintenance_margin_rate": 0.050, "max_leverage": 10},
    {"bracket": 4, "notional_floor": 100_000,   "notional_cap": 500_000,     "maintenance_margin_rate": 0.100, "max_leverage": 5},
    {"bracket": 5, "notional_floor": 500_000,   "notional_cap": 2_000_000,   "maintenance_margin_rate": 0.150, "max_leverage": 3},
    {"bracket": 6, "notional_floor": 2_000_000, "notional_cap": 5_000_000,   "maintenance_margin_rate": 0.250, "max_leverage": 2},
    {"bracket": 7, "notional_floor": 5_000_000, "notional_cap": float('inf'),"maintenance_margin_rate": 0.500, "max_leverage": 1},
]


def get_mmr_tiers(symbol: str) -> list:
    """根据交易对获取对应的维持保证金阶梯"""
    pair = symbol.replace("/", "").upper()
    if pair.startswith("BTC"):
        return BTC_MMR_TIERS
    elif pair.startswith("ETH"):
        return ETH_MMR_TIERS
    return DEFAULT_MMR_TIERS


def get_maintenance_margin_rate(symbol: str, notional_value: float) -> tuple:
    """
    根据仓位价值获取维持保证金率
    :return: (维持保证金率, 最大允许杠杆, 阶梯编号)
    """
    tiers = get_mmr_tiers(symbol)
    for tier in tiers:
        if tier["notional_floor"] <= notional_value < tier["notional_cap"]:
            return tier["maintenance_margin_rate"], tier["max_leverage"], tier["bracket"]
    # 默认返回最高阶梯
    last = tiers[-1]
    return last["maintenance_margin_rate"], last["max_leverage"], last["bracket"]


def get_max_leverage(symbol: str, notional_value: float) -> int:
    """获取允许的最大杠杆"""
    _, max_lev, _ = get_maintenance_margin_rate(symbol, notional_value)
    return max_lev


def calc_initial_margin(position_value: float, leverage: float) -> float:
    """
    计算初始保证金
    :param position_value: 仓位价值 (数量 × 价格)
    :param leverage: 杠杆倍数
    :return: 初始保证金
    """
    return position_value / leverage


def calc_liquidation_price_cross(
    entry_price: float,
    quantity: float,
    direction: str,
    leverage: float,
    symbol: str,
    available_balance: float,
    taker_fee_rate: float = 0.0004,
) -> float:
    """
    计算全仓交叉保证金模式的强平价格
    币安真实公式推导：
    强平条件：账户权益 = 维持保证金 + 平仓手续费
    账户权益 = 总保证金 + 未实现盈亏
    总保证金 = 初始保证金 + 可用余额 - 开仓手续费

    多头强平价（liq_price < entry_price）:
        total_margin + (liq_price - entry_price) × qty = liq_price × qty × mmr + liq_price × qty × fee_rate
        化简: liq_price = (entry_price × qty - total_margin) / (qty × (1 - mmr - fee_rate))

    空头强平价（liq_price > entry_price）:
        total_margin + (entry_price - liq_price) × qty = liq_price × qty × mmr + liq_price × qty × fee_rate
        化简: liq_price = (entry_price × qty + total_margin) / (qty × (1 + mmr + fee_rate))

    :param entry_price: 入场价
    :param quantity: 仓位数量
    :param direction: 'long' or 'short'
    :param leverage: 杠杆倍数
    :param symbol: 交易对
    :param available_balance: 可用余额（全仓模式下的额外保证金）
    :param taker_fee_rate: Taker手续费率
    :return: 强平价格
    """
    qty = abs(quantity)
    if qty == 0:
        return 0.0

    position_value = qty * entry_price
    mmr, _, _ = get_maintenance_margin_rate(symbol, position_value)

    # 初始保证金
    initial_margin = calc_initial_margin(position_value, leverage)
    # 开仓手续费
    open_fee = position_value * taker_fee_rate
    # 全仓模式：可用保证金 = 初始保证金 + 可用余额 - 开仓手续费
    total_margin = initial_margin + max(0, available_balance) - open_fee

    if direction == 'long':
        # 多头强平价（低于入场价）
        # liq_price = (entry_price × qty - total_margin) / (qty × (1 - mmr - fee_rate))
        denominator = qty * (1 - mmr - taker_fee_rate)
        if denominator <= 0:
            # 维持保证金率+手续费率过高，不会强平
            return 0.0
        liq_price = (entry_price * qty - total_margin) / denominator
    else:
        # 空头强平价（高于入场价）
        # liq_price = (entry_price × qty + total_margin) / (qty × (1 + mmr + fee_rate))
        denominator = qty * (1 + mmr + taker_fee_rate)
        liq_price = (entry_price * qty + total_margin) / denominator

    # 强平价不能为负
    return max(0.0, liq_price)


def calc_funding_fee(position_value: float, funding_rate: float, direction: str) -> float:
    """
    计算资金费率
    正资金费率：多方付给空方（多方支出，空方收入）
    负资金费率：空方付给多方（空方支出，多方收入）
    :param position_value: 仓位价值
    :param funding_rate: 资金费率（如 0.0001 = 0.01%）
    :param direction: 'long' or 'short'
    :return: 资金费（正数=支出，负数=收入）
    """
    if direction == 'long':
        return position_value * funding_rate  # 多方在正费率下支出
    else:
        return -position_value * funding_rate  # 空方在正费率下收入


def is_funding_time(timestamp: pd.Timestamp) -> bool:
    """
    判断是否是资金费率结算时间
    币安每8小时结算: 00:00, 08:00, 16:00 UTC
    """
    utc_hour = timestamp.hour
    utc_minute = timestamp.minute
    return utc_hour in [0, 8, 16] and utc_minute == 0


def get_default_funding_rate(symbol: str) -> float:
    """
    获取默认资金费率（历史平均值）
    实际应从API获取，这里使用各币种的历史平均
    """
    pair = symbol.replace("/", "").upper()
    funding_rates = {
        "BTCUSDT": 0.0001,   # 0.01%
        "ETHUSDT": 0.0001,
        "BNBUSDT": 0.0001,
        "SOLUSDT": 0.0001,
        "XRPUSDT": 0.0001,
        "ADAUSDT": 0.0001,
        "DOGEUSDT": 0.0002,
        "AVAXUSDT": 0.0001,
        "DOTUSDT": 0.0001,
        "LINKUSDT": 0.0001,
        "LTCUSDT": 0.0001,
        "TRXUSDT": 0.0001,
        "ATOMUSDT": 0.0001,
        "NEARUSDT": 0.0001,
    }
    return funding_rates.get(pair, 0.0001)


def calc_liquidation_fee(position_value: float) -> float:
    """
    计算强平清算费
    币安规定：强平会收取仓位价值0.5%的清算费
    """
    return position_value * 0.005


def validate_leverage(symbol: str, leverage: float, position_value: float) -> tuple:
    """
    验证杠杆是否在允许范围内
    :return: (实际杠杆, 是否被限制, 限制原因)
    """
    mmr, max_lev, bracket = get_maintenance_margin_rate(symbol, position_value)
    if leverage > max_lev:
        return float(max_lev), True, f"仓位价值{position_value:.0f}USDT对应阶梯{bracket}，最大允许杠杆{max_lev}x"
    return leverage, False, ""
