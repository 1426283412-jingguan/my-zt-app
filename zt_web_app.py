import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io

# --- 1. 页面配置与 CSS ---
st.set_page_config(page_title="局部范围正态分析", layout="wide")
st.markdown("<style>.main {background-color: #fcfcfc;}</style>", unsafe_allow_html=True)

# --- 2. 侧边栏：数据导入 ---
with st.sidebar:
    st.header("📥 数据输入")
    input_method = st.radio("方式", ["文件上传", "直接粘贴"])
    
    raw_df = None
    if input_method == "文件上传":
        uploaded_file = st.file_uploader("拖拽文件", type=["csv", "xlsx"])
        if uploaded_file:
            raw_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    else:
        data_text = st.text_area("粘贴 Excel 数据列", height=150)
        if data_text:
            raw_df = pd.read_csv(io.StringIO(data_text), header=None, names=["数据"])

    if raw_df is not None:
        target_col = st.selectbox("🎯 目标列", raw_df.columns.tolist())
        # 预清洗
        clean_series = pd.to_numeric(raw_df[target_col], errors='coerce').dropna()
        
        if len(clean_series) > 1:
            st.markdown("---")
            st.header("🔍 局部范围选择")
            d_min, d_max = float(clean_series.min()), float(clean_series.max())
            
            # 用户选择显示的范围
            analysis_range = st.slider("选择展示区间", d_min, d_max, (d_min, d_max))
            
            # 置信区间开关
            show_ci = st.checkbox("显示均值置信区间", value=True)
            conf_level = st.select_slider("置信水平", options=[90, 95, 99], value=95) / 100.0
            
            # 组距微调
            bin_width = st.number_input("局部组距", value=(analysis_range[1]-analysis_range[0])/15 if analysis_range[1]!=analysis_range[0] else 1.0)
        else:
            st.stop()
    else:
        st.stop()

# --- 3. 局部数据处理逻辑 ---
# 仅提取选定范围内的数据
subset = clean_series[(clean_series >= analysis_range[0]) & (clean_series <= analysis_range[1])]
n_subset = len(subset)
n_total = len(clean_series)

# 计算统计量
if n_subset > 0:
    sub_mean = subset.mean()
    sub_std = subset.std(ddof=1) if n_subset > 1 else 0
    sub_range = subset.max() - subset.min()
    
    # 置信区间 (基于全局数据计算更严谨，或基于局部计算，此处演示基于局部)
    sem = stats.sem(subset) if n_subset > 1 else 0
    ci_bounds = stats.t.interval(conf_level, df=n_subset-1, loc=sub_mean, scale=sem) if n_subset > 1 else (sub_mean, sub_mean)
else:
    st.error("当前选定范围内无有效数据，请调整滑块。")
    st.stop()

# --- 4. 绘图与报告 ---
tab1, tab2 = st.tabs(["🎯 局部分布图", "📋 范围统计分析"])

with tab1:
    fig = go.Figure()

    # A. 局部直方图：仅使用 subset
    # 重新计算 bins 以适配局部范围
    local_bins = np.arange(analysis_range[0], analysis_range[1] + bin_width, bin_width)
    counts, edges = np.histogram(subset, bins=local_bins)
    
    fig.add_trace(go.Bar(
        x=edges[:-1] + bin_width/2, 
        y=counts / n_subset, # 展示在局部样本中的占比
        width=bin_width * 0.8,
        name="局部频数占比",
        marker_color='#2c3e50',
        text=[f"{(c/n_subset)*100:.1f}%" for c in counts],
        textposition='outside'
    ))

    # B. 局部正态曲线：仅在选定范围内绘制
    x_line = np.linspace(analysis_range[0], analysis_range[1], 200)
    y_line = stats.norm.pdf(x_line, sub_mean, sub_std) * bin_width if sub_std > 0 else np.zeros_like(x_line)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        name="局部理论正态", 
        line=dict(color='#e74c3c', width=3)
    ))

    # C. 置信区间阴影
    if show_ci and n_subset > 1:
        fig.add_vrect(
            x0=max(ci_bounds[0], analysis_range
