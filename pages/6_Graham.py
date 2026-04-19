import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.calc import graham_batch, load_excel_template
from utils.ui_components import apply_page_style, page_header, render_intro, render_upload

st.set_page_config(page_title="Graham 法则", page_icon="🔍", layout="wide")
apply_page_style()
page_header("🔍", "Graham 选股法则", "格雷厄姆7条安全边际标准，经典价值投资筛选器")

tab1, tab2, tab3 = st.tabs(["📖 原理介绍", "📤 数据上传与筛选", "📊 筛选结果"])

with tab1:
    render_intro(
        principle="""Benjamin Graham 在《聪明的投资者》中提出的7条防御型选股标准，
        通过严格的安全边际要求筛选出被严重低估的稳健企业。
        本工具逐条检验每只股票，通过≥6条标记为"推荐"，通过≥4条标记为"关注"。""",
        inputs_df=pd.DataFrame({
            '规则': ['R1_营收', 'R2_流动比率', 'R3_连续盈利', 'R4_分红记录',
                     'R5_盈利增长', 'R6_PE限制', 'R7_PB限制'],
            '条件': ['年营收≥1亿元', '流动比率≥2.0', '连续盈利年数≥10年',
                     '持续分红年数≥20年', '近10年EPS增长率≥33%', 'PE≤15', 'PB≤1.5'],
            '对应列': ['Revenue', 'CurrentRatio', 'ProfitYears', 'DividendYears',
                       'EPSGrowth10yr', 'PE', 'PB']
        }),
        pros=["标准明确客观", "注重安全边际", "经过长期市场验证"],
        cons=["标准过于保守，筛选后标的少", "不适合成长股", "部分数据难以获取"],
        scenes=["价值投资者长期持股", "熊市防御型配置", "A股低估值蓝筹筛选"]
    )

with tab2:
    st.markdown('<div class="section-header">单股快速检验</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        rev      = st.number_input("Revenue 年营收（万元）", value=20000.0, step=1000.0)
        cr       = st.number_input("CurrentRatio 流动比率", value=2.5, step=0.1)
        py       = st.number_input("ProfitYears 连续盈利年数", value=12, step=1)
        dy_years = st.number_input("DividendYears 分红年数", value=15, step=1)
    with c2:
        eps_g    = st.number_input("EPSGrowth10yr 10年EPS增长(%)", value=40.0, step=1.0)
        pe       = st.number_input("PE 市盈率", value=12.0, step=0.5)
        pb       = st.number_input("PB 市净率", value=1.2, step=0.1)

    if st.button("🔵 检验 Graham 标准", type="primary"):
        from utils.calc import graham_check
        row = {'Revenue': rev*1e4, 'CurrentRatio': cr, 'ProfitYears': py,
               'DividendYears': dy_years, 'EPSGrowth10yr': eps_g/100, 'PE': pe, 'PB': pb}
        result = graham_check(row)
        st.markdown(f"### 综合评定：{result['是否推荐']}（通过 {result['通过条数']}/7 条）")
        cols = st.columns(7)
        for col, (rule, val) in zip(cols, [(k, v) for k, v in result.items() if k.startswith('R')]):
            col.metric(rule.replace('_', '\n'), val)

    st.divider()
    df_upload = render_upload("Graham", load_excel_template("Graham"))
    if 'graham_df' not in st.session_state:
        st.session_state.graham_df = None
    if df_upload is not None:
        if st.button("🚀 批量筛选", type="primary"):
            with st.spinner("筛选中..."):
                st.session_state.graham_df = graham_batch(df_upload)
            st.success("筛选完成！请切换到「筛选结果」Tab")

with tab3:
    df = st.session_state.get('graham_df')
    if df is not None and not df.empty:
        filter_opt = st.radio("显示范围", ["全部", "⭐ 推荐", "🔶 关注"], horizontal=True)
        show_df = df if filter_opt == "全部" else df[df['是否推荐'] == filter_opt]
        st.dataframe(show_df, use_container_width=True, hide_index=True)
        import io
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buf.seek(0)
        st.download_button("⬇️ 下载筛选结果", data=buf, file_name="Graham筛选结果.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("请先上传数据并筛选")
