"""
杠杆分析报告生成模块
识别重大亏损、操作错误，提供风险评估和建议
"""
import numpy as np
from dataclasses import dataclass, field
from typing import List
from backtest import BacktestResult


@dataclass
class RiskEvent:
    """风险事件"""
    severity: str  # 'critical' | 'warning' | 'info'
    category: str  # 'liquidation' | 'huge_loss' | 'over_leverage' | 'concentration' | 'funding' | 'operation'
    title: str
    description: str
    trade_index: int = -1  # 关联的交易索引，-1表示全局
    value: float = 0.0
    suggestion: str = ""


@dataclass
class LeverageReport:
    """杠杆分析报告"""
    # 风险评级
    risk_level: str  # '极高' | '高' | '中' | '低'
    risk_score: float  # 0-100，越高越危险

    # 关键指标
    max_loss_per_trade_pct: float    # 最大单笔亏损占比
    avg_loss_per_trade_pct: float    # 平均单笔亏损占比
    liquidation_rate: float          # 强平率 %
    funding_fee_ratio: float         # 资金费占总盈亏比 %
    margin_utilization: float        # 保证金利用率 %
    risk_reward_with_lev: float      # 杠杆下盈亏比

    # 风险事件列表
    events: List[RiskEvent] = field(default_factory=list)

    # 总结建议
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


