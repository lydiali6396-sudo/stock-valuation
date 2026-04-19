"""
stock-valuation-app/utils/calc.py
所有估值模型的核心计算函数
"""
import numpy as np
import pandas as pd
from scipy.stats import norm
import math


# ════════════════════════════════════════════════════════
# 1. DDM  股利贴现模型
# ════════════════════════════════════════════════════════

def ddm_gordon(D0: float, g: float, r: float) -> float:
    """
    Gordon 永续增长 DDM
    V = D1 / (r - g)
    D0: 当前年度股利; g: 长期增长率(小数); r: 贴现率(小数)
    """
    if r <= g:
        raise ValueError("贴现率 r 必须大于增长率 g")
    D1 = D0 * (1 + g)
    return D1 / (r - g)


def ddm_multistage(D0: float, g_high: float, years_high: int,
                   g_stable: float, r: float) -> float:
    """
    两阶段 DDM
    第一阶段：高增长 g_high，持续 years_high 年
    第二阶段：永续稳定增长 g_stable
    """
    if r <= g_stable:
        raise ValueError("贴现率 r 必须大于永续增长率 g_stable")
    pv = 0.0
    D = D0
    for t in range(1, years_high + 1):
        D = D * (1 + g_high)
        pv += D / (1 + r) ** t
    # 第 years_high 年末的终值
    terminal_value = (D * (1 + g_stable)) / (r - g_stable)
    pv += terminal_value / (1 + r) ** years_high
    return pv


