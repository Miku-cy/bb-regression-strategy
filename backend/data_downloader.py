"""
Binance 数据下载模块
直接使用 Binance REST API 下载K线数据并缓存到本地 CSV
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Binance API 基础 URL（多个备用域名）
BINANCE_API_DOMAINS = [
    'https://api.binance.com',
    'https://api1.binance.com',
    'https://api2.binance.com',
    'https://api3.binance.com',
    'https://api4.binance.com',
]

# 支持的交易对
SUPPORTED_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "LTC/USDT", "TRX/USDT", "ATOM/USDT", "NEAR/USDT"
]

# 支持的时间周期
SUPPORTED_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]


def _get_working_domain() -> str:
    """测试并返回可用的 Binance API 域名"""
    for domain in BINANCE_API_DOMAINS:
        try:
            resp = requests.get(f"{domain}/api/v3/ping", timeout=5)
            if resp.status_code == 200:
                print(f"✓ 使用 Binance API: {domain}")
                return domain
        except:
            continue
    print("⚠ 所有 Binance API 域名均无法访问，使用默认域名")
    return BINANCE_API_DOMAINS[0]


def _csv_path(symbol: str, timeframe: str) -> Path:
    """获取CSV缓存路径"""
    safe_name = symbol.replace("/", "_")
    return DATA_DIR / f"{safe_name}_{timeframe}.csv"


def download_klines(symbol: str, timeframe: str, days: int = 365) -> pd.DataFrame:
    """
    下载K线数据（直接使用 Binance REST API）
    :param symbol: 交易对，如 BTC/USDT
    :param timeframe: 时间周期，如 1h
    :param days: 下载天数
    :return: DataFrame
    """
    domain = _get_working_domain()
    pair = symbol.replace("/", "").upper()

    end_time = int(datetime.utcnow().timestamp() * 1000)
    start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)

    all_data = []
    current_start = start_time

    print(f"开始下载 {symbol} {timeframe} ({days}天)...")

    while current_start < end_time:
        try:
            url = f"{domain}/api/v3/klines"
            params = {
                'symbol': pair,
                'interval': timeframe,
                'startTime': current_start,
                'limit': 1000
            }
            resp = requests.get(url, params=params, timeout=30)

            if resp.status_code != 200:
                print(f"API 返回错误 {resp.status_code}: {resp.text[:100]}")
                break

            data = resp.json()
            if not data:
                break

            all_data.extend(data)
            # 下一批从最后一条数据的 close_time + 1 开始
            current_start = data[-1][6] + 1
            print(f"  已下载 {len(all_data)} 条...", end='\r')

            # 避免API限频
            time.sleep(0.15)

        except Exception as e:
            print(f"\n下载出错: {e}")
            break

    if not all_data:
        print(f"未获取到 {symbol} {timeframe} 数据")
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])

    # 转换数据类型
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df['timestamp'] = df['open_time']
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df[['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']]
    df = df.drop_duplicates(subset='timestamp').reset_index(drop=True)

    # 保存到本地
    csv_path = _csv_path(symbol, timeframe)
    df.to_csv(csv_path, index=False)
    print(f"\n✓ 已保存 {len(df)} 条数据到 {csv_path}")
    return df


def load_klines(symbol: str, timeframe: str) -> pd.DataFrame:
    """
    加载本地K线数据
    """
    csv_path = _csv_path(symbol, timeframe)
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    return pd.DataFrame()


def ensure_data(symbol: str, timeframe: str, days: int = 365) -> pd.DataFrame:
    """
    确保数据存在：先尝试加载本地，不存在则下载
    """
    df = load_klines(symbol, timeframe)
    if df.empty:
        print(f"本地无 {symbol} {timeframe} 数据，开始下载...")
        df = download_klines(symbol, timeframe, days)
    return df


def list_local_data() -> list:
    """列出本地已有的数据文件"""
    files = []
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.csv"):
            name = f.stem
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                symbol = parts[0].replace("_", "/")
                timeframe = parts[1]
                size = f.stat().st_size
                files.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "file": str(f),
                    "size_kb": round(size / 1024, 1)
                })
    return files


def delete_local_data(symbol: str, timeframe: str) -> bool:
    """删除本地数据"""
    csv_path = _csv_path(symbol, timeframe)
    if csv_path.exists():
        csv_path.unlink()
        return True
    return False
