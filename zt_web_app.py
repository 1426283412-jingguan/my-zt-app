import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats

# 网页基本配置
st.set_page_config(page_title="高级正态分布分析系统", layout="wide")

st.title("📊 高级正态分布与数据分析工作站")
st.markdown("上传数据，自定义组距与坐标范围，实时生成带占比标签的精准图表。")

# --- 侧边栏：数据导入 ---
st.sidebar.header("1. 数据导入")
uploaded_file = st.sidebar.file_uploader("上传 Excel 或 CSV 文件", type=["csv", "xlsx"])

if uploaded_file:
    # 根据文件后缀读取数据
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # 获取数字列
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        column_name = st.sidebar.selectbox("选择要分析的数字列", numeric_cols)

        if column_name:
            # 提取数据并剔除空值
            data = df[column_name].dropna()

            if len(data) > 0:
                st.sidebar.markdown("---")
                st.sidebar.header("2. 图表与统计参数设置")
                
                # 获取数据的极值，用于默认设置
                data_min = float(data.min())
                data_max = float(data.max())
                
                # 组距设置
                default_bin_width = (data_max - data_min) / 10 if data_max != data_min else 1.0
                bin_width = st.sidebar.number_input("设置横坐标组距 (Bin Width)", min_value=0.0001, value=default_bin_width, step=0.1)
                
                # 横坐标范围设置
                col_min, col_max = st.sidebar.columns(2)
                x_min = col_min.number_input("横坐标起始值 (下限)", value=data_min)
                x_max = col_max.number_input("横坐标结束值 (上限)", value=data_max)
                
                # 置信区间设置
                conf_level = st.sidebar.slider("置信区间水平 (%)", 90, 99, 95) / 100.0
                
                # ==========================================
                # 数据统计与计算
                # ==========================================
                total_mean = data.mean()
                total_var = data.var()
                total_std = data.std()
                n_total = len(data)
                
                # 计算置信区间 (基于 t 分布)
                se = total_std / np.sqrt(n_total)
                ci_lower, ci_upper = stats.t.interval(conf_level, df=n_total-1, loc=total_mean, scale=se)
                
                # 计算选定范围内的数据均值
                filtered_data = data[(data >= x_min) & (data <= x_max)]
                filtered_mean = filtered_data.mean() if len(filtered_data) > 0 else np.nan
                
                # ==========================================
                # 绘图逻辑 (使用 Plotly Graph Objects)
                # ==========================================
                # 根据自定义的 min, max 和 bin_width 生成区间边界
                # 为了确保最后一个区间被包含，上限加上一个 bin_width
                bins = np.arange(x_min, x_max + bin_width, bin_width)
                
                # 统计每个区间内的数据量
                counts, bin_edges = np.histogram(data, bins=bins)
                
                # 计算每个区间的占比
                proportions = counts / n_total
                percentages = proportions * 100
                
                # 计算柱状图的中心点坐标
                bin_centers = bin_edges[:-1] + bin_width / 2
                
                fig = go.Figure()
                
                # 1. 绘制带有百分比标签的柱状图
                fig.add_trace(go.Bar(
                    x=bin_centers,
                    y=proportions,
                    width=bin_width * 0.95, # 柱子宽度稍微留缝隙，更美观
                    text=[f'{p:.1f}%' if p > 0 else '' for p in percentages], # 柱子顶部显示占比
                    textposition='outside',
                    name='实际数据分组占比',
                    marker_color='#636EFA'
                ))
                
                # 2. 绘制平滑的正态分布理论曲线
                x_curve = np.linspace(x_min, x_max, 500)
                # 计算理论概率密度并乘以组距，使其面积与柱状图比例对齐
                y_curve = stats.norm.pdf(x_curve, total_mean, total_std) * bin_width
                
                fig.add_trace(go.Scatter(
                    x=x_curve,
                    y=y_curve,
                    mode='lines',
                    name='理论正态分布曲线',
                    line=dict(color='#EF553B', width=3)
                ))
                
                # 优化图表布局
                fig.update_layout(
                    title=dict(text=f"<b>{column_name}</b> 的正态分布及占比分析图", font=dict(size=20)),
                    xaxis_title="数值 (自定义横坐标范围)",
                    yaxis_title="占比 (比例)",
                    bargap=0.05,
                    hovermode="x unified",
                    legend=dict(x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)')
                )
                
                # 在网页上展示图表
                st.plotly_chart(fig, use_container_width=True)
                
                # ==========================================
                # 展示核心统计指标
                # ==========================================
                st.markdown("### 📈 核心统计指标分析")
                
                # 第一排数据：均值对比
                c1, c2 = st.columns(2)
                c1.metric("所有数据的平均值 (Total Mean)", f"{total_mean:.4f}")
                if np.isnan(filtered_mean):
                    c2.metric(f"选定横坐标范围 [{x_min}, {x_max}] 内的均值", "该范围内无数据")
                else:
                    c2.metric(f"选定横坐标范围 [{x_min}, {x_max}] 内的均值", f"{filtered_mean:.4f}")
                
                # 第二排数据：离散程度与可靠性
                st.markdown("<br>", unsafe_allow_html=True) # 增加一些间距
                c3, c4, c5 = st.columns(3)
                c3.metric("方差 (Variance)", f"{total_var:.4f}")
                c4.metric("标准差 (Std Deviation)", f"{total_std:.4f}")
                c5.metric("有效数据量 (Count)", f"{n_total}")
                
                # 置信区间展示框
                st.success(f"**💡 {int(conf_level*100)}% 置信区间 (Confidence Interval):** 真实均值有 {int(conf_level*100)}% 的概率落在 **[{ci_lower:.4f},  {ci_upper:.4f}]** 之间。")

            else:
                st.warning("选中列中没有有效数字数据，请检查表格。")
    else:
        st.error("表格中没有发现数字列，请确认上传了正确的数据格式。")

else:
    # 欢迎页提示
    st.info("👈 请在左侧面板上传您的 Excel 或 CSV 数据文件以开始分析。")