def generate_leverage_report(result: BacktestResult) -> LeverageReport:
    """生成杠杆分析报告"""
    events: List[RiskEvent] = []
    trades = result.trades
    initial_capital = result.initial_capital

    if not trades:
        return LeverageReport(
            risk_level="低", risk_score=0,
            max_loss_per_trade_pct=0, avg_loss_per_trade_pct=0,
            liquidation_rate=0, funding_fee_ratio=0,
            margin_utilization=0, risk_reward_with_lev=0,
            summary="无交易记录", recommendations=[]
        )

    # ===== 1. 检测强平事件（最严重）=====
    liquidation_trades = [(i, t) for i, t in enumerate(trades) if t.get('is_liquidated', False)]
    for idx, t in liquidation_trades:
        loss_pct = abs(t['pnl']) / initial_capital * 100
        events.append(RiskEvent(
            severity='critical',
            category='liquidation',
            title=f'⚠ 强制平仓(爆仓) - 第{idx+1}笔交易',
            description=(
                f"时间: {t['entry_time'][:16]}\n"
                f"方向: {'做多' if t['direction']=='long' else '做空'} | 杠杆: {t['leverage']}x\n"
                f"入场价: {t['entry_price']:.2f} → 强平价: {t.get('liquidation_price', 0):.2f}\n"
                f"亏损: {t['pnl']:.2f} USDT ({loss_pct:.2f}% 本金)\n"
                f"强平清算费: {t.get('liquidation_fee', 0):.2f} USDT"
            ),
            trade_index=idx,
            value=t['pnl'],
            suggestion=(
                f"强平是杠杆交易中最严重的事件。该笔交易使用了 {t['leverage']}x 杠杆，"
                f"价格波动仅 {(abs(t.get('liquidation_price',0)-t['entry_price'])/t['entry_price']*100 if t['entry_price']>0 else 0):.2f}% 即触发爆仓。"
                f"建议: ①降低杠杆至3-5x ②扩大止损距离 ③增加保证金"
            )
        ))

    # ===== 2. 检测重大亏损（单笔亏损>5%本金）=====
    for i, t in enumerate(trades):
        if t['pnl'] < 0:
            loss_pct = abs(t['pnl']) / initial_capital * 100
            if loss_pct >= 10:
                severity = 'critical'
            elif loss_pct >= 5:
                severity = 'warning'
            else:
                continue

            # 跳过已记录的强平事件
            if t.get('is_liquidated', False):
                continue

            events.append(RiskEvent(
                severity=severity,
                category='huge_loss',
                title=f'重大亏损 - 第{i+1}笔交易 ({loss_pct:.2f}% 本金)',
                description=(
                    f"时间: {t['entry_time'][:16]}\n"
                    f"方向: {'做多' if t['direction']=='long' else '做空'} | 杠杆: {t.get('leverage', 1)}x\n"
                    f"入场价: {t['entry_price']:.2f} → 出场价: {t.get('exit_price', 0):.2f}\n"
                    f"出场原因: {t.get('exit_reason', '未知')}\n"
                    f"亏损: {t['pnl']:.2f} USDT ({loss_pct:.2f}% 本金)"
                ),
                trade_index=i,
                value=t['pnl'],
                suggestion=(
                    f"单笔亏损超过 {loss_pct:.1f}% 本金，远超 2% 的安全线。"
                    f"在 {t.get('leverage', 1)}x 杠杆下，价格波动被放大。"
                    f"建议: ①减小仓位 ②收紧止损 ③降低杠杆"
                )
            ))

    # ===== 3. 检测过度杠杆 =====
    if result.use_leverage:
        high_lev_trades = [(i, t) for i, t in enumerate(trades) if t.get('leverage', 1) >= 20]
        for idx, t in high_lev_trades[:5]:  # 只显示前5个
            events.append(RiskEvent(
                severity='warning' if t.get('leverage', 1) < 50 else 'critical',
                category='over_leverage',
                title=f'过度杠杆 - 第{idx+1}笔交易 ({t["leverage"]}x)',
                description=(
                    f"杠杆 {t['leverage']}x 意味着价格反向波动 {100/t['leverage']:.2f}% 即爆仓\n"
                    f"仓位价值: {t.get('position_value', 0):.2f} USDT\n"
                    f"占用保证金: {t.get('margin', 0):.2f} USDT"
                ),
                trade_index=idx,
                suggestion=(
                    f"{t['leverage']}x 杠杆风险极高，BTC日内波动常达3-5%。"
                    f"建议杠杆不超过10x，稳健策略建议3-5x。"
                )
            ))

    # ===== 4. 检测风险集中（连续亏损）=====
    consecutive_losses = 0
    max_consecutive = 0
    consec_start_idx = -1
    max_consec_start = -1
    for i, t in enumerate(trades):
        if t['pnl'] < 0:
            if consecutive_losses == 0:
                consec_start_idx = i
            consecutive_losses += 1
            if consecutive_losses > max_consecutive:
                max_consecutive = consecutive_losses
                max_consec_start = consec_start_idx
        else:
            consecutive_losses = 0

    if max_consecutive >= 5:
        total_loss = sum(trades[i]['pnl'] for i in range(max_consec_start, max_consec_start + max_consecutive))
        events.append(RiskEvent(
            severity='warning' if max_consecutive < 8 else 'critical',
            category='concentration',
            title=f'连续亏损 {max_consecutive} 笔',
            description=(
                f"从第{max_consec_start+1}笔开始连续亏损 {max_consecutive} 笔\n"
                f"累计亏损: {total_loss:.2f} USDT ({abs(total_loss)/initial_capital*100:.2f}% 本金)\n"
                f"在杠杆模式下，连续亏损会导致保证金快速消耗，增加爆仓风险"
            ),
            suggestion=(
                f"连续 {max_consecutive} 笔亏损表明策略可能进入失效期。"
                f"建议: ①暂停交易 ②减小仓位 ③检查市场环境是否变化"
            )
        ))

    # ===== 5. 检测资金费率影响 =====
    if result.total_funding_fees != 0:
        funding_ratio = abs(result.total_funding_fees) / (abs(result.total_pnl) + 1) * 100
        if funding_ratio > 10:
            events.append(RiskEvent(
                severity='warning' if funding_ratio < 30 else 'critical',
                category='funding',
                title=f'资金费率消耗过大 ({funding_ratio:.1f}% of P&L)',
                description=(
                    f"总资金费: {result.total_funding_fees:.2f} USDT\n"
                    f"占总盈亏比例: {funding_ratio:.1f}%\n"
                    f"资金费率每8小时结算，长期持仓成本显著"
                ),
                suggestion=(
                    f"资金费率消耗了 {funding_ratio:.1f}% 的盈亏。"
                    f"建议: ①缩短持仓时间 ②避免长期逆势持仓 ③关注资金费率方向"
                )
            ))

    # ===== 6. 检测保证金利用率过高 =====
    if result.max_margin_used > 0:
        margin_util = result.max_margin_used / initial_capital * 100
        if margin_util > 70:
            events.append(RiskEvent(
                severity='warning' if margin_util < 90 else 'critical',
                category='operation',
                title=f'保证金利用率过高 ({margin_util:.1f}%)',
                description=(
                    f"最大占用保证金: {result.max_margin_used:.2f} USDT\n"
                    f"占初始资金: {margin_util:.1f}%\n"
                    f"保证金利用率过高时，小幅波动即可能触发强平"
                ),
                suggestion=(
                    f"保证金利用率达 {margin_util:.1f}%，建议控制在50%以下。"
                    f"降低杠杆或减小仓位可显著降低爆仓风险。"
                )
            ))

    # ===== 7. 检测单笔风险超标 =====
    if result.risk_per_trade_pct > 3:
        events.append(RiskEvent(
            severity='warning' if result.risk_per_trade_pct < 6 else 'critical',
            category='operation',
            title=f'单笔风险超标 ({result.risk_per_trade_pct:.2f}%)',
            description=(
                f"平均单笔风险: {result.risk_per_trade_pct:.2f}% 本金\n"
                f"安全标准: ≤2% 本金\n"
                f"杠杆放大了实际风险敞口"
            ),
            suggestion=(
                f"单笔风险 {result.risk_per_trade_pct:.2f}% 超过2%安全线。"
                f"建议: ①降低杠杆 ②收紧止损 ③减小仓位"
            )
        ))

    # ===== 计算风险评分 =====
    risk_score = _calc_risk_score(result, events)

    # ===== 风险等级 =====
    if risk_score >= 75:
        risk_level = "极高"
    elif risk_score >= 50:
        risk_level = "高"
    elif risk_score >= 25:
        risk_level = "中"
    else:
        risk_level = "低"

    # ===== 关键指标 =====
    losses = [t['pnl'] for t in trades if t['pnl'] < 0]
    max_loss_pct = max([abs(l) / initial_capital * 100 for l in losses], default=0)
    avg_loss_pct = np.mean([abs(l) / initial_capital * 100 for l in losses]) if losses else 0
    liquidation_rate = result.liquidation_count / len(trades) * 100 if trades else 0
    funding_ratio = abs(result.total_funding_fees) / (abs(result.total_pnl) + 1) * 100
    margin_util = result.max_margin_used / initial_capital * 100 if initial_capital > 0 else 0

    # 杠杆下盈亏比
    if losses:
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss_abs = abs(np.mean(losses))
        rr_lev = avg_win / avg_loss_abs if avg_loss_abs > 0 else 0
    else:
        rr_lev = 0

    # ===== 总结 =====
    summary = _generate_summary(result, risk_level, risk_score, events)

    # ===== 建议 =====
    recommendations = _generate_recommendations(result, events)

    return LeverageReport(
        risk_level=risk_level,
        risk_score=round(risk_score, 1),
        max_loss_per_trade_pct=round(max_loss_pct, 2),
        avg_loss_per_trade_pct=round(avg_loss_pct, 2),
        liquidation_rate=round(liquidation_rate, 2),
        funding_fee_ratio=round(funding_ratio, 2),
        margin_utilization=round(margin_util, 2),
        risk_reward_with_lev=round(rr_lev, 2),
        events=events,
        summary=summary,
        recommendations=recommendations,
    )


