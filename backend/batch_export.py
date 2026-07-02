"""
批量下载多币种K线数据 + 运行回测 + 导出CSV
为GitHub Pages静态部署准备完整数据
"""
import sys
import os
import json
import csv
import shutil
from pathlib import Path
from dataclasses import asdict

# 设置路径
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from data_downloader import download_klines, load_klines
from strategy import StrategyParams, run_strategy
from backtest import run_backtest
from leverage_report import generate_leverage_report, report_to_dict

# 主流币种列表（按市值排序，排除已下载的BTC）
SYMBOLS = [
    ("ETH/USDT", "ETH_USDT"),
    ("BNB/USDT", "BNB_USDT"),
    ("SOL/USDT", "SOL_USDT"),
    ("XRP/USDT", "XRP_USDT"),
    ("ADA/USDT", "ADA_USDT"),
    ("DOGE/USDT", "DOGE_USDT"),
    ("AVAX/USDT", "AVAX_USDT"),
    ("DOT/USDT", "DOT_USDT"),
    ("LINK/USDT", "LINK_USDT"),
    ("LTC/USDT", "LTC_USDT"),
]

# 输出目录
DOCS_DATA_DIR = BACKEND_DIR.parent / "docs" / "data"
DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)


def export_csv(filename: str, rows: list, fieldnames: list = None):
    """导出CSV到docs/data目录"""
    filepath = DOCS_DATA_DIR / filename
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if isinstance(rows[0], dict) else None
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  导出: {filename} ({len(rows)}行)")


def run_backtest_for_symbol(symbol: str, use_leverage: bool = False, leverage: float = 10.0):
    """为指定币种运行回测"""
    sym_file = symbol.replace("/", "_")
    prefix = f"leverage_{leverage}x_" if use_leverage else "backtest_"
    lev_suffix = f"_lev{leverage}x" if use_leverage else ""

    print(f"\n=== {symbol} {'杠杆'+str(leverage)+'x' if use_leverage else '无杠杆'} ===")

    # 加载数据检查
    try:
        df_large = load_klines(symbol, "1h")
        df_small = load_klines(symbol, "5m")
    except Exception as e:
        print(f"  跳过: 数据未找到 - {e}")
        return None

    if df_large is None or df_small is None or len(df_large) < 50:
        print(f"  跳过: 数据不足 (large={len(df_large) if df_large is not None else 0})")
        return None

    # 构建参数
    params = StrategyParams(
        large_timeframe="1h",
        bb_period=20,
        bb_std=2.0,
        small_timeframe="5m",
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        swing_lookback=10,
        atr_period=14,
        stop_atr_mult=2.0,
        stop_atr_buffer=0.5,
        risk_percent=2.0,
        tp1_ratio=1.0,
        tp1_close_ratio=0.5,
        tp2_ratio=2.0,
        use_bb_mid_exit=True,
        use_near_zero_filter=True,
        initial_capital=100000.0,
        fee_rate=0.0004,
        slippage=0.0002,
        use_leverage=use_leverage,
        leverage=leverage,
        margin_mode="cross",
        use_funding_rate=True,
        funding_rate_override=-1,
    )

    # 运行回测（使用90天数据，与下载的天数一致）
    result = run_backtest(symbol, params, days=90)

    # 导出统计
    stats = {
        "symbol": symbol,
        "use_leverage": use_leverage,
        "leverage": leverage if use_leverage else 1,
        "total_return": result.total_return,
        "final_capital": result.final_capital,
        "annual_return": result.annual_return,
        "total_pnl": result.total_pnl,
        "total_trades": result.total_trades,
        "win_trades": result.win_trades,
        "loss_trades": result.loss_trades,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "long_trades": result.long_trades,
        "short_trades": result.short_trades,
        "liquidation_count": result.liquidation_count,
        "total_funding_fees": result.total_funding_fees,
        "max_position_value": result.max_position_value,
    }

    # 导出资金曲线
    equity_rows = []
    for i, point in enumerate(result.equity_curve):
        equity_rows.append({
            "index": i,
            "datetime": point.get("datetime", ""),
            "equity": point.get("equity", 0),
        })

    # 导出回撤曲线
    drawdown_rows = []
    for i, point in enumerate(result.drawdown_curve):
        drawdown_rows.append({
            "index": i,
            "datetime": point.get("datetime", ""),
            "drawdown": point.get("drawdown", 0),
        })

    # 导出交易记录（trades已经是dict列表）
    trade_rows = []
    for t in result.trades:
        trade_rows.append({
            "entry_time": t.get("entry_time", ""),
            "exit_time": t.get("exit_time", ""),
            "side": t.get("side", ""),
            "entry_price": t.get("entry_price", 0),
            "exit_price": t.get("exit_price", 0),
            "size": t.get("size", 0),
            "pnl": t.get("pnl", 0),
            "return_pct": t.get("return_pct", 0),
            "bars_held": t.get("bars_held", 0),
            "exit_reason": t.get("exit_reason", ""),
            "leverage": t.get("leverage", 1) if use_leverage else 1,
            "margin": t.get("margin", 0) if use_leverage else 0,
            "is_liquidated": t.get("is_liquidated", False) if use_leverage else False,
        })

    # 导出文件
    export_csv(f"{prefix}stats_{sym_file}{lev_suffix}.csv", [stats])
    export_csv(f"{prefix}equity_{sym_file}{lev_suffix}.csv", equity_rows)
    export_csv(f"{prefix}drawdown_{sym_file}{lev_suffix}.csv", drawdown_rows)
    export_csv(f"{prefix}trades_{sym_file}{lev_suffix}.csv", trade_rows)

    # 杠杆报告
    if use_leverage:
        report = generate_leverage_report(result)
        report_dict = report_to_dict(report)
        report_file = DOCS_DATA_DIR / f"leverage_report_{sym_file}{lev_suffix}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        print(f"  导出: leverage_report_{sym_file}{lev_suffix}.json")

        # 风险事件CSV
        events_rows = []
        for ev in report_dict.get("events", []):
            events_rows.append({
                "type": ev.get("type", ""),
                "severity": ev.get("severity", ""),
                "title": ev.get("title", ""),
                "description": ev.get("description", ""),
                "suggestion": ev.get("suggestion", ""),
            })
        export_csv(f"leverage_events_{sym_file}{lev_suffix}.csv", events_rows)

    print(f"  完成: 收益{result.total_return:+.2f}% 交易{result.total_trades}笔 胜率{result.win_rate}%")
    return result


