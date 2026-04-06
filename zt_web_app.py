import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io
import datetime

# --- 1. 页面级整体配置 ---
st.set_page_config(page_title="高级数据统计实验室 V5.0", layout="wide", page_icon="📈")

# 自定义 UI 样式美化
st.markdown("""
    <style>
    .stMetric { border-left: 5px solid #3498db; background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .plot-container { border: 1px solid #f0f2f6; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：数据导入与导航 ---
with st.sidebar:
    st.title("🔬 实验控制台")
    
    # 【需求】正态分析与趋势分析图标并列可选
    analysis_type = st.radio(
        "选择分析引擎：",
        ["📊 正态分布分析", "📈 趋势回归分析"],
        help="切换不同的统计模式"
    )
    
    st.divider()
    st.subheader("📥 数据录入")
    up_file = st.file_uploader("1. 上传 Excel/CSV 文件", type=["csv", "xlsx"])
    ps_text = st.text_area("2. 或者：直接在此粘贴 Excel 数据列", height=120, placeholder="序号\t数值\n1\t10.5...")

    # 数据解析逻辑
    df_input = pd.DataFrame()
    if up_file:
        df_input = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
    elif ps_text:
        # 支持 Tab 分隔符（Excel 复制）或逗号
        df_input = pd.read_csv(io.StringIO(ps_text), sep='\t' if '\t' in ps_text else ',')
    
    # 修正后的演示数据生成逻辑
    if df_input.empty:
        np.random.seed(42)
        df_input = pd.DataFrame({
            "序号": range(1, 101),
            "压力检测值(Mpa)": np.random.normal(50, 5, 100).round(2),
            "温度趋势值(℃)": np.linspace(20, 30, 100) + np.random.normal(0, 1, 100)
        })
        st.info("💡 当前使用演示数据，您可以上传或粘贴自己的数据。")

    st.subheader("📝 在线数据编辑")
    # 【需求】数据可以直接修改、编辑
    df_active = st.data_editor(df_input, num_rows="dynamic", use_container_width=True, key="editor_v5")

# 初始化全局导出变量
report_txt = ""
final_fig = None

# --- 3. 核心分析模块 ---

# --- A. 正态分布分析模块 ---
if analysis_type == "📊 正态分布分析":
    st.title("正态分布与区间占比统计")
    
    target_col = st.sidebar.selectbox("选择目标分析列", df_active.columns)
    raw_data = pd.to_numeric(df_active[target_col], errors='coerce').dropna()
    
    if not raw_data.empty:
        st.sidebar.subheader("📐 数值范围精确控制")
        c1, c2 = st.sidebar.columns(2)
        # 【需求】数值范围可以直接输入
        x_min = c1.number_input("起点数值", value=float(raw_data.min()))
        x_max = c2.number_input("终点数值", value=float(raw_data.max()))
        
        bw = st.sidebar.number_input("设置组距 (Bin Width)", value=(x_max-x_min)/15 if x_max != x_min else 1.0, step=0.1)
        # 【需求】置信区间 0-100%
        conf_level = st.sidebar.slider("置信水平 (%)", 0.0, 100.0, 95.0) / 100.0

        # 指定范围过滤
        subset = raw_data[(raw_data >= x_min) & (raw_data <= x_max)]
        
        if not subset.empty:
            mean_v, std_v, range_v = subset.mean(), subset.std(), subset.max() - subset.min()
            ci = stats.t.interval(conf_level, len(subset)-1, loc=mean_v, scale=stats.sem(subset)) if 0 < conf_level < 1 else (mean_v, mean_v)

            # 指标卡
            cols = st.columns(4)
            cols[0].metric("局部样本量", len(subset))
            cols[1].metric("局部均值", f"{mean_v:.4f}")
            cols[2].metric("指定范围极差", f"{range_v:.4f}")
            cols[3].metric("数据覆盖率", f"{(len(subset)/len(raw_data))*100:.1f}%")

            # 绘图：包含柱状图占比标注
            final_fig = go.Figure()
            bin_edges = np.arange(x_min, x_max + bw, bw)
            counts, _ = np.histogram(subset, bins=bin_edges)
            proportions = counts / len(subset) # 局部占比
            
            # 【需求】柱状图上方标注各区间占比
            final_fig.add_trace(go.Bar(
                x=bin_edges[:-1] + bw/2, y=proportions,
                text=[f"{(p*100):.1f}%" for p in proportions],
                textposition='outside', name="频率占比", marker_color='#2c3e50'
            ))
            
            # 拟合曲线
            x_line = np.linspace(x_min, x_max, 200)
            y_line = stats.norm.pdf(x_line, mean_v, std_v) * bw
            final_fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name="正态拟合", line=dict(color='red', width=3)))
            
            final_fig.update_layout(template="simple_white", height=500, xaxis_range=[x_min, x_max], xaxis_title=target_col, yaxis_title="占比")
            st.plotly_chart(final_fig, use_container_width=True)

            report_txt = f"【正态分布分析报告】\n时间: {datetime.datetime.now()}\n列名: {target_col}\n指定范围: {x_min} ~ {x_max}\n样本数: {len(subset)}\n均值: {mean_v:.6f}\n极差: {range_v:.6f}\n置信区间: {ci}"
        else:
            st.warning("所选范围内无数据。")

# --- B. 趋势回归分析模块 ---
else:
    st.title("趋势折线图与线性回归分析")
    
    # 【需求】可以选择某一列作为横坐标，某一列作为纵坐标
    st.sidebar.subheader("🎯 坐标轴列映射")
    col_x = st.sidebar.selectbox("选择 X 轴 (横坐标)", df_active.columns, index=0)
    col_y = st.sidebar.selectbox("选择 Y 轴 (纵坐标)", df_active.columns, index=min(1, len(df_active.columns)-1))
    
    reg_data = df_active[[col_x, col_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(reg_data) >= 2:
        st.sidebar.subheader("📐 坐标轴范围输入")
        cx1, cx2 = st.sidebar.columns(2)
        xmin_r = cx1.number_input("X 轴起", value=float(reg_data[col_x].min()))
        xmax_r = cx2.number_input("X 轴止", value=float(reg_data[col_x].max()))
        
        # 过滤数据
        f_df = reg_data[(reg_data[col_x] >= xmin_r) & (reg_data[col_x] <= xmax_r)]
        
        if not f_df.empty:
            # 回归计算
            slope, intercept, r_v, p_v, std_e = stats.linregress(f_df[col_x], f_df[col_y])
            # 【需求】衡量参数 R2 等
            r_sq = r_v**2
            
            m_cols = st.columns(4)
            m_cols[0].metric("判定系数 $R^2$", f"{r_sq:.4f}")
            m_cols[1].metric("相关系数 $r$", f"{r_v:.4f}")
            m_cols[2].metric("回归斜率", f"{slope:.4f}")
            m_cols[3].metric("显著性 P", f"{p_v:.4e}")

            # 绘图
            final_fig = go.Figure()
            final_fig.add_trace(go.Scatter(x=f_df[col_x], y=f_df[col_y], mode='lines+markers', name="实测折线"))
            rx = np.array([xmin_r, xmax_r])
            final_fig.add_trace(go.Scatter(x=rx, y=slope*rx+intercept, name="回归趋势线", line=dict(dash='dash', color='red')))
            
            final_fig.update_layout(template="simple_white", height=500, xaxis_title=col_x, yaxis_title=col_y, xaxis_range=[xmin_r, xmax_r])
            st.plotly_chart(final_fig, use_container_width=True)
            st.success(f"线性拟合方程: $y = {slope:.4f}x + {intercept:.4f}$")

            report_txt = f"【趋势回归分析报告】\n时间: {datetime.datetime.now()}\nX轴: {col_x}\nY轴: {col_y}\n判定系数 R2: {r_sq:.6f}\n拟合方程: Y = {slope:.4f}X + {intercept:.4f}"
        else:
            st.error("此数值范围内无有效点")

# --- 4. 导出中心 ---
st.divider()
st.subheader("📥 报告与图表导出")
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button("📑 下载分析报告 (TXT)", report_txt, f"Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt", "text/plain", use_container_width=True)

with d2:
    if final_fig is not None:
        html_buf = io.StringIO()
        final_fig.write_html(html_buf, include_plotlyjs='cdn')
        st.download_button("🖼️ 下载交互式高清图 (HTML)", html_buf.getvalue(), "Scientific_Chart.html", "text/html", use_container_width=True)

with d3:
    st.download_button("📊 下载已编辑数据 (CSV)", df_active.to_csv(index=False).encode('utf-8'), "Export_Data.csv", "text/csv", use_container_width=True)

if report_txt:
    with st.expander("📄 报告内容实时预览"):
        st.code(report_txt)
