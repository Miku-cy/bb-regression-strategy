"""
导出回测API数据为CSV文件，用于GitHub Pages静态部署演示
生成两组数据：无杠杆回测 + 10x杠杆回测
"""
import sys
import csv
import json
import os
from pathlib import Path

# 添加后端路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from data_downloader import ensure_data, list_local_data
from strategy import StrategyParams
from backtest import run_backtest
from leverage_report import generate_leverage_report, report_to_dict


def csv_path(name: str) -> str:
    """获取CSV输出路径"""
    out_dir = Path(__file__).parent / "docs" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / name)


def write_csv(filename: str, rows: list, headers: list):
    """写入CSV文件"""
    path = csv_path(filename)
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"  ✓ {filename} ({len(rows)} 行)")


def export_backtest_result(result, prefix: str):
    """导出单个回测结果的所有CSV"""
    print(f"\n=== 导出 {prefix} 回测数据 ===")

    # 1. 统计摘要（单行）
    stats_row = {
        "symbol": result.symbol,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_capital": round(result.final_capital, 2),
        "total_return": result.total_return,
        "total_pnl": round(result.total_pnl, 2),
        "annual_return": result.annual_return,
        "total_trades": result.total_trades,
        "win_trades": result.win_trades,
        "loss_trades": result.loss_trades,
        "win_rate": result.win_rate,
        "avg_win": round(result.avg_win, 2),
        "avg_loss": round(result.avg_loss, 2),
        "profit_factor": result.profit_factor,
        "max_win": round(result.max_win, 2),
        "max_loss": round(result.max_loss, 2),
        "avg_rr": result.avg_rr,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "avg_holding_bars": result.avg_holding_bars,
        "long_trades": result.long_trades,
        "short_trades": result.short_trades,
        "use_leverage": result.use_leverage,
        "leverage": result.leverage,
        "liquidation_count": result.liquidation_count,
        "total_funding_fees": round(result.total_funding_fees, 2),
        "total_liquidation_fees": round(result.total_liquidation_fees, 2),
        "max_position_value": round(result.max_position_value, 2),
        "avg_margin_used": round(result.avg_margin_used, 2),
        "max_margin_used": round(result.max_margin_used, 2),
        "leverage_amplification": result.leverage_amplification,
        "risk_per_trade_pct": result.risk_per_trade_pct,
    }
    write_csv(f"{prefix}_stats.csv", [stats_row], list(stats_row.keys()))

    # 2. 资金曲线
    eq_rows = [{"datetime": p["datetime"], "equity": p["equity"]} for p in result.equity_curve]
    write_csv(f"{prefix}_equity.csv", eq_rows, ["datetime", "equity"])

    # 3. 回撤曲线
    dd_rows = [{"datetime": p["datetime"], "drawdown": p["drawdown"]} for p in result.drawdown_curve]
    write_csv(f"{prefix}_drawdown.csv", dd_rows, ["datetime", "drawdown"])

    # 4. 交易记录
    trade_headers = [
        "entry_time", "exit_time", "direction", "entry_price", "exit_price",
        "size", "stop_loss", "initial_stop", "take_profit_1",
        "pnl", "pnl_pct", "rr", "exit_reason", "tp1_hit", "breakeven_set",
        "signal_strength", "leverage", "margin", "position_value",
        "liquidation_price", "funding_fees", "liquidation_fee",
        "is_liquidated", "margin_ratio_at_entry", "mmr_tier"
    ]
    trade_rows = []
    for t in result.trades:
        row = {}
        for h in trade_headers:
            val = t.get(h, "")
            if isinstance(val, bool):
                val = str(val).lower()
            if val is None:
                val = ""
            row[h] = val
        trade_rows.append(row)
    write_csv(f"{prefix}_trades.csv", trade_rows, trade_headers)


