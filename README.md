# 股票估值分析工具

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用
streamlit run app.py
```

浏览器打开 http://localhost:8501 即可使用。

---

## 项目结构

```
stock-valuation-app/
├── app.py                   # 首页（模型选择）
├── requirements.txt
├── pages/
│   ├── 1_DDM.py             # DDM 股利贴现模型
│   ├── 2_DCF.py             # DCF 自由现金流模型
│   ├── 3_Relative.py        # 相对估值（PE/PB/PS）
│   ├── 4_RealOption.py      # 实物期权（Black-Scholes）
│   ├── 5_Factor.py          # 因子模型与量化策略
│   └── 6_Graham.py          # Graham 选股法则
└── utils/
    ├── calc.py              # 所有模型核心计算函数
    └── ui_components.py     # 共用 UI 组件
```

---

## 各模型 Excel 模板列名

| 模型 | 必须列 |
|------|--------|
| DDM | Ticker, D0, g, r |
| DCF | Ticker, FCFF0, g_high, WACC, Debt, Shares |
| 相对估值 | Ticker, EPS, BVPS, SalesPS, PE_peers, PB_peers, PS_peers |
| 实物期权 | Project, S, K, T, sigma, r |
| 因子模型 | Ticker, ROE, PE, PB, DY, NPM, PCF, Beta |
| Graham | Ticker, Revenue, CurrentRatio, ProfitYears, DividendYears, EPSGrowth10yr, PE, PB |

> **利率类列（g, r, WACC, sigma 等）请填入百分比数字，如 8 代表 8%**

---

## 免费部署

### Streamlit Cloud（推荐）
1. 将项目推送到 GitHub
2. 访问 https://share.streamlit.io
3. 选择仓库 → 选择 `app.py` → 点击 Deploy

### Railway / Render
添加启动命令：`streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
