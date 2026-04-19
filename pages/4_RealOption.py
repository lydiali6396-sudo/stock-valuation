import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.calc import black_scholes_call, realoption_batch, realoption_sensitivity, load_excel_template
from utils.ui_components import apply_page_style, page_header, render_intro, render_upload, render_sensitivity_heatmap

st.set_page_config(page_title="实物期权", page_icon="🎲", layout="wide")
apply_page_style()
page_header("🎲", "或有估值（实物期权）", "用 Black-Scholes 模型对战略期权和资源储备定价")

tab1, tab2, tab3 = st.tabs(["📖 原理介绍", "📤 数据上传与计算", "📊 结果分析"])

with tab1:
    render_intro(
        principle="""实物期权将企业的战略机会（如扩张权、放弃权、资源开采权）类比为金融期权。
        使用 <b>Black-Scholes 模型</b>：C = S·e^(−qT)·N(d1) − K·e^(−rT)·N(d2)
        其中 S 为标的资产现值（如矿藏价值），K 为执行价格（如开采成本），
        T 为决策期限，σ 为资产价值的波动率，r 为无风险利率。""",
        inputs_df=pd.DataFrame({
            '参数': ['S', 'K', 'T', 'sigma', 'r', 'q（可选）'],
            '含义': ['标的资产现值（元）', '执行价格/投入成本（元）', '期权到期年限',
                     '标的资产价值波动率（%）', '无风险利率（%）', '股息率/泄漏率（%）'],
            '示例': ['10亿', '7亿', 3, 35, 3, 0]
        }),
        pros=["能对战略灵活性定价", "反映不确定性的价值", "适合资源类资产"],
        cons=["参数估计困难", "假设资产价值符合对数正态分布", "模型复杂度高"],
        scenes=["矿业、油气资源公司", "生物医药研发管线", "科技公司战略并购"]
    )

with tab2:
    st.markdown('<div class="section-header">单项目计算</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    S     = c1.number_input("S 标的资产现值（万元）", value=10000.0, step=500.0)
    K     = c1.number_input("K 执行价格（万元）", value=7000.0, step=500.0)
    T     = c2.number_input("T 期限（年）", value=3.0, step=0.5, min_value=0.1)
    sigma = c2.number_input("σ 波动率 (%)", value=35.0, step=1.0)
    r_rf  = c3.number_input("r 无风险利率 (%)", value=3.0, step=0.1)
    q     = c3.number_input("q 股息率 (%)", value=0.0, step=0.1)

    if st.button("🔵 计算期权价值", type="primary"):
        try:
            res = black_scholes_call(S*1e4, K*1e4, T, r_rf/100, sigma/100, q/100)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("期权价值（万元）", f"{res['call_value']/1e4:.1f}")
            c2.metric("Delta", f"{res['delta']:.4f}")
            c3.metric("N(d1)", f"{res['N_d1']:.4f}")
            c4.metric("N(d2)", f"{res['N_d2']:.4f}")
            sens = realoption_sensitivity(S*1e4, K*1e4, T, r_rf, sigma/100)
            render_sensitivity_heatmap(sens, "敏感性分析（σ vs T）")
        except Exception as e:
            st.error(f"计算错误：{e}")

    st.divider()
    df_upload = render_upload("RealOption", load_excel_template("RealOption"))
    if 'ro_df' not in st.session_state:
        st.session_state.ro_df = None
    if df_upload is not None:
        if st.button("🚀 批量计算", type="primary"):
            with st.spinner("计算中..."):
                st.session_state.ro_df = realoption_batch(df_upload)
            st.success("计算完成！")

with tab3:
    if st.session_state.get('ro_df') is not None:
        st.dataframe(st.session_state.ro_df, use_container_width=True, hide_index=True)
    else:
        st.info("请先上传数据并计算")
