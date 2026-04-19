import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os

# 1. 页面基本配置
st.set_page_config(
    page_title="股票估值分析工具",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 安全读取和保存配置文件
def load_config():
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        st.error(f"未找到配置文件: {config_path}")
        st.stop()
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.load(file, Loader=SafeLoader)

def save_config(config):
    with open('config.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False)

config = load_config()

# 3. 初始化认证对象
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 4. 登录/注册逻辑处理
if not st.session_state.get("authentication_status"):
    # 在未登录时，提供一个选择框切换 登录 或 注册
    tab1, tab2 = st.tabs(["🔐 用户登录", "📝 新用户注册"])
    
    with tab1:
        # 登录界面
        authenticator.login(location='main')
        if st.session_state["authentication_status"] is False:
            st.error('用户名/密码错误')
        elif st.session_state["authentication_status"] is None:
            st.warning('请输入用户名和密码')

    with tab2:
        # 注册界面
        try:
            # pre_authorized 是预授权名单，如果不限制则留空列表
            email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(pre_authorized=[], location='main')
            if email_of_registered_user:
                # 重要：注册成功后必须将 config 对象写回 yaml 文件
                save_config(config)
                st.success('注册成功！现在请切换到登录标签进行登录。')
        except Exception as e:
            st.error(f"注册出错: {e}")

# 5. 主界面逻辑（登录成功后）
if st.session_state["authentication_status"]:
    
    # ── 侧边栏 ──────────────────────────────────────────────
    with st.sidebar:
        st.write(f"欢迎回来, **{st.session_state['name']}**")
        authenticator.logout('退出登录', 'sidebar')
        st.divider()

    # ── 全局样式 ──────────────────────────────────────────────
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Noto Sans SC', sans-serif; }
        .main-title {
            font-size: 2.4rem; font-weight: 700;
            background: linear-gradient(135deg, #1a3a5c, #2e7bcf);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        .subtitle { color: #6b7280; font-size: 1rem; margin-bottom: 2rem; }
        .model-card {
            background: white; border: 1px solid #e5e7eb;
            border-radius: 12px; padding: 1.5rem;
            min-height: 180px;
            transition: all 0.2s; 
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }
        .model-card:hover { 
            box-shadow: 0 6px 20px rgba(46,123,207,0.15); 
            transform: translateY(-2px); 
            border-color: #2e7bcf;
        }
        .model-card h3 { color: #1a3a5c; margin-top:0; margin-bottom: 0.4rem; font-size: 1.1rem; }
        .model-card p { color: #6b7280; font-size: 0.85rem; line-height: 1.5; }
        .tag {
            display: inline-block; background: #eff6ff; color: #2563eb;
            border-radius: 99px; padding: 2px 10px; font-size: 0.75rem;
            margin-top: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ── 首页内容 ──────────────────────────────────────────────
    st.markdown('<p class="main-title">📈 股票估值分析工具</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">你好 {st.session_state["name"]}，请选择估值模型，一键获得分析结果</p>', unsafe_allow_html=True)
    
    models = [
        {"icon": "💰", "name": "DDM 股利贴现模型", "desc": "基于未来股利现值计算内在价值，适合持续派息的成熟企业。", "tag": "适合：银行、消费蓝筹", "page": "pages/1_DDM"},
        {"icon": "🔮", "name": "DCF/FCF 自由现金流模型", "desc": "多阶段折现自由现金流，最全面的基本面估值方法。", "tag": "适合：成长股、科技股", "page": "pages/2_DCF"},
        {"icon": "📊", "name": "相对估值（PE/PB/PS）", "desc": "与同行比较 PE、PB、PS 倍数，快速判断高估或低估。", "tag": "适合：行业横向比较", "page": "pages/3_Relative"},
        {"icon": "🎲", "name": "或有估值（实物期权）", "desc": "用 Black-Scholes 模型对战略期权、资源储备进行定价。", "tag": "适合：矿业、生物医药", "page": "pages/4_RealOption"},
        {"icon": "🧮", "name": "因子模型与量化策略", "desc": "多因子综合打分，筛选高质量低估值股票池。", "tag": "适合：量化选股", "page": "pages/5_Factor"},
        {"icon": "🔍", "name": "Graham 选股法则", "desc": "格雷厄姆 7 条安全边际标准，经典价值投资筛选器。", "tag": "适合：价值投资者", "page": "pages/6_Graham"},
    ]
    
    cols = st.columns(3)
    for i, m in enumerate(models):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="model-card">
                <h3>{m['icon']} {m['name']}</h3>
                <p>{m['desc']}</p>
                <span class="tag">{m['tag']}</span>
            </div>
            """, unsafe_allow_html=True)
            # 注意：请确保你的项目目录下有 pages 文件夹且包含对应的 .py 文件
            try:
                st.page_link(f"{m['page']}.py", label=f"进入分析 →", use_container_width=True)
            except:
                st.button(f"{m['name']} (暂未上线)", disabled=True, key=f"btn_{i}")
            st.write("") 
    
    st.divider()
    st.info("**使用流程：** 选择模型 → 下载 Excel 模板 → 填入数据 → 上传 → 点击计算 → 查看结果与图表")