def main():
    print("=" * 60)
    print("批量下载多币种数据 + 生成回测结果")
    print("=" * 60)

    # 第1步：下载K线数据
    print("\n[1/3] 下载K线数据...")
    for symbol, sym_file in SYMBOLS:
        for tf, tf_name, days in [("1h", "1h", 90), ("5m", "5m", 90)]:
            local_path = BACKEND_DIR.parent / "data" / f"{sym_file}_{tf}.csv"
            if local_path.exists():
                print(f"  跳过(已存在): {symbol} {tf}")
                continue
            print(f"  下载: {symbol} {tf}...")
            try:
                df = download_klines(symbol, tf, days)
                if df is not None and len(df) > 0:
                    print(f"    ✓ {len(df)}条")
                else:
                    print(f"    ✗ 失败")
            except Exception as e:
                print(f"    ✗ 错误: {e}")

    # 第2步：为每个币种运行回测（无杠杆 + 10x杠杆）
    print("\n[2/3] 运行回测并导出CSV...")
    all_symbols = [("BTC/USDT", "BTC_USDT")] + SYMBOLS
    for symbol, sym_file in all_symbols:
        # 检查数据是否存在
        large_path = BACKEND_DIR.parent / "data" / f"{sym_file}_1h.csv"
        small_path = BACKEND_DIR.parent / "data" / f"{sym_file}_5m.csv"
        if not large_path.exists() or not small_path.exists():
            print(f"\n跳过 {symbol}: 缺少K线数据")
            continue

        # 无杠杆回测
        run_backtest_for_symbol(symbol, use_leverage=False)

        # 10x杠杆回测
        run_backtest_for_symbol(symbol, use_leverage=True, leverage=10.0)

    # 第3步：复制K线原始数据到docs/data供下载
    print("\n[3/3] 复制K线原始数据到docs/data...")
    data_dir = BACKEND_DIR.parent / "data"
    copied = 0
    for f in data_dir.glob("*.csv"):
        dest = DOCS_DATA_DIR / f.name
        shutil.copy2(f, dest)
        copied += 1
        print(f"  复制: {f.name}")
    print(f"  共复制 {copied} 个K线数据文件")

    # 生成数据清单
    print("\n[4/4] 生成数据清单...")
    kline_files = []
    for f in sorted(DOCS_DATA_DIR.glob("*.csv")):
        # 只列出K线数据（包含_open等字段的）
        if any(x in f.name for x in ["_1h.csv", "_4h.csv", "_5m.csv", "_15m.csv", "_1d.csv"]):
            size_kb = round(f.stat().st_size / 1024, 1)
            # 读取行数
            with open(f, "r", encoding="utf-8") as fp:
                rows = sum(1 for _ in fp) - 1
            # 解析symbol和timeframe
            name = f.stem  # e.g. BTC_USDT_1h
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                sym = parts[0].replace("_", "/")
                tf = parts[1]
            else:
                sym = name
                tf = "unknown"
            kline_files.append({
                "file": f.name,
                "symbol": sym,
                "timeframe": tf,
                "rows": rows,
                "size_kb": size_kb,
            })

    # 保存为JSON清单
    manifest_file = DOCS_DATA_DIR / "kline_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(kline_files, f, ensure_ascii=False, indent=2)
    print(f"  生成: kline_manifest.json ({len(kline_files)}个K线数据文件)")

    print("\n" + "=" * 60)
    print("全部完成！")
    print(f"输出目录: {DOCS_DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
