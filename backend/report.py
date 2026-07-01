"""
回测报告生成模块
生成统计报告、图表导出
"""
import os
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from backtest import BacktestResult

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

REPORT_DIR = Path(__file__).parent.parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def generate_report_charts(result: BacktestResult) -> dict:
    """
    生成回测图表，返回base64编码的图片
    """
    charts = {}

    # 1. 资金曲线图
    charts['equity_curve'] = _plot_equity_curve(result)

    # 2. 回撤曲线图
    charts['drawdown'] = _plot_drawdown(result)

    # 3. 交易盈亏分布图
    charts['pnl_distribution'] = _plot_pnl_distribution(result)

    # 4. 累积盈亏图
    charts['cumulative_pnl'] = _plot_cumulative_pnl(result)

    # 5. 月度收益热力图
    charts['monthly_returns'] = _plot_monthly_returns(result)

    return charts


def _plot_equity_curve(result: BacktestResult) -> str:
    """资金曲线图"""
    fig, ax = plt.subplots(figsize=(12, 5))

    eq_data = result.equity_curve
    dates = [pd.to_datetime(p['datetime']) for p in eq_data]
    equity = [p['equity'] for p in eq_data]

    ax.fill_between(dates, equity, result.initial_capital,
                     where=[e >= result.initial_capital for e in equity],
                     alpha=0.3, color='#10b981', label='盈利区域')
    ax.fill_between(dates, equity, result.initial_capital,
                     where=[e < result.initial_capital for e in equity],
                     alpha=0.3, color='#ef4444', label='亏损区域')
    ax.plot(dates, equity, color='#3b82f6', linewidth=1.5, label='资金曲线')
    ax.axhline(y=result.initial_capital, color='gray', linestyle='--', alpha=0.5, label='初始资金')

    ax.set_title(f'{result.symbol} 资金曲线', fontsize=14, fontweight='bold')
    ax.set_xlabel('时间')
    ax.set_ylabel('资金 (USDT)')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    return _fig_to_base64(fig)


def _plot_drawdown(result: BacktestResult) -> str:
    """回撤曲线图"""
    fig, ax = plt.subplots(figsize=(12, 4))

    dd_data = result.drawdown_curve
    dates = [pd.to_datetime(p['datetime']) for p in dd_data]
    drawdown = [p['drawdown'] for p in dd_data]

    ax.fill_between(dates, drawdown, 0, alpha=0.4, color='#ef4444')
    ax.plot(dates, drawdown, color='#dc2626', linewidth=1)

    ax.set_title(f'回撤曲线 (最大回撤: {result.max_drawdown}%)', fontsize=14, fontweight='bold')
    ax.set_xlabel('时间')
    ax.set_ylabel('回撤 (%)')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    return _fig_to_base64(fig)


def _plot_pnl_distribution(result: BacktestResult) -> str:
    """交易盈亏分布图"""
    fig, ax = plt.subplots(figsize=(10, 5))

    trades = result.trades
    pnls = [t['pnl'] for t in trades]

    colors = ['#10b981' if p > 0 else '#ef4444' for p in pnls]
    ax.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)

    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.set_title(f'交易盈亏分布 (共{len(pnls)}笔)', fontsize=14, fontweight='bold')
    ax.set_xlabel('交易序号')
    ax.set_ylabel('盈亏 (USDT)')
    ax.grid(True, alpha=0.3, axis='y')

    return _fig_to_base64(fig)


def _plot_cumulative_pnl(result: BacktestResult) -> str:
    """累积盈亏图"""
    fig, ax = plt.subplots(figsize=(12, 5))

    trades = result.trades
    pnls = [t['pnl'] for t in trades]
    cum_pnl = np.cumsum(pnls)

    ax.plot(range(len(cum_pnl)), cum_pnl, color='#8b5cf6', linewidth=2)
    ax.fill_between(range(len(cum_pnl)), cum_pnl, 0,
                     where=[c >= 0 for c in cum_pnl], alpha=0.3, color='#8b5cf6')
    ax.fill_between(range(len(cum_pnl)), cum_pnl, 0,
                     where=[c < 0 for c in cum_pnl], alpha=0.3, color='#ef4444')

    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.set_title('累积盈亏曲线', fontsize=14, fontweight='bold')
    ax.set_xlabel('交易序号')
    ax.set_ylabel('累积盈亏 (USDT)')
    ax.grid(True, alpha=0.3)

    return _fig_to_base64(fig)


