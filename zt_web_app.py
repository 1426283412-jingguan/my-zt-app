import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io

# --- 1. 页面配置 ---
st.set_page_config(page_title="高级正态分布分析工具", layout="wide")

st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #ececec; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔬 高级数据统计与正态分布分析")

# --- 2. 侧边栏：数据输入模块 ---
with st.sidebar:
    st.header("📥 数据导入")
    input_method = st.radio("选择输入方式", ["文件上传 (Excel/CSV)", "直接粘贴数据"])
    
    raw_df = None
    if input_method == "文件上传 (Excel/CSV)":
        uploaded_file = st.file_uploader("拖拽文件至此", type=["csv", "xlsx"])
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)
    else:
        data_text = st.text_area("在下方粘贴数据 (支持从 Excel 复制列，每行一个数字)", height=200)
        if data_text:
            # 处理粘贴的数据，尝试读取为单列
            try:
                raw_df = pd.read_csv(io.StringIO(data_text), header=None, names=["粘贴数据"])
            except:
                st.error("数据格式错误")

    if raw_df is not None:
        all_cols = raw_df.columns.tolist()
        target_col = st.selectbox("🎯 选择分析列", all_cols)
        
        # 数据清洗
        clean_series = pd.to_numeric(raw_df[target_col], errors='coerce').dropna()
        
        if len(clean_series) > 1:
            st.success(f"有效样本量: {len(clean_series)}")
            st.markdown("---")
            st.header("🎛️ 范围与区间控制")
            
            # 定义全局边界
            d_min, d_max = float(clean_series.min()), float(clean_series.max())
            
            # 指定分析范围 (用于极差和占比分析)
            st.subheader("指定分析范围")
            analysis_range = st.slider(
                "滑动选择感兴趣的数值区间",
                min_value=d_min, max_value=d_max,
                value=(d_min, d_max), step=(d_max-d_min)/100
            )
            
            # 绘图组距
            bin_width = st.number_input("设置绘图组距 (Bin Width)", value=(d_max-d_min)/15, step=0.1)
        else:
            st.warning("数据不足，无法分析")
            st.stop()
    else:
        st.info("请先导入数据以开始分析")
        st.stop()

# --- 3. 核心计算逻辑 ---
# 1. 全局数据统计
full_mean = clean_series.mean()
full_std = clean_series.std()

# 2. 指定范围数据切片
mask = (clean_series >= analysis_range[0]) & (clean_series <= analysis_range[1])
subset = clean_series[mask]

# 3. 指定范围指标计算
if not subset.empty:
    sub_range = subset.max() - subset.min()  # 极差
    sub_count = len(subset)                  # 范围内样本量
    sub_ratio = (sub_count / len(clean_series)) * 100  # 占比
else:
    sub_range = sub_count = sub_ratio = 0

# --- 4. 主界面展示 ---
t1, t2, t3 = st.tabs(["📊 可视化大屏", "🔍 范围分析报告", "📋 原始数据清洗"])

with t1:
    # 绘制 Plotly 图表
    fig = go.Figure()

    # 直方图
    bins = np.arange(d_min, d_max + bin_width, bin_width)
    counts, edges = np.histogram(clean_series, bins=bins)
    centers = edges[:-1] + bin_width/2
    probs = counts / len(clean_series)

    fig.add_trace(go.Bar(
        x=centers, y=probs, width=bin_width*0.9,
        name="分布占比", marker_color='#34495e', opacity=0.7,
        text=[f"{p*100:.1f}%" for p in probs], textposition='outside'
    ))

    # 正态曲线
    x_line = np.linspace(d_min, d_max, 200)
    y_line = stats.norm.pdf(x_line, full_mean, full_std) * bin_width
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name="理论正态", line=dict(color='#e74c3c', width=3)))

    # 标记指定范围阴影
    fig.add_vrect(
        x0=analysis_range[0], x1=analysis_range[1],
        fillcolor="green", opacity=0.1, line_width=0,
        annotation_text="分析目标范围", annotation_position="top left"
    )

    fig.update_layout(
        template="simple_white", height=550,
        xaxis_title=f"数值 ({target_col})", yaxis_title="出现概率",
        hovermode="x unified", legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

with t2:
    st.subheader(f"🎯 范围分析结果: {analysis_range[0]:.2f} 至 {analysis_range[1]:.2f}")
    
    # 指标卡片
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("范围内样本量", f"{sub_count}")
    m2.metric("数量占比", f"{sub_ratio:.2f}%")
    m3.metric("范围内极差 (Range)", f"{sub_range:.4f}")
    m4.metric("范围内均值", f"{subset.mean():.4f}" if not subset.empty else "N/A")

    st.markdown("---")
    
    # 统计详情表格
    c1, c2 = st.columns(2)
    with c1:
        st.write("**全局统计摘要**")
        st.table(clean_series.describe())
    with c2:
        st.write("**正态性参考**")
        is_normal = stats.shapiro(clean_series)[1] > 0.05
        st.info(f"Shapiro-Wilk 检验结果: {'接近正态分布' if is_normal else '偏离正态分布'}")
        st.write(f"偏度: {clean_series.skew():.4f}")
        st.write(f"峰度: {clean_series.kurt():.4f}")

with t3:
    st.dataframe(raw_df[[target_col]].assign(是否有效=pd.to_numeric(raw_df[target_col], errors='coerce').notnull()), use_container_width=True)
