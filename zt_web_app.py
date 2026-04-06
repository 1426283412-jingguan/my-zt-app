import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io
import datetime

# --- 1. 页面级整体配置 ---
st.set_page_config(page_title="数据分析工作站", layout="wide", page_icon="🧪")

# 自定义 UI 样式
st.markdown("""
    <style>
    .stMetric { border-left: 5px solid #3498db; background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：导航与数据导入 ---
with st.sidebar:
    st.title("🛠 控制中心")
    
    # 按钮并列可选
    analysis_type = st.radio("🎯 选择分析模块", ["正态分布分析", "趋势回归分析"])
    
    st.divider()
    st.subheader("📥 数据录入")
    up_file = st.file_uploader("1. 上传 Excel/CSV 文件", type=["csv", "xlsx"])
    ps_text = st.text_area("2. 或者粘贴数据", height=100, placeholder="序号\t测量值...")

    # 数据解析
    df_raw = pd.DataFrame()
    if up_file:
        df_raw = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
    elif ps_text:
        df_raw = pd.read_csv(io.StringIO(ps_text), sep='\t' if '\t' in ps_text else ',')
    
    if df_raw.empty:
        df_raw = pd.DataFrame({
            "实验批次": range(1, 101),
            "数值A": np.random.normal(50, 5, 100).round(2),
            "数值B": np.random.linear_model = np.linspace(10, 20, 100) + np.random.normal(0, 1, 100)
        })
        st.info("💡 已加载演示数据")

    st.subheader("📝 在线数据编辑")
    df_edited = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True)

# 初始化全局变量
report_content = ""
current_fig = None

# --- 3. 分析逻辑 ---

if analysis_type == "正态分布分析":
    st.title("📊 正态分布分析")
    
    # 这里统一变量名为 target_col
    target_col = st.sidebar.selectbox("选择目标分析列", df_edited.columns)
    valid_data = pd.to_numeric(df_edited[target_col], errors='coerce').dropna()
    
    if not valid_data.empty:
        st.sidebar.subheader("📐 范围与参数")
        c1, c2 = st.sidebar.columns(2)
        xmin = c1.number_input("起点值", value=float(valid_data.min()))
        xmax = c2.number_input("终点值", value=float(valid_data.max()))
        
        bw = st.sidebar.number_input("组距 (Bin)", value=(xmax-xmin)/15 if xmax!=xmin else 1.0)
        conf = st.sidebar.slider("置信水平 (%)", 0.0, 100.0, 95.0) / 100.0

        # 数据切片
        sub = valid_data[(valid_data >= xmin) & (valid_data <= xmax)]
        
        if not sub.empty:
            mean_v, std_v, range_v = sub.mean(), sub.std(), sub.max() - sub.min()
            ci = stats.t.interval(conf, len(sub)-1, loc=mean_v, scale=stats.sem(sub)) if 0 < conf < 1 else (mean_v, mean_v)

            # 指标展示
            m = st.columns(4)
            m[0].metric("局部样本量", len(sub))
            m[1].metric("范围均值", f"{mean_v:.4f}")
            m[2].metric("范围极差", f"{range_v:.4f}")
            m[3].metric("占比", f"{(len(sub)/len(valid_data))*100:.1f}%")

            # 绘图
            current_fig = go.Figure()
            bins = np.arange(xmin, xmax + bw, bw)
            counts, _ = np.histogram(sub, bins=bins)
            # 占比标注在柱子顶部
            current_fig.add_trace(go.Bar(
                x=bins[:-1]+bw/2, y=counts/len(sub), 
                text=[f"{(c/len(sub))*100:.1f}%" for c in counts],
                textposition='outside', name="频率占比", marker_color='#34495e'
            ))
            xl = np.linspace(xmin, xmax, 200)
            yl = stats.norm.pdf(xl, mean_v, std_v) * bw
            current_fig.add_trace(go.Scatter(x=xl, y=yl, mode='lines', name="正态曲线", line=dict(color='red', width=3)))

            current_fig.update_layout(template="simple_white", height=550, xaxis_range=[xmin, xmax])
            st.plotly_chart(current_fig, use_container_width=True)

            # 报告内容（修正变量名错误）
            report_content = f"分析报告 (正态分布)\n列名: {target_col}\n样本数: {len(sub)}\n均值: {mean_v:.4f}\n极差: {range_v:.4f}\n置信区间: {ci}"

else: # --- 趋势回归分析 ---
    st.title("📈 趋势折线与回归分析")
    
    col_x = st.sidebar.selectbox("选择 X 轴", df_edited.columns, index=0)
    col_y = st.sidebar.selectbox("选择 Y 轴", df_edited.columns, index=min(1, len(df_edited.columns)-1))
    
    reg_df = df_edited[[col_x, col_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(reg_df) >= 2:
        st.sidebar.subheader("📐 坐标轴控制")
        cx1, cx2 = st.sidebar.columns(2)
        xmin_r = cx1.number_input("X 起", value=float(reg_df[col_x].min()))
        xmax_r = cx2.number_input("X 止", value=float(reg_df[col_x].max()))
        
        f_reg = reg_df[(reg_df[col_x] >= xmin_r) & (reg_df[col_x] <= xmax_r)]
        
        if not f_reg.empty:
            slope, intercept, r_v, p_v, std_e = stats.linregress(f_reg[col_x], f_reg[col_y])
            
            k = st.columns(4)
            k[0].metric("判定系数 $R^2$", f"{r_v**2:.4f}")
            k[1].metric("相关系数 $r$", f"{r_v:.4f}")
            k[2].metric("斜率", f"{slope:.4f}")
            k[3].metric("显著性 P", f"{p_v:.4e}")

            current_fig = go.Figure()
            current_fig.add_trace(go.Scatter(x=f_reg[col_x], y=f_reg[col_y], mode='lines+markers', name="原始数据"))
            rx = np.array([xmin_r, xmax_r])
            current_fig.add_trace(go.Scatter(x=rx, y=slope*rx+intercept, name="回归线", line=dict(dash='dash', color='red')))
            
            current_fig.update_layout(template="simple_white", height=550, xaxis_title=col_x, yaxis_title=col_y)
            st.plotly_chart(current_fig, use_container_width=True)

            report_content = f"分析报告 (线性回归)\nX轴: {col_x}, Y轴: {col_y}\nR^2: {r_v**2:.4f}\n方程: Y = {slope:.4f}X + {intercept:.4f}"

# --- 4. 导出中心 ---
st.divider()
st.subheader("📥 导出结果")
d1, d2, d3 = st.columns(3)
with d1:
    st.download_button("📑 下载报告", report_content, "Report.txt")
with d2:
    if current_fig:
        html_bytes = current_fig.to_html(include_plotlyjs='cdn')
        st.download_button("🖼️ 下载交互图表", html_bytes, "Chart.html", "text/html")
with d3:
    st.download_button("📊 下载数据", df_edited.to_csv(index=False), "Data.csv")
