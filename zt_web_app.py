import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats

# 1. 网页基础美化配置
st.set_page_config(
    page_title="正态分布分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式，让界面更整洁
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stExpander"] { border: none; box-shadow: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 ZT Pro 数据正态分析工作站")
st.caption("专业的混合数据清洗、交互式绘图与深度统计推断工具")

# --- 侧边栏：模块化配置 ---
with st.sidebar:
    st.header("⚙️ 控制面板")
    
    # 数据上传模块
    st.subheader("1. 导入数据")
    uploaded_file = st.file_uploader("上传 Excel / CSV (支持混合文本列)", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            st.success("✅ 文件加载成功")
        except Exception as e:
            st.error(f"❌ 读取错误: {e}")
            st.stop()

        # 列选择
        all_cols = df.columns.tolist()
        column_name = st.selectbox("🎯 选择分析目标列", all_cols)

        st.markdown("---")
        st.subheader("2. 分析参数")
        
        # 智能数据清洗
        raw_series = df[column_name]
        clean_data = pd.to_numeric(raw_series, errors='coerce').dropna()
        n_count = len(clean_data)

        if n_count > 1:
            d_min, d_max = float(clean_data.min()), float(clean_data.max())
            
            # 参数交互
            bin_width = st.number_input("📏 设置组距 (Bin Width)", min_value=0.0001, value=(d_max-d_min)/10 if d_max!=d_min else 1.0, step=0.1)
            
            x_min = st.number_input("📉 横轴起始值", value=d_min)
            x_max = st.number_input("📈 横轴结束值", value=d_max)
            
            # 置信区间范围优化：60-100
            conf_level = st.slider("⚖️ 置信区间水平 (%)", 60, 100, 95) / 100.0
        else:
            st.warning("⚠️ 该列有效数字不足")

# --- 主界面内容 ---
if uploaded_file and n_count > 1:
    # 定义标签页，让界面整洁
    tab1, tab2, tab3 = st.tabs(["📈 图形可视化", "📋 统计报告", "🔍 数据预览"])

    # --- 计算统计量 ---
    total_mean = clean_data.mean()
    total_std = clean_data.std()
    total_var = clean_data.var()
    
    # 范围过滤数据统计
    range_data = clean_data[(clean_data >= x_min) & (clean_data <= x_max)]
    range_mean = range_data.mean() if len(range_data) > 0 else np.nan
    
    # 置信区间计算 (处理 100% 的特殊情况)
    if conf_level < 1.0:
        ci_lower, ci_upper = stats.t.interval(conf_level, df=n_count-1, loc=total_mean, scale=total_std/np.sqrt(n_count))
    else:
        ci_lower, ci_upper = -np.inf, np.inf # 100% 理论上涵盖所有可能

    with tab1:
        # 绘图区域
        bins = np.arange(x_min, x_max + bin_width, bin_width)
        counts, bin_edges = np.histogram(clean_data, bins=bins)
        proportions = counts / n_count
        bin_centers = bin_edges[:-1] + bin_width / 2

        fig = go.Figure()

        # 柱状图：带占比标签
        fig.add_trace(go.Bar(
            x=bin_centers,
            y=proportions,
            width=bin_width * 0.9,
            text=[f'{p*100:.1f}%' if p > 0 else '' for p in proportions],
            textposition='outside',
            name='区间频率占比',
            marker=dict(color='rgb(55, 83, 109)', opacity=0.8)
        ))

        # 正态分布曲线
        x_curve = np.linspace(x_min, x_max, 500)
        y_curve = stats.norm.pdf(x_curve, total_mean, total_std) * bin_width
        fig.add_trace(go.Scatter(
            x=x_curve, y=y_curve, mode='lines', 
            name='理论正态曲线',
            line=dict(color='rgb(219, 64, 82)', width=3)
        ))

        fig.update_layout(
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis_title=f"数值范围 ({column_name})",
            yaxis_title="占比频率",
            template="simple_white",
            height=600,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📊 核心深度统计")
        
        # 使用 Metric 展示重要均值对比
        c1, c2, c3 = st.columns(3)
        c1.metric("所有数据均值", f"{total_mean:.4f}")
        c2.metric(f"选定范围均值", f"{range_mean:.4f}" if not np.isnan(range_mean) else "N/A")
        c3.metric("有效样本量", f"{n_count}")

        st.markdown("---")
        
        # 详细统计参数
        c4, c5, c6 = st.columns(3)
        c4.write(f"**方差 (Variance):** {total_var:.4f}")
        c5.write(f"**标准差 (Std Dev):** {total_std:.4f}")
        c6.write(f"**过滤行数:** {len(raw_series) - n_count}")

        # 置信区间卡片
        if conf_level < 1.0:
            st.info(f"📍 **{int(conf_level*100)}% 置信区间:** 真实均值约有 {int(conf_level*100)}% 的概率落在区间 `[{ci_lower:.4f}, {ci_upper:.4f}]` 内。")
        else:
            st.warning("📍 **100% 置信区间:** 理论上涵盖所有数值范围 (-∞, +∞)。")

    with tab3:
        st.subheader("📄 数据清洗预览")
        st.write(f"以下是 **{column_name}** 列清洗后的前 100 条有效数字数据：")
        st.dataframe(clean_data.head(100), use_container_width=True)

elif uploaded_file:
    st.error("❌ 无法进行分析。请确保选定的列中包含至少 2 个有效的数字。")

else:
    # 初始引导页
    st.info("💡 **快速开始：** 请在左侧侧边栏上传您的数据文件（CSV 或 Excel）。")
    col_a, col_b = st.columns(2)
    with col_a:
        st.image("https://img.icons8.com/clouds/200/000000/data-configuration.png")
    with col_b:
        st.markdown("""
        ### 软件优势：
        - **智能识别：** 自动剔除混合列中的文字、符号。
        - **精准占比：** 柱状图上方实时标注百分比。
        - **交互调节：** 动态修改组距和坐标显示范围。
        - **置信区间：** 支持 60% 到 100% 的自由设定。
        """)