def _plot_monthly_returns(result: BacktestResult) -> str:
    """月度收益热力图"""
    fig, ax = plt.subplots(figsize=(10, 4))

    trades = result.trades
    if not trades:
        ax.text(0.5, 0.5, '无交易数据', ha='center', va='center', fontsize=14)
        return _fig_to_base64(fig)

    # 按月统计收益
    monthly = {}
    for t in trades:
        if t['exit_time']:
            dt = pd.to_datetime(t['exit_time'])
            key = (dt.year, dt.month)
            monthly[key] = monthly.get(key, 0) + t['pnl']

    if not monthly:
        ax.text(0.5, 0.5, '无交易数据', ha='center', va='center', fontsize=14)
        return _fig_to_base64(fig)

    years = sorted(set(k[0] for k in monthly.keys()))
    months = range(1, 13)

    data = np.zeros((len(years), 12))
    for (y, m), pnl in monthly.items():
        yi = years.index(y)
        data[yi, m - 1] = pnl

    im = ax.imshow(data, cmap='RdYlGn', aspect='auto')

    ax.set_xticks(range(12))
    ax.set_xticklabels([f'{m}月' for m in range(1, 13)])
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels(years)

    # 添加数值标注
    for i in range(len(years)):
        for j in range(12):
            if data[i, j] != 0:
                ax.text(j, i, f'{data[i, j]:.0f}', ha='center', va='center', fontsize=8)

    ax.set_title('月度收益热力图', fontsize=14, fontweight='bold')
    plt.colorbar(im, ax=ax, label='盈亏 (USDT)')

    return _fig_to_base64(fig)


def _fig_to_base64(fig) -> str:
    """将matplotlib图转为base64字符串"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


def save_report_images(result: BacktestResult) -> list:
    """保存报告图片到本地文件，返回文件路径列表"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_folder = REPORT_DIR / f"{result.symbol.replace('/', '_')}_{timestamp}"
    report_folder.mkdir(exist_ok=True)

    saved_files = []

    # 资金曲线
    fig = _create_equity_fig(result)
    path = report_folder / "equity_curve.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    saved_files.append(str(path))

    # 回撤曲线
    fig = _create_drawdown_fig(result)
    path = report_folder / "drawdown.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    saved_files.append(str(path))

    # 盈亏分布
    fig = _create_pnl_fig(result)
    path = report_folder / "pnl_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    saved_files.append(str(path))

    return saved_files


def _create_equity_fig(result):
    fig, ax = plt.subplots(figsize=(12, 5))
    eq_data = result.equity_curve
    dates = [pd.to_datetime(p['datetime']) for p in eq_data]
    equity = [p['equity'] for p in eq_data]
    ax.plot(dates, equity, color='#3b82f6', linewidth=1.5)
    ax.fill_between(dates, equity, result.initial_capital, alpha=0.3, color='#3b82f6')
    ax.axhline(y=result.initial_capital, color='gray', linestyle='--', alpha=0.5)
    ax.set_title(f'{result.symbol} 资金曲线', fontsize=14, fontweight='bold')
    ax.set_xlabel('时间')
    ax.set_ylabel('资金 (USDT)')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    return fig


def _create_drawdown_fig(result):
    fig, ax = plt.subplots(figsize=(12, 4))
    dd_data = result.drawdown_curve
    dates = [pd.to_datetime(p['datetime']) for p in dd_data]
    drawdown = [p['drawdown'] for p in dd_data]
    ax.fill_between(dates, drawdown, 0, alpha=0.4, color='#ef4444')
    ax.plot(dates, drawdown, color='#dc2626', linewidth=1)
    ax.set_title(f'回撤曲线 (最大回撤: {result.max_drawdown}%)', fontsize=14, fontweight='bold')
    ax.set_xlabel('时间')
    ax.set_ylabel('回撤 (%)')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    return fig


def _create_pnl_fig(result):
    fig, ax = plt.subplots(figsize=(10, 5))
    trades = result.trades
    pnls = [t['pnl'] for t in trades]
    colors = ['#10b981' if p > 0 else '#ef4444' for p in pnls]
    ax.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.set_title(f'交易盈亏分布 (共{len(pnls)}笔)', fontsize=14, fontweight='bold')
    ax.set_xlabel('交易序号')
    ax.set_ylabel('盈亏 (USDT)')
    ax.grid(True, alpha=0.3, axis='y')
    return fig
