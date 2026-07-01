"""
FastAPI 主程序
提供回测、数据下载、报告生成、杠杆分析的 REST API
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from data_downloader import (
    SUPPORTED_SYMBOLS, SUPPORTED_TIMEFRAMES,
    download_klines, load_klines, ensure_data, list_local_data, delete_local_data
)
from strategy import StrategyParams
from backtest import run_backtest, BacktestResult
from report import generate_report_charts, save_report_images
from leverage_report import generate_leverage_report, report_to_dict
from dataclasses import asdict

app = FastAPI(title="布林带回归策略回测系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 请求模型 =====
class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    days: int = 365
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
    tp1_ratio: float = 1.0
    tp1_close_ratio: float = 0.5
    tp2_ratio: float = 2.0
    use_bb_mid_exit: bool = True
    # 信号过滤
    use_near_zero_filter: bool = True
    # 资金管理
    initial_capital: float = 100000.0
    fee_rate: float = 0.0004
    slippage: float = 0.0002
    # ===== 杠杆参数 =====
    use_leverage: bool = False
    leverage: float = 10.0
    margin_mode: str = "cross"
    use_funding_rate: bool = True
    funding_rate_override: float = -1


class DownloadRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    days: int = 365


def _build_params(req: BacktestRequest) -> StrategyParams:
    """从请求构建策略参数"""
    return StrategyParams(
        large_timeframe=req.large_timeframe,
        bb_period=req.bb_period,
        bb_std=req.bb_std,
        small_timeframe=req.small_timeframe,
        macd_fast=req.macd_fast,
        macd_slow=req.macd_slow,
        macd_signal=req.macd_signal,
        swing_lookback=req.swing_lookback,
        atr_period=req.atr_period,
        stop_atr_mult=req.stop_atr_mult,
        stop_atr_buffer=req.stop_atr_buffer,
        risk_percent=req.risk_percent,
        tp1_ratio=req.tp1_ratio,
        tp1_close_ratio=req.tp1_close_ratio,
        tp2_ratio=req.tp2_ratio,
        use_bb_mid_exit=req.use_bb_mid_exit,
        use_near_zero_filter=req.use_near_zero_filter,
        initial_capital=req.initial_capital,
        fee_rate=req.fee_rate,
        slippage=req.slippage,
        use_leverage=req.use_leverage,
        leverage=req.leverage,
        margin_mode=req.margin_mode,
        use_funding_rate=req.use_funding_rate,
        funding_rate_override=req.funding_rate_override,
    )


def _result_to_dict(result: BacktestResult) -> dict:
    """将回测结果转为字典（含杠杆统计）"""
    return {
        "symbol": result.symbol,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_capital": round(result.final_capital, 2),
        "total_return": result.total_return,
        "total_pnl": result.total_pnl,
        "annual_return": result.annual_return,
        "total_trades": result.total_trades,
        "win_trades": result.win_trades,
        "loss_trades": result.loss_trades,
        "win_rate": result.win_rate,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "profit_factor": result.profit_factor,
        "max_win": result.max_win,
        "max_loss": result.max_loss,
        "avg_rr": result.avg_rr,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "avg_holding_bars": result.avg_holding_bars,
        "long_trades": result.long_trades,
        "short_trades": result.short_trades,
        # 杠杆统计
        "use_leverage": result.use_leverage,
        "leverage": result.leverage,
        "liquidation_count": result.liquidation_count,
        "total_funding_fees": result.total_funding_fees,
        "total_liquidation_fees": result.total_liquidation_fees,
        "max_position_value": result.max_position_value,
        "avg_margin_used": result.avg_margin_used,
        "max_margin_used": result.max_margin_used,
        "leverage_amplification": result.leverage_amplification,
        "risk_per_trade_pct": result.risk_per_trade_pct,
        # 数据序列
        "equity_curve": result.equity_curve,
        "drawdown_curve": result.drawdown_curve,
        "trades": result.trades,
    }


# ===== API 接口 =====

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "布林带回归策略回测系统 v2.0 运行中（含杠杆）"}


@app.get("/api/symbols")
async def get_symbols():
    return {"symbols": SUPPORTED_SYMBOLS}


@app.get("/api/timeframes")
async def get_timeframes():
    return {"timeframes": SUPPORTED_TIMEFRAMES}


@app.get("/api/local-data")
async def get_local_data():
    return {"data": list_local_data()}


@app.post("/api/download")
async def download_data(req: DownloadRequest, background_tasks: BackgroundTasks):
    if req.symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"不支持的交易对: {req.symbol}")
    if req.timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(status_code=400, detail=f"不支持的时间周期: {req.timeframe}")

    try:
        df = download_klines(req.symbol, req.timeframe, req.days)
        return {
            "success": True,
            "symbol": req.symbol,
            "timeframe": req.timeframe,
            "rows": len(df),
            "start": df['datetime'].iloc[0].strftime('%Y-%m-%d %H:%M') if not df.empty else "",
            "end": df['datetime'].iloc[-1].strftime('%Y-%m-%d %H:%M') if not df.empty else "",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/local-data/{symbol}/{timeframe}")
async def remove_local_data(symbol: str, timeframe: str):
    symbol = symbol.replace("_", "/")
    success = delete_local_data(symbol, timeframe)
    return {"success": success}


@app.post("/api/backtest")
async def backtest(req: BacktestRequest):
    """执行回测（含杠杆支持和风险分析）"""
    try:
        params = _build_params(req)
        result = run_backtest(req.symbol, params, req.days)

        # 生成图表
        charts = generate_report_charts(result)

        # 生成杠杆分析报告
        leverage_report = generate_leverage_report(result)
        leverage_report_dict = report_to_dict(leverage_report)

        return {
            "success": True,
            "result": _result_to_dict(result),
            "charts": charts,
            "leverage_report": leverage_report_dict,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export-report")
async def export_report(req: BacktestRequest):
    """导出报告图片到本地"""
    try:
        params = _build_params(req)
        result = run_backtest(req.symbol, params, req.days)
        files = save_report_images(result)
        return {"success": True, "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/klines/{symbol}/{timeframe}")
async def get_klines(symbol: str, timeframe: str, days: int = 365):
    symbol = symbol.replace("_", "/")
    df = ensure_data(symbol, timeframe, days)
    if df.empty:
        raise HTTPException(status_code=404, detail="数据不存在，请先下载")

    if len(df) > 2000:
        df = df.tail(2000)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "data": df[['datetime', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
