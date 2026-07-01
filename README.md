# 布林带回归策略量化回测系统

> 支持币安USDT永续合约杠杆交易模拟与风险分析的加密货币量化回测系统

## ✨ 功能特性

- **多周期策略**：大周期(1H/4H)布林带触轨定方向，小周期(5m/15m) MACD+突破进场
- **完整风控**：2倍ATR止损、1:1平半仓、多重出场条件
- **币安杠杆模拟**：USDT永续合约、1-125x杠杆、阶梯维持保证金率、全仓交叉保证金
- **真实强平计算**：动态强平价、资金费率(每8小时)、强平清算费(0.5%)
- **杠杆风险分析报告**：7类风险事件检测、0-100风险评分、改进建议
- **可视化界面**：React + ECharts 交互式图表
- **CSV演示模式**：GitHub Pages 静态部署，无需后端即可体验

## 🚀 在线体验

访问 GitHub Pages 部署的演示版本：
**https://miku-cy.github.io/bb-regression-strategy/**

> 演示模式使用预导出的BTC/USDT 365天回测数据，可在左侧切换「启用杠杆」对比10x杠杆回测结果。

## 📦 本地部署（完整功能）

### 前置要求
- Python 3.10+
- Node.js 18+

### 后端启动
```bash
cd backend
pip install -r requirements.txt
python main.py
# 后端运行在 http://localhost:8000
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 快速启动
```bash
# Windows
启动系统.bat
```

## 📊 策略说明

### 进场条件
1. 大周期布林带触上轨 → 做空方向
2. 大周期布林带触下轨 → 做多方向
3. 小周期MACD金叉/死叉 + 突破震荡高低点进场

### 出场条件
- 止损：2倍ATR + 缓冲
- 止盈1：1:1盈亏比平50%仓位
- 止盈2：2:1盈亏比触发保本止损
- 布林带中轨止盈

### 杠杆规则（币安USDT永续）
- 阶梯维持保证金率（BTC: 0.4%-50%，按仓位价值分9档）
- 全仓交叉保证金模式
- 资金费率每8小时结算（00:00, 08:00, 16:00 UTC）
- 强平清算费：仓位价值0.5%

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.14 · FastAPI · pandas · numpy · matplotlib |
| 前端 | React 18 · TypeScript · Vite · ECharts |
| 数据源 | Binance REST API |

## 📁 项目结构

```
├── backend/              # 后端API服务
│   ├── main.py           # FastAPI 主程序
│   ├── strategy.py       # 策略引擎（含杠杆）
│   ├── backtest.py       # 回测引擎
│   ├── leverage_rules.py # 币安杠杆规则
│   ├── leverage_report.py# 杠杆风险分析
│   ├── indicators.py     # 技术指标
│   ├── report.py         # 报告生成
│   └── data_downloader.py# 数据下载
├── frontend/             # 前端React应用
│   └── src/
│       ├── api.ts        # API层（含CSV演示模式）
│       ├── types.ts      # 类型定义
│       └── components/    # UI组件
├── docs/                 # GitHub Pages 部署目录
│   ├── index.html        # 构建产物
│   ├── assets/           # JS/CSS
│   └── data/             # CSV演示数据
├── data/                 # 本地K线数据
└── export_csv_data.py    # CSV数据导出脚本
```

## 📄 License

MIT