def export_leverage_report(result):
    """导出杠杆分析报告"""
    if not result.use_leverage:
        return

    print("\n=== 导出杠杆分析报告 ===")
    report = generate_leverage_report(result)
    report_dict = report_to_dict(report)

    # 报告摘要（单行）
    summary_row = {
        "risk_level": report_dict["risk_level"],
        "risk_score": report_dict["risk_score"],
        "max_loss_per_trade_pct": report_dict["max_loss_per_trade_pct"],
        "avg_loss_per_trade_pct": report_dict["avg_loss_per_trade_pct"],
        "liquidation_rate": report_dict["liquidation_rate"],
        "funding_fee_ratio": report_dict["funding_fee_ratio"],
        "margin_utilization": report_dict["margin_utilization"],
        "risk_reward_with_lev": report_dict["risk_reward_with_lev"],
        "summary": report_dict["summary"],
    }
    write_csv("leverage_summary.csv", [summary_row], list(summary_row.keys()))

    # 风险事件
    event_headers = ["severity", "category", "title", "description", "trade_index", "value", "suggestion"]
    event_rows = []
    for e in report_dict["events"]:
        event_rows.append({h: e.get(h, "") for h in event_headers})
    write_csv("leverage_events.csv", event_rows, event_headers)

    # 建议
    rec_rows = [{"index": i, "recommendation": r} for i, r in enumerate(report_dict["recommendations"])]
    write_csv("leverage_recommendations.csv", rec_rows, ["index", "recommendation"])

    # 保存完整JSON报告（备用）
    json_path = csv_path("leverage_report_full.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)
    print(f"  ✓ leverage_report_full.json")


def export_local_data_list():
    """导出本地数据列表"""
    print("\n=== 导出本地数据列表 ===")
    local = list_local_data()
    rows = [{"symbol": d["symbol"], "timeframe": d["timeframe"], "file": d["file"], "size_kb": d["size_kb"]} for d in local]
    write_csv("local_data.csv", rows, ["symbol", "timeframe", "file", "size_kb"])


def main():
    print("=" * 60)
    print("导出回测API数据为CSV文件")
    print("=" * 60)

    # 确保数据存在
    symbol = "BTC/USDT"
    ensure_data(symbol, "1h", 365)
    ensure_data(symbol, "5m", 365)

    # === 1. 无杠杆回测 ===
    print("\n>>> 运行无杠杆回测...")
    params_no_lev = StrategyParams(
        large_timeframe="1h",
        small_timeframe="5m",
        initial_capital=100000.0,
        risk_percent=2.0,
        use_leverage=False,
    )
    result_no_lev = run_backtest(symbol, params_no_lev, days=365)
    print(f"  完成: {result_no_lev.total_trades}笔交易, 收益{result_no_lev.total_return}%")
    export_backtest_result(result_no_lev, "backtest")

    # === 2. 10x杠杆回测 ===
    print("\n>>> 运行10x杠杆回测...")
    params_lev = StrategyParams(
        large_timeframe="1h",
        small_timeframe="5m",
        initial_capital=100000.0,
        risk_percent=2.0,
        use_leverage=True,
        leverage=10.0,
        margin_mode="cross",
        use_funding_rate=True,
        funding_rate_override=-1,
    )
    result_lev = run_backtest(symbol, params_lev, days=365)
    print(f"  完成: {result_lev.total_trades}笔交易, 收益{result_lev.total_return}%")
    export_backtest_result(result_lev, "leverage")
    export_leverage_report(result_lev)

    # === 3. 本地数据列表 ===
    export_local_data_list()

    # === 4. 导出默认参数（供前端读取）===
    print("\n=== 导出默认参数 ===")
    default_params = {
        "symbol": symbol,
        "days": 365,
        "large_timeframe": "1h",
        "bb_period": 20,
        "bb_std": 2.0,
        "small_timeframe": "5m",
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "swing_lookback": 10,
        "atr_period": 14,
        "stop_atr_mult": 2.0,
        "stop_atr_buffer": 0.5,
        "risk_percent": 2.0,
        "tp1_ratio": 1.0,
        "tp1_close_ratio": 0.5,
        "tp2_ratio": 2.0,
        "use_bb_mid_exit": True,
        "use_near_zero_filter": True,
        "initial_capital": 100000,
        "fee_rate": 0.0004,
        "slippage": 0.0002,
        "use_leverage": False,
        "leverage": 10,
        "margin_mode": "cross",
        "use_funding_rate": True,
        "funding_rate_override": -1,
    }
    param_rows = [{"key": k, "value": str(v)} for k, v in default_params.items()]
    write_csv("default_params.csv", param_rows, ["key", "value"])

    print("\n" + "=" * 60)
    print("✅ 所有CSV数据导出完成")
    print(f"   输出目录: {Path(__file__).parent / 'docs' / 'data'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
