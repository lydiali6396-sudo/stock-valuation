import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.calc import dcf_value, dcf_batch, dcf_sensitivity, load_excel_template
from utils.ui_components import apply_page_style, page_header, render_intro, render_upload, render_results, render_sensitivity_heatmap

st.set_page_config(page_title="DCF 估值", page_icon="🔮", layout="wide")
apply_page_style()
page_header("🔮", "DCF / FCF 自由现金流模型", "两阶段折现自由现金流，最全面的基本面估值方法")

tab1, tab2, tab3 = st.tabs(["📖 原理介绍", "📤 数据上传与计算", "📊 结果分析"])

with tab1:
    render_intro(
        principle="""DCF（折现现金流）模型将企业未来产生的自由现金流（FCFF）折现到现值。
        本工具采用两阶段模型：<b>第一阶段</b>为高速增长期（g_high），持续 n 年；
        <b>第二阶段</b>为永续稳定增长期（g_stable）。
        企业价值 = Σ FCFF_t/(1+WACC)^t + 终值/(1+WACC)^n。
        减去净负债后得股权价值，再除以总股数得每股内在价值。""",
        inputs_df=pd.DataFrame({
            '参数': ['FCFF0', 'g_high', 'years_high', 'g_stable', 'WACC', 'Debt', 'Shares'],
            '含义': ['当前自由现金流（元）', '高增长期增长率（%）', '高增长持续年数',
                     '永续增长率（%）', '加权平均资本成本（%）', '净负债（元）', '总股本（股）'],
            '示例': ['5亿', '20', 5, 3, 10, '10亿', '1亿股']
        }),
        pros=["最全面，考虑现金流", "适合高成长公司", "可拆解终值占比风险"],
        cons=["假设多，误差可能大", "终值对结果影响巨大", "需要预测多年现金流"],
        scenes=["科技成长股", "新能源公司", "有可预测现金流的企业"]
    )

with tab2:
    st.markdown('<div class="section-header">快速单股测试</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    FCFF0      = c1.number_input("FCFF0（万元）", value=50000.0, step=1000.0)
    g_high     = c1.number_input("g_high 高增长率 (%)", value=20.0, step=1.0)
    years_high = c2.number_input("years_high 高增长年数", value=5, min_value=1, max_value=20)
    g_stable   = c2.number_input("g_stable 永续增长率 (%)", value=3.0, step=0.5)
    WACC       = c3.number_input("WACC (%)", value=10.0, step=0.5)
    debt       = c3.number_input("净负债（万元）", value=10000.0, step=1000.0)
    shares     = c3.number_input("总股本（万股）", value=10000.0, step=1000.0)

    if st.button("🔵 计算 DCF 估值", type="primary"):
        try:
            res = dcf_value(
                FCFF0 * 1e4, g_high/100, int(years_high),
                g_stable/100, WACC/100, debt*1e4, shares*1e4
            )
            c1, c2, c3 = st.columns(3)
            c1.metric("每股内在价值", f"¥{res['per_share_value']:.2f}")
            c2.metric("企业价值（亿）", f"{res['enterprise_value']/1e8:.2f}")
            c3.metric("终值占比", f"{res['terminal_pct']}%",
                      delta="⚠️ 终值占比过高" if res['terminal_pct'] > 75 else "正常")
            sens = dcf_sensitivity(
                FCFF0*1e4, g_high/100, int(years_high),
                g_stable/100, WACC/100, debt*1e4, shares*1e4
            )
            render_sensitivity_heatmap(sens, "敏感性分析（WACC vs g_high）")
        except Exception as e:
            st.error(f"计算错误：{e}")

    st.divider()
    df_upload = render_upload("DCF", load_excel_template("DCF"))
    if 'dcf_df' not in st.session_state:
        st.session_state.dcf_df = None
    if df_upload is not None:
        if st.button("🚀 批量计算", type="primary"):
            with st.spinner("计算中..."):
                st.session_state.dcf_df = dcf_batch(df_upload)
            st.success("计算完成！请切换到「结果分析」Tab")

with tab3:
    render_results(st.session_state.get('dcf_df'),
                   value_col='每股内在价值', price_col='当前价格')
