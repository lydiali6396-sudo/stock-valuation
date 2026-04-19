import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.calc import ddm_batch, ddm_sensitivity, ddm_gordon, load_excel_template
from utils.ui_components import apply_page_style, page_header, render_intro, render_upload, render_results, render_sensitivity_heatmap

st.set_page_config(page_title="DDM 估值", page_icon="💰", layout="wide")
apply_page_style()
page_header("💰", "DDM 股利贴现模型", "基于未来股利现值，计算股票内在价值")

tab1, tab2, tab3 = st.tabs(["📖 原理介绍", "📤 数据上传与计算", "📊 结果分析"])

# ── Tab1 ────────────────────────────────────────────────
with tab1:
    render_intro(
        principle="""DDM（股利贴现模型）认为股票价值等于所有未来股利的现值之和。
        最常用的 Gordon 增长模型公式为：<b>V = D₁ / (r − g)</b>，
        其中 D₁ 是下一期股利，r 是投资者要求的贴现率，g 是股利的永续增长率。
        本工具还支持<b>两阶段 DDM</b>：先高速增长若干年，再进入永续稳定增长阶段。""",
        inputs_df=pd.DataFrame({
            '参数': ['D0', 'g', 'r', 'years_high（可选）', 'g_stable（可选）'],
            '含义': ['当前年度每股股利（元）', '股利增长率（%）', '贴现率/要求回报率（%）',
                     '高增长阶段持续年数', '永续稳定增长率（%）'],
            '示例': [2.5, 8.0, 12.0, 5, 3.0]
        }),
        pros=["逻辑简洁，参数少", "适合稳定派息公司", "两阶段模型更贴近实际"],
        cons=["不适用于不派息成长股", "对 g 和 r 假设极敏感", "g ≥ r 时公式失效"],
        scenes=["银行、保险、电力等高息股", "成熟消费品牌", "公用事业公司"]
    )

# ── Tab2 ────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">快速单股测试（手动输入）</div>', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    D0    = col1.number_input("D0 当前股利", value=2.5, step=0.1)
    g     = col2.number_input("g 增长率 (%)", value=8.0, step=0.5)
    r     = col3.number_input("r 贴现率 (%)", value=12.0, step=0.5)
    price = col4.number_input("当前价格（可选）", value=0.0, step=1.0)
    stage = col5.checkbox("启用两阶段")

    years_high = g_stable = None
    if stage:
        c1, c2 = st.columns(2)
        years_high = c1.number_input("高增长年数", value=5, min_value=1, max_value=20)
        g_stable   = c2.number_input("永续增长率 (%)", value=3.0, step=0.5)

    if st.button("🔵 计算单股估值", type="primary"):
        try:
            from utils.calc import ddm_gordon, ddm_multistage
            if stage:
                val = ddm_multistage(D0, g/100, int(years_high), g_stable/100, r/100)
                model_name = "两阶段DDM"
            else:
                val = ddm_gordon(D0, g/100, r/100)
                model_name = "Gordon DDM"
            upside = (val - price) / price * 100 if price > 0 else None
            c1, c2, c3 = st.columns(3)
            c1.metric("内在价值", f"¥{val:.2f}")
            if price > 0:
                c2.metric("当前价格", f"¥{price:.2f}")
                c3.metric("上涨空间", f"{upside:.1f}%",
                          delta=f"{'低估' if upside > 0 else '高估'}")
            # 敏感性
            sens = ddm_sensitivity(D0, g/100, r/100)
            render_sensitivity_heatmap(sens, "敏感性分析（g vs r）")
        except Exception as e:
            st.error(f"计算错误：{e}")

    st.divider()
    df_upload = render_upload("DDM", load_excel_template("DDM"))
    if 'ddm_df' not in st.session_state:
        st.session_state.ddm_df = None
    if df_upload is not None:
        if st.button("🚀 批量计算", type="primary"):
            with st.spinner("计算中..."):
                st.session_state.ddm_df = ddm_batch(df_upload)
            st.success("计算完成！请切换到「结果分析」Tab")

# ── Tab3 ────────────────────────────────────────────────
with tab3:
    render_results(st.session_state.get('ddm_df'))
