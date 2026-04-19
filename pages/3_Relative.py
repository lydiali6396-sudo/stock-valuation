import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.calc import relative_value, relative_batch, load_excel_template
from utils.ui_components import apply_page_style, page_header, render_intro, render_upload, render_results

st.set_page_config(page_title="相对估值", page_icon="📊", layout="wide")
apply_page_style()
page_header("📊", "相对估值（PE / PB / PS）", "与同行比较估值倍数，快速判断高估或低估")

tab1, tab2, tab3 = st.tabs(["📖 原理介绍", "📤 数据上传与计算", "📊 结果分析"])

with tab1:
    render_intro(
        principle="""相对估值法通过将目标公司的基本面指标（EPS、BVPS、SalesPS）
        乘以行业平均/可比公司的估值倍数（PE、PB、PS），来估算合理股价。
        本工具支持三种方法加权合并，并可自定义各方法权重。
        <b>综合估值 = PE估值×权重 + PB估值×权重 + PS估值×权重</b>""",
        inputs_df=pd.DataFrame({
            '参数': ['EPS', 'BVPS', 'SalesPS', 'PE_peers', 'PB_peers', 'PS_peers'],
            '含义': ['每股收益（元）', '每股净资产（元）', '每股销售额（元）',
                     '同行平均PE', '同行平均PB', '同行平均PS'],
            '示例': [3.5, 20.0, 50.0, 15, 2.0, 1.5]
        }),
        pros=["直观易懂", "数据容易获取", "便于行业横向比较"],
        cons=["依赖可比公司质量", "不同行业倍数差异大", "无法反映绝对价值"],
        scenes=["银行、地产等传统行业", "快速横向筛选", "IPO定价参考"]
    )

with tab2:
    st.markdown('<div class="section-header">快速单股测试</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        EPS      = st.number_input("EPS 每股收益", value=3.5, step=0.1)
        BVPS     = st.number_input("BVPS 每股净资产", value=20.0, step=1.0)
        SalesPS  = st.number_input("SalesPS 每股销售额", value=50.0, step=1.0)
        price    = st.number_input("当前价格（可选）", value=0.0, step=1.0)
    with c2:
        PE_peers = st.number_input("PE 同行均值", value=15.0, step=0.5)
        PB_peers = st.number_input("PB 同行均值", value=2.0, step=0.1)
        PS_peers = st.number_input("PS 同行均值", value=1.5, step=0.1)
        st.markdown("**权重设置**")
        w_pe = st.slider("PE 权重", 0.0, 1.0, 0.4, 0.1)
        w_pb = st.slider("PB 权重", 0.0, 1.0, 0.3, 0.1)
        w_ps = st.slider("PS 权重", 0.0, 1.0, 0.3, 0.1)

    if st.button("🔵 计算相对估值", type="primary"):
        try:
            res = relative_value(EPS, BVPS, SalesPS, PE_peers, PB_peers, PS_peers, w_pe, w_pb, w_ps)
            c1, c2, c3, c4 = st.columns(4)
            for col, (k, v) in zip([c1, c2, c3, c4], res.items()):
                col.metric(k, f"¥{v:.2f}" if v else "N/A")
            if price > 0 and res['综合估值']:
                upside = (res['综合估值'] - price) / price * 100
                st.info(f"相对当前价格 ¥{price}，上涨空间：**{upside:.1f}%** ({'低估' if upside > 0 else '高估'})")
        except Exception as e:
            st.error(f"计算错误：{e}")

    st.divider()
    df_upload = render_upload("Relative", load_excel_template("Relative"))
    if 'rel_df' not in st.session_state:
        st.session_state.rel_df = None
    if df_upload is not None:
        if st.button("🚀 批量计算", type="primary"):
            with st.spinner("计算中..."):
                st.session_state.rel_df = relative_batch(df_upload)
            st.success("计算完成！请切换到「结果分析」Tab")

with tab3:
    render_results(st.session_state.get('rel_df'), value_col='综合估值')