def _calc_risk_score(result: BacktestResult, events: list) -> float:
    """计算风险评分 0-100"""
    score = 0

    # 强平事件（每个+20）
    critical_count = sum(1 for e in events if e.severity == 'critical')
    warning_count = sum(1 for e in events if e.severity == 'warning')
    score += critical_count * 15
    score += warning_count * 5

    # 最大回撤（>30% 加分）
    if result.max_drawdown < -50:
        score += 25
    elif result.max_drawdown < -30:
        score += 15
    elif result.max_drawdown < -15:
        score += 5

    # 杠杆倍数
    if result.leverage >= 50:
        score += 20
    elif result.leverage >= 20:
        score += 12
    elif result.leverage >= 10:
        score += 6

    # 强平率
    if result.liquidation_count > 0:
        liq_rate = result.liquidation_count / max(result.total_trades, 1)
        score += liq_rate * 30

    # 单笔风险
    if result.risk_per_trade_pct > 5:
        score += 10
    elif result.risk_per_trade_pct > 3:
        score += 5

    # 资金费率占比
    if result.total_funding_fees != 0:
        funding_ratio = abs(result.total_funding_fees) / (abs(result.total_pnl) + 1) * 100
        if funding_ratio > 30:
            score += 8
        elif funding_ratio > 10:
            score += 4

    return min(score, 100)


