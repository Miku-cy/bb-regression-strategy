"""
技术指标计算模块 - 纯 pandas/numpy 实现，无外部 C 依赖
包含：布林带、MACD、ATR
"""
import pandas as pd
import numpy as np


def bollinger_bands(df: pd.DataFrame, period: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    """
    计算布林带指标
    :param df: 含 'close' 列的 DataFrame
    :param period: 布林带周期
    :param std_mult: 标准差倍数
    :return: 增加 bb_mid, bb_upper, bb_lower, bb_std 列
    """
    close = df['close']
    bb_mid = close.rolling(window=period, min_periods=period).mean()
    bb_std = close.rolling(window=period, min_periods=period).std(ddof=0)
    bb_upper = bb_mid + std_mult * bb_std
    bb_lower = bb_mid - std_mult * bb_std

    df = df.copy()
    df['bb_mid'] = bb_mid
    df['bb_upper'] = bb_upper
    df['bb_lower'] = bb_lower
    df['bb_std'] = bb_std
    df['bb_width'] = (bb_upper - bb_lower) / bb_mid
    return df


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    计算MACD指标
    :param df: 含 'close' 列的 DataFrame
    :param fast: 快线周期
    :param slow: 慢线周期
    :param signal: 信号线周期
    :return: 增加 macd, macd_signal, macd_hist 列
    """
    close = df['close']
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    df = df.copy()
    df['macd'] = macd_line
    df['macd_signal'] = signal_line
    df['macd_hist'] = hist
    return df


def atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算ATR (Average True Range)
    :param df: 含 high, low, close 列的 DataFrame
    :param period: ATR周期
    :return: 增加 atr 列
    """
    high = df['high']
    low = df['low']
    close = df['close']

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_val = tr.ewm(alpha=1/period, adjust=False).mean()

    df = df.copy()
    df['atr'] = atr_val
    df['tr'] = tr
    return df


def find_swing_high_low(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """
    寻找震荡区域的最高点和最低点
    :param df: DataFrame
    :param lookback: 回看周期
    :return: 增加 swing_high, swing_low 列
    """
    df = df.copy()
    df['swing_high'] = df['high'].rolling(window=lookback, min_periods=1).max()
    df['swing_low'] = df['low'].rolling(window=lookback, min_periods=1).min()
    return df


def detect_macd_cross(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测MACD金叉/死叉信号
    :return: 增加 macd_golden_cross, macd_death_cross, macd_near_zero 列
    """
    df = df.copy()
    macd_line = df['macd']
    signal_line = df['macd_signal']

    prev_diff = (macd_line - signal_line).shift(1)
    curr_diff = macd_line - signal_line

    df['macd_golden_cross'] = (prev_diff <= 0) & (curr_diff > 0)
    df['macd_death_cross'] = (prev_diff >= 0) & (curr_diff < 0)

    # MACD线接近0轴判断（信号强弱）
    macd_abs = macd_line.abs()
    recent_max = macd_abs.rolling(window=50, min_periods=1).max()
    df['macd_near_zero'] = macd_abs < (recent_max * 0.15)
    df['macd_signal_strength'] = np.where(df['macd_near_zero'], 2, 1)

    return df
