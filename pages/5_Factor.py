import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.calc import factor_batch, FACTOR_WEIGHTS, load_excel_template
from utils.ui_components import apply_page_style, page_header, render_intro, render_upload

st.set_page_config(page_title="因子模型", page_icon="🧮", layout="wide")
apply_page_style()
page_header("🧮", "因子模型与量化策略", "多因子综合打分，筛选高质量低估值股票")

tab1, tab2, tab3 = st.tabs(["📖 原理介绍", "📤 数据上传与计算", "📊 结果分析"])

with tab1:
    render_intro(
        principle="""因子模型将各财务指标标准化（z-score）后按权重加权，
        正权重因子（如ROE、DY）越高越好，负权重因子（如PE、PB）越低越好。
        综合得分 = Σ(标准化因子值 × 权重)。
        得分越高的股票越被认为是"高质量低估值"的优选标的。
        支持自定义各因子权重。""",
        inputs_df=pd.DataFrame({
            '因子': ['ROE', 'PE', 'PB', 'DY', 'NPM', 'PCF', 'Beta'],
            '含义': ['净资产收益率(%)', '市盈率', '市净率', '股息率(%)', '净利润率(%)', '市现率', '贝塔系数'],
            '默认权重': [0.20, -0.20, -0.15, 0.15, 0.15, -0.10, -0.05]
        }),
        pros=["综合多维度信息", "可客制化权重", "适合批量选股"],
        cons=["历史数据不代表未来", "权重设定主观性强", "需要较多数据列"],
        scenes=["量化选股", "指数增强策略", "股票池初筛"]
    )

with tab2:
    st.markdown('<div class="section-header">自定义因子权重</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    custom_weights = {}
    for i, (factor, default_w) in enumerate(FACTOR_WEIGHTS.items()):
        with cols[i % 4]:
            custom_weights[factor] = st.number_input(
                f"{factor} 权重", value=default_w, step=0.05,
                min_value=-1.0, max_value=1.0, key=f"w_{factor}"
            )
    st.caption("💡 正值=越大越好，负值=越小越好。建议权重绝对值之和接近1。")
    st.divider()

    df_upload = render_upload("Factor", load_excel_template("Factor"))
    if 'factor_df' not in st.session_state:
        st.session_state.factor_df = None
    if df_upload is not None:
        if st.button("🚀 批量计算因子得分", type="primary"):
            with st.spinner("标准化 & 计算中..."):
                st.session_state.factor_df = factor_batch(df_upload, custom_weights)
            st.success("计算完成！请切换到「结果分析」Tab")

with tab3:
    df = st.session_state.get('factor_df')
    if df is not None and not df.empty:
        st.markdown('<div class="section-header">因子得分排名</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if 'Ticker' in df.columns and '综合得分' in df.columns:
            fig = px.bar(df.head(20), x='Ticker', y='综合得分',
                         color='综合得分', color_continuous_scale='Blues',
                         title='Top 20 综合因子得分')
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)
        # 下载
        import io
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buf.seek(0)
        st.download_button("⬇️ 下载因子得分结果", data=buf,
                           file_name="因子得分.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("请先上传数据并计算")