def _generate_summary(result: BacktestResult, risk_level: str, risk_score: float, events: list) -> str:
    """生成总结"""
    critical = sum(1 for e in events if e.severity == 'critical')
    warning = sum(1 for e in events if e.severity == 'warning')

    if not result.use_leverage:
        return "当前未启用杠杆，风险等级低。启用杠杆后将提供详细的风险分析。"

    parts = []
    parts.append(f"杠杆模式风险评估: {risk_level} (评分 {risk_score}/100)")

    if critical > 0:
        parts.append(f"发现 {critical} 个严重风险事件")
    if warning > 0:
        parts.append(f"发现 {warning} 个警告级风险事件")

    if result.liquidation_count > 0:
        parts.append(f"共发生 {result.liquidation_count} 次强平爆仓")
    else:
        parts.append("未发生强平事件")

    parts.append(f"最大回撤 {result.max_drawdown}%")
    parts.append(f"使用 {result.leverage}x 杠杆")

    if result.total_pnl < 0:
        parts.append(f"策略亏损 {abs(result.total_return)}%，杠杆放大了亏损")
    else:
        parts.append(f"策略盈利 {result.total_return}%，杠杆放大了收益")

    return " | ".join(parts)


def _generate_recommendations(result: BacktestResult, events: list) -> list:
    """生成建议"""
    recs = []

    if not result.use_leverage:
        return ["当前未启用杠杆。如需启用，建议从3-5x开始，逐步调整。"]

    # 基于事件类型生成建议
    has_liquidation = any(e.category == 'liquidation' for e in events)
    has_huge_loss = any(e.category == 'huge_loss' for e in events)
    has_over_lev = any(e.category == 'over_leverage' for e in events)
    has_consecutive = any(e.category == 'concentration' for e in events)
    has_funding = any(e.category == 'funding' for e in events)
    has_margin = any(e.category == 'operation' for e in events)

    if has_liquidation:
        recs.append("🚨 发生强平事件！强烈建议降低杠杆至3-5x，并扩大止损距离。强平意味着仓位完全归零，是杠杆交易中最严重的损失。")

    if has_over_lev:
        recs.append(f"⚠️ 当前杠杆 {result.leverage}x 过高。BTC日内波动3-5%，20x杠杆下1.5%波动即爆仓。建议杠杆≤10x。")

    if has_huge_loss:
        recs.append("📉 存在重大亏损交易。建议: ①严格执行2%止损 ②降低单笔仓位 ③避免在信号不明时进场。")

    if has_consecutive:
        recs.append("🔁 出现连续亏损。建议: ①设置每日最大亏损限额 ②连续亏损3笔后暂停交易 ③检查策略是否失效。")

    if has_funding:
        recs.append(f"💸 资金费率消耗过大 ({result.total_funding_fees:.0f} USDT)。建议: ①缩短持仓时间 ②避免长期逆势 ③关注资金费率方向。")

    if has_margin:
        recs.append("🏦 保证金利用率过高。建议将保证金利用率控制在50%以下，预留足够资金应对波动。")

    # 通用建议
    if result.risk_per_trade_pct > 2:
        recs.append(f"🎯 单笔风险 {result.risk_per_trade_pct:.1f}% 超标。建议降至2%以内: 减小仓位或收紧止损。")

    if result.max_drawdown < -30:
        recs.append(f"📊 最大回撤 {result.max_drawdown}% 过大。建议: ①降低杠杆 ②增加过滤条件 ③分散交易标的。")

    if not recs:
        recs.append("✅ 未发现严重风险事件。建议继续保持当前风险管理策略。")

    recs.append("💡 通用建议: 杠杆是双刃剑，放大收益也放大亏损。建议先在低杠杆(3-5x)下验证策略有效性，再逐步调整。")

    return recs


def report_to_dict(report: LeverageReport) -> dict:
    """将报告转为字典"""
    return {
        "risk_level": report.risk_level,
        "risk_score": report.risk_score,
        "max_loss_per_trade_pct": report.max_loss_per_trade_pct,
        "avg_loss_per_trade_pct": report.avg_loss_per_trade_pct,
        "liquidation_rate": report.liquidation_rate,
        "funding_fee_ratio": report.funding_fee_ratio,
        "margin_utilization": report.margin_utilization,
        "risk_reward_with_lev": report.risk_reward_with_lev,
        "events": [
            {
                "severity": e.severity,
                "category": e.category,
                "title": e.title,
                "description": e.description,
                "trade_index": e.trade_index,
                "value": e.value,
                "suggestion": e.suggestion,
            }
            for e in report.events
        ],
        "summary": report.summary,
        "recommendations": report.recommendations,
    }
