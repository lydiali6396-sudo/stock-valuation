"""
utils/ui_components.py
共用 UI 组件：上传、结果展示、图表、敏感性分析
"""
import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np


# ── 通用样式 ──────────────────────────────────────────────
PAGE_STYLE = """
<style>
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #1a3a5c;
        border-left: 4px solid #2e7bcf; padding-left: 0.8rem;
        margin: 1.5rem 0 1rem 0;
    }
    .info-card {
        background: #f0f7ff; border-radius: 10px;
        padding: 1rem 1.2rem; margin: 0.5rem 0;
        border: 1px solid #c3dafe;
    }
    .warn-card {
        background: #fff7ed; border-radius: 10px;
        padding: 1rem 1.2rem; margin: 0.5rem 0;
        border: 1px solid #fcd9a8;
    }
    .metric-card {
        text-align: center; background: white;
        border: 1px solid #e5e7eb; border-radius: 10px;
        padding: 1rem;
    }
    .metric-value { font-size: 1.6rem; font-weight: 700; color: #1a3a5c; }
    .metric-label { font-size: 0.8rem; color: #6b7280; }
    div[data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 10px; }
</style>
"""

def apply_page_style():
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)


# ── 页面顶部 Header ─────────────────────────────────────
def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"## {icon} {title}")
    if subtitle:
        st.markdown(f"<p style='color:#6b7280;margin-top:-0.5rem'>{subtitle}</p>",
                    unsafe_allow_html=True)
    st.divider()


# ── Tab1：原理介绍 ───────────────────────────────────────
def render_intro(principle: str, inputs_df: pd.DataFrame,
                 pros: list, cons: list, scenes: list):
    """
    principle: 原理文字
    inputs_df: 输入参数说明 DataFrame（列名, 含义, 示例值）
    pros/cons/scenes: 优点、缺点、适合场景列表
    """
    st.markdown('<div class="section-header">核心原理</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="info-card">{principle}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">输入参数说明</div>', unsafe_allow_html=True)
    st.dataframe(inputs_df, use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**✅ 优点**")
        for p in pros:
            st.markdown(f"- {p}")
    with col2:
        st.markdown("**⚠️ 局限性**")
        for c in cons:
            st.markdown(f"- {c}")
    with col3:
        st.markdown("**🎯 适合场景**")
        for s in scenes:
            st.markdown(f"- {s}")


# ── Tab2：Excel 上传 & 手动输入 ─────────────────────────
def render_upload(model_key: str, template_df: pd.DataFrame) -> pd.DataFrame | None:
    """返回用户上传或手动输入的 DataFrame，未就绪则返回 None"""
    st.markdown('<div class="section-header">上传数据</div>', unsafe_allow_html=True)

    # 下载模板
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='数据')
        # 说明sheet
        hint = pd.DataFrame({'说明': ['请按照模板列名填入数据', '删除此说明行后上传', 'g/r/sigma等利率列请填百分比数字，如: 8 代表8%']})
        hint.to_excel(writer, index=False, sheet_name='说明')
    buf.seek(0)
    st.download_button(
        f"⬇️ 下载 {model_key} Excel 模板",
        data=buf,
        file_name=f"{model_key}_模板.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    uploaded = st.file_uploader("拖拽上传 Excel 文件（.xlsx）", type=["xlsx"])
    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            st.success(f"✅ 已读取 {len(df)} 行数据")
            with st.expander("预览前10行"):
                st.dataframe(df.head(10), use_container_width=True)
            return df
        except Exception as e:
            st.error(f"读取失败：{e}")
    return None


# ── Tab3：结果展示 ───────────────────────────────────────
def render_results(result_df: pd.DataFrame,
                   value_col: str = '内在价值',
                   price_col: str = '当前价格'):
    """结果表 + 图表 + 下载"""
    if result_df is None or result_df.empty:
        st.info("暂无结果，请先上传数据并点击计算")
        return

    # KPI 指标卡
    valid = result_df[result_df[value_col].notna()] if value_col in result_df.columns else result_df
    total = len(result_df)
    success = len(valid)
    if '估值判断' in result_df.columns:
        undervalued = (result_df['估值判断'] == '🟢 低估').sum()
        overvalued = (result_df['估值判断'] == '🔴 高估').sum()
    else:
        undervalued = overvalued = 0

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in zip(
        [c1, c2, c3, c4],
        [total, success, undervalued, overvalued],
        ['总股票数', '计算成功', '低估股票', '高估股票']
    ):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("")

    # 结果表
    st.markdown('<div class="section-header">估值结果表</div>', unsafe_allow_html=True)
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    # 柱状图：内在价值 vs 当前价格
    if value_col in result_df.columns and price_col in result_df.columns:
        plot_df = valid[[col for col in ['Ticker', value_col, price_col] if col in valid.columns]].dropna()
        if not plot_df.empty and 'Ticker' in plot_df.columns:
            fig = go.Figure()
            fig.add_bar(x=plot_df['Ticker'], y=plot_df[value_col], name='内在价值', marker_color='#2e7bcf')
            fig.add_bar(x=plot_df['Ticker'], y=plot_df[price_col], name='当前价格', marker_color='#f59e0b')
            fig.update_layout(
                barmode='group', title='内在价值 vs 当前价格',
                plot_bgcolor='white', paper_bgcolor='white',
                font_family='sans-serif', height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        # 上涨空间分布
        if '上涨空间%' in result_df.columns:
            up_df = result_df[['Ticker', '上涨空间%']].dropna()
            if not up_df.empty:
                fig2 = px.bar(
                    up_df.sort_values('上涨空间%', ascending=False),
                    x='Ticker', y='上涨空间%',
                    color='上涨空间%',
                    color_continuous_scale=['#ef4444', '#f59e0b', '#22c55e'],
                    title='各股票上涨空间 (%)'
                )
                fig2.add_hline(y=0, line_dash='dash', line_color='gray')
                fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=350)
                st.plotly_chart(fig2, use_container_width=True)

    # 下载结果
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False, sheet_name='估值结果')
    out_buf.seek(0)
    st.download_button(
        "⬇️ 下载结果 Excel",
        data=out_buf,
        file_name="估值结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ── 敏感性分析热力图 ─────────────────────────────────────
def render_sensitivity_heatmap(sens_df: pd.DataFrame, title: str = "敏感性分析"):
    """将敏感性 DataFrame 渲染为热力图"""
    if sens_df is None or sens_df.empty:
        return
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    try:
        numeric_df = sens_df.apply(pd.to_numeric, errors='coerce')
        fig = px.imshow(
            numeric_df,
            text_auto=True,
            color_continuous_scale='RdYlGn',
            title=title, aspect='auto'
        )
        fig.update_layout(height=350, paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"热力图渲染失败：{e}")
        st.dataframe(sens_df, use_container_width=True)