def ddm_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    批量计算 DDM；df 必须包含列: Ticker, D0, g, r
    可选列: D0_stage2_g(两阶段增长率), years_high, g_stable
    """
    results = []
    for _, row in df.iterrows():
        try:
            g_pct = row['g'] / 100
            r_pct = row['r'] / 100
            if 'years_high' in df.columns and not pd.isna(row.get('years_high')):
                value = ddm_multistage(
                    row['D0'], g_pct, int(row['years_high']),
                    row.get('g_stable', 3) / 100, r_pct
                )
                model = "两阶段DDM"
            else:
                value = ddm_gordon(row['D0'], g_pct, r_pct)
                model = "Gordon DDM"
            results.append({
                'Ticker': row['Ticker'],
                'Company': row.get('Company', ''),
                '内在价值': round(value, 2),
                '当前价格': row.get('Price', None),
                '估值模型': model,
                '状态': '✅ 正常'
            })
        except Exception as e:
            results.append({
                'Ticker': row['Ticker'],
                'Company': row.get('Company', ''),
                '内在价值': None,
                '当前价格': row.get('Price', None),
                '估值模型': 'DDM',
                '状态': f'❌ {e}'
            })
    result_df = pd.DataFrame(results)
    result_df = _add_upside(result_df)
    return result_df


def ddm_sensitivity(D0: float, g_base: float, r_base: float,
                    g_range: list = None, r_range: list = None) -> pd.DataFrame:
    """生成 DDM 敏感性分析矩阵（g vs r）"""
    if g_range is None:
        g_range = [g_base - 0.02, g_base - 0.01, g_base, g_base + 0.01, g_base + 0.02]
    if r_range is None:
        r_range = [r_base - 0.02, r_base - 0.01, r_base, r_base + 0.01, r_base + 0.02]
    data = {}
    for r in r_range:
        col = {}
        for g in g_range:
            try:
                col[f"g={g*100:.1f}%"] = round(ddm_gordon(D0, g, r), 2)
            except:
                col[f"g={g*100:.1f}%"] = "N/A"
        data[f"r={r*100:.1f}%"] = col
    return pd.DataFrame(data)


# ════════════════════════════════════════════════════════
# 2. DCF / FCF  自由现金流模型
# ════════════════════════════════════════════════════════

def dcf_value(FCFF0: float, g_high: float, years_high: int,
              g_stable: float, WACC: float,
              debt: float = 0.0, shares: float = 1.0) -> dict:
    """
    两阶段 DCF (FCFF)
    返回: 企业价值、股权价值、每股价值
    FCFF0: 当前自由现金流（元）
    g_high/g_stable: 增长率（小数）
    WACC: 加权平均资本成本（小数）
    debt: 净负债（元）
    shares: 总股本（股）
    """
    if WACC <= g_stable:
        raise ValueError("WACC 必须大于永续增长率")
    pv = 0.0
    FCFF = FCFF0
    for t in range(1, years_high + 1):
        FCFF *= (1 + g_high)
        pv += FCFF / (1 + WACC) ** t
    terminal = FCFF * (1 + g_stable) / (WACC - g_stable)
    pv += terminal / (1 + WACC) ** years_high
    equity_value = pv - debt
    per_share = equity_value / shares if shares > 0 else 0
    return {
        'enterprise_value': round(pv, 2),
        'equity_value': round(equity_value, 2),
        'per_share_value': round(per_share, 2),
        'terminal_value': round(terminal, 2),
        'terminal_pct': round(terminal / (1 + WACC) ** years_high / pv * 100, 1) if pv else 0
    }


def dcf_batch(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        try:
            res = dcf_value(
                FCFF0=row['FCFF0'],
                g_high=row['g_high'] / 100,
                years_high=int(row.get('years_high', 5)),
                g_stable=row.get('g_stable', 3) / 100,
                WACC=row['WACC'] / 100,
                debt=row.get('Debt', 0),
                shares=row.get('Shares', 1)
            )
            results.append({
                'Ticker': row['Ticker'],
                'Company': row.get('Company', ''),
                '每股内在价值': res['per_share_value'],
                '企业价值(亿)': round(res['enterprise_value'] / 1e8, 2),
                '终值占比%': res['terminal_pct'],
                '当前价格': row.get('Price', None),
                '状态': '✅ 正常'
            })
        except Exception as e:
            results.append({
                'Ticker': row['Ticker'],
                'Company': row.get('Company', ''),
                '每股内在价值': None,
                '状态': f'❌ {e}'
            })
    result_df = pd.DataFrame(results)
    result_df = _add_upside(result_df, value_col='每股内在价值')
    return result_df


def dcf_sensitivity(FCFF0: float, g_high_base: float, years_high: int,
                    g_stable: float, WACC_base: float,
                    debt: float = 0, shares: float = 1) -> pd.DataFrame:
    """DCF 敏感性：WACC vs g_high"""
    wacc_range = [WACC_base + d for d in [-0.02, -0.01, 0, 0.01, 0.02]]
    g_range = [g_high_base + d for d in [-0.03, -0.015, 0, 0.015, 0.03]]
    data = {}
    for wacc in wacc_range:
        col = {}
        for g in g_range:
            try:
                r = dcf_value(FCFF0, g, years_high, g_stable, wacc, debt, shares)
                col[f"g={g*100:.1f}%"] = round(r['per_share_value'], 2)
            except:
                col[f"g={g*100:.1f}%"] = "N/A"
        data[f"WACC={wacc*100:.1f}%"] = col
    return pd.DataFrame(data)


# ════════════════════════════════════════════════════════
# 3. 相对估值（PE / PB / PS）
# ════════════════════════════════════════════════════════

def relative_value(EPS: float, BVPS: float, SalesPS: float,
                   PE_peers: float, PB_peers: float, PS_peers: float,
                   weight_pe: float = 0.4, weight_pb: float = 0.3,
                   weight_ps: float = 0.3) -> dict:
    """
    加权相对估值
    返回各方法估值及综合估值
    """
    val_pe = EPS * PE_peers if EPS and PE_peers else None
    val_pb = BVPS * PB_peers if BVPS and PB_peers else None
    val_ps = SalesPS * PS_peers if SalesPS and PS_peers else None

    vals, weights = [], []
    for v, w in [(val_pe, weight_pe), (val_pb, weight_pb), (val_ps, weight_ps)]:
        if v is not None:
            vals.append(v * w)
            weights.append(w)
    composite = sum(vals) / sum(weights) if weights else None

    return {
        'PE估值': round(val_pe, 2) if val_pe else None,
        'PB估值': round(val_pb, 2) if val_pb else None,
        'PS估值': round(val_ps, 2) if val_ps else None,
        '综合估值': round(composite, 2) if composite else None
    }


def relative_batch(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        try:
            r = relative_value(
                EPS=row.get('EPS', 0), BVPS=row.get('BVPS', 0),
                SalesPS=row.get('SalesPS', 0),
                PE_peers=row.get('PE_peers', 0), PB_peers=row.get('PB_peers', 0),
                PS_peers=row.get('PS_peers', 0)
            )
            results.append({
                'Ticker': row['Ticker'],
                'Company': row.get('Company', ''),
                **r,
                '当前价格': row.get('Price', None),
                '状态': '✅ 正常'
            })
        except Exception as e:
            results.append({'Ticker': row['Ticker'], '状态': f'❌ {e}'})
    result_df = pd.DataFrame(results)
    result_df = _add_upside(result_df, value_col='综合估值')
    return result_df


# ════════════════════════════════════════════════════════
# 4. 实物期权（Black-Scholes）
# ════════════════════════════════════════════════════════

def black_scholes_call(S: float, K: float, T: float,
                       r: float, sigma: float, q: float = 0.0) -> dict:
    """
    Black-Scholes 欧式看涨期权
    S: 标的资产现值; K: 执行价格; T: 到期年限
    r: 无风险利率(小数); sigma: 波动率(小数); q: 股息率(小数)
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        raise ValueError("T、sigma、S 必须为正数")
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call = S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    delta = math.exp(-q * T) * norm.cdf(d1)
    return {
        'call_value': round(call, 4),
        'd1': round(d1, 4), 'd2': round(d2, 4),
        'delta': round(delta, 4),
        'N_d1': round(norm.cdf(d1), 4),
        'N_d2': round(norm.cdf(d2), 4)
    }


def realoption_batch(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        try:
            r = black_scholes_call(
                S=row['S'], K=row['K'], T=row['T'],
                r=row['r'] / 100, sigma=row['sigma'] / 100,
                q=row.get('q', 0) / 100
            )
            results.append({
                'Project': row.get('Project', row.get('Ticker', '')),
                '期权价值': r['call_value'],
                'Delta': r['delta'],
                'd1': r['d1'], 'd2': r['d2'],
                '状态': '✅ 正常'
            })
        except Exception as e:
            results.append({'Project': row.get('Project', ''), '状态': f'❌ {e}'})
    return pd.DataFrame(results)


def realoption_sensitivity(S: float, K: float, T: float,
                           r: float, sigma_base: float) -> pd.DataFrame:
    """敏感性：sigma vs T"""
    sig_range = [sigma_base + d for d in [-0.1, -0.05, 0, 0.05, 0.1]]
    t_range = [max(0.5, T + d) for d in [-2, -1, 0, 1, 2]]
    data = {}
    for t in t_range:
        col = {}
        for sig in sig_range:
            try:
                v = black_scholes_call(S, K, t, r / 100, sig)['call_value']
                col[f"σ={sig*100:.0f}%"] = v
            except:
                col[f"σ={sig*100:.0f}%"] = "N/A"
        data[f"T={t:.1f}年"] = col
    return pd.DataFrame(data)


# ════════════════════════════════════════════════════════
# 5. 因子模型
# ════════════════════════════════════════════════════════

FACTOR_WEIGHTS = {
    'ROE': 0.20, 'PE': -0.20, 'PB': -0.15,
    'DY': 0.15, 'NPM': 0.15, 'PCF': -0.10, 'Beta': -0.05
}

def factor_score(row: dict, weights: dict = None) -> float:
    """
    对单只股票计算标准化因子得分（越高越好）
    weights: 因子权重字典，负值表示越小越好
    """
    if weights is None:
        weights = FACTOR_WEIGHTS
    scores = {}
    for factor, w in weights.items():
        val = row.get(factor)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            scores[factor] = val * w
    if not scores:
        return 0.0
    return sum(scores.values())


def factor_batch(df: pd.DataFrame, weights: dict = None) -> pd.DataFrame:
    """
    批量因子打分 + 排名
    df 推荐列: Ticker, ROE, PE, PB, DY, NPM, PCF, Beta, Price, MarketCap
    """
    if weights is None:
        weights = FACTOR_WEIGHTS
    # 先对每个因子做 z-score 标准化
    numeric_factors = [f for f in weights.keys() if f in df.columns]
    df_norm = df.copy()
    for col in numeric_factors:
        mean, std = df[col].mean(), df[col].std()
        df_norm[col] = (df[col] - mean) / (std + 1e-9)

    df_norm['综合得分'] = df_norm.apply(
        lambda r: factor_score(r.to_dict(), weights), axis=1
    )
    df_norm['综合得分'] = df_norm['综合得分'].round(4)
    df_norm['排名'] = df_norm['综合得分'].rank(ascending=False).astype(int)

    keep_cols = ['Ticker'] + (['Company'] if 'Company' in df.columns else []) + \
                numeric_factors + ['综合得分', '排名'] + \
                (['Price'] if 'Price' in df.columns else [])
    return df_norm[[c for c in keep_cols if c in df_norm.columns]].sort_values('排名')


# ════════════════════════════════════════════════════════
# 6. Graham 选股法则
# ════════════════════════════════════════════════════════

GRAHAM_RULES = {
    'R1_营收': lambda r: r.get('Revenue', 0) >= 1e8,
    'R2_流动比率': lambda r: r.get('CurrentRatio', 0) >= 2.0,
    'R3_连续盈利': lambda r: r.get('ProfitYears', 0) >= 10,
    'R4_分红记录': lambda r: r.get('DividendYears', 0) >= 20,
    'R5_盈利增长': lambda r: r.get('EPSGrowth10yr', 0) >= 0.33,
    'R6_PE限制': lambda r: r.get('PE', 999) <= 15,
    'R7_PB限制': lambda r: r.get('PB', 999) <= 1.5,
}

def graham_check(row: dict) -> dict:
    results = {}
    for name, rule in GRAHAM_RULES.items():
        try:
            results[name] = '✅' if rule(row) else '❌'
        except:
            results[name] = '⚠️'
    results['通过条数'] = list(results.values()).count('✅')
    results['是否推荐'] = '⭐ 推荐' if results['通过条数'] >= 6 else (
        '🔶 关注' if results['通过条数'] >= 4 else '❌ 不符合'
    )
    return results


def graham_batch(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in df.iterrows():
        r = {'Ticker': row['Ticker'], 'Company': row.get('Company', '')}
        r.update(graham_check(row.to_dict()))
        results.append(r)
    return pd.DataFrame(results).sort_values('通过条数', ascending=False)


# ════════════════════════════════════════════════════════
# 公用工具函数
# ════════════════════════════════════════════════════════

def _add_upside(df: pd.DataFrame,
                value_col: str = '内在价值',
                price_col: str = '当前价格') -> pd.DataFrame:
    """计算上涨空间%，并添加高估/低估标记"""
    if value_col not in df.columns or price_col not in df.columns:
        return df
    df = df.copy()
    mask = df[value_col].notna() & df[price_col].notna() & (df[price_col] > 0)
    df.loc[mask, '上涨空间%'] = (
        (df.loc[mask, value_col] - df.loc[mask, price_col]) /
        df.loc[mask, price_col] * 100
    ).round(1)
    df.loc[mask, '估值判断'] = df.loc[mask, '上涨空间%'].apply(
        lambda x: '🟢 低估' if x > 10 else ('🔴 高估' if x < -10 else '🟡 合理')
    )
    return df


def load_excel_template(model: str) -> pd.DataFrame:
    """返回各模型的 Excel 模板（空数据 + 列说明）"""
    templates = {
        'DDM': pd.DataFrame(columns=['Ticker', 'Company', 'D0', 'g', 'r', 'Price', 'years_high', 'g_stable']),
        'DCF': pd.DataFrame(columns=['Ticker', 'Company', 'FCFF0', 'g_high', 'years_high', 'g_stable', 'WACC', 'Debt', 'Shares', 'Price']),
        'Relative': pd.DataFrame(columns=['Ticker', 'Company', 'EPS', 'BVPS', 'SalesPS', 'PE_peers', 'PB_peers', 'PS_peers', 'Price']),
        'RealOption': pd.DataFrame(columns=['Project', 'S', 'K', 'T', 'sigma', 'r', 'q']),
        'Factor': pd.DataFrame(columns=['Ticker', 'Company', 'ROE', 'PE', 'PB', 'DY', 'NPM', 'PCF', 'Beta', 'Price', 'MarketCap']),
        'Graham': pd.DataFrame(columns=['Ticker', 'Company', 'Revenue', 'CurrentRatio', 'ProfitYears', 'DividendYears', 'EPSGrowth10yr', 'PE', 'PB']),
    }
    return templates.get(model, pd.DataFrame())
