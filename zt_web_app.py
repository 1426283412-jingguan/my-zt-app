import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io
import datetime

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="数据专家 V3.0", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stMetric { border-top: 3px solid #3498db; background-color: #f8f9fa; padding: 10px; border-radius: 5px; }
    .report-area { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：多源数据导入与编辑 ---
with st.sidebar:
    st.title("🚀 控制中心")
    mode = st.toggle("模式：正态分布 (OFF) / 趋势回归 (ON)", value=True)
    
    st.divider()
    st.subheader("📁 数据录入")
    upload = st.file_uploader("上传 Excel/CSV", type=["csv", "xlsx"])
    paste = st.text_area("或者粘贴数据 (含表头)", height=100, placeholder="列1\t列2\t列3...")

    # 解析逻辑
    df_raw = pd.DataFrame()
    if upload:
        df_raw = pd.read_csv(upload) if upload.name.endswith('.csv') else pd.read_excel(upload)
    elif paste:
        df_raw = pd.read_csv(io.StringIO(paste), sep='\t' if '\t' in paste else ',')
    
    if df_raw.empty:
        # 默认多列演示数据
        df_raw = pd.DataFrame({
            "时间(s)": np.arange(1, 11),
            "压力(Mpa)": [10.2, 10.5, 10.8, 11.2, 11.5, 12.1, 12.4, 12.8, 13.2, 13.8],
            "温度(℃)": [25.1, 25.3, 25.6, 26.0, 26.2, 26.8, 27.1, 27.5, 27.9, 28.5]
        })
        st.info("💡 演示数据已加载")

    st.subheader("📝 在线数据编辑")
    df_edited = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True)

# --- 3. 核心统计逻辑 ---

report_txt = ""

if not mode: # --- 正态分布模式 ---
    st.title("📊 正态分布与局部区间分析")
    
    target_col = st.sidebar.selectbox("选择分析目标列", df_edited.columns)
    data = pd.to_numeric(df_edited[target_col], errors='coerce').dropna()
    
    if not data.empty:
        # 数值范围精确输入
        st.sidebar.subheader("📐 数值边界输入")
        c1, c2 = st.sidebar.columns(2)
        xmin = c1.number_input("起点值", value=float(data.min()))
        xmax = c2.number_input("终点值", value=float(data.max()))
        
        conf = st.sidebar.slider("置信水平 (%)", 0.0, 100.0, 95.0) / 100.0
        bw = st.sidebar.number_input("组距 (Bin)", value=(xmax-xmin)/15 if xmax!=xmin else 1.0)

        # 过滤数据
        sub = data[(data >= xmin) & (data <= xmax)]
        
        if not sub.empty:
            mean, std, rge = sub.mean(), sub.std(), sub.max() - sub.min()
            ci = stats.t.interval(conf, len(sub)-1, loc=mean, scale=stats.sem(sub)) if 0 < conf < 1 else (mean, mean)

            # 布局
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("局部样本量", len(sub))
            m2.metric("局部均值", f"{mean:.4f}")
            m3.metric("局部极差", f"{rge:.4f}")
            m4.metric("占比", f"{(len(sub)/len(data))*100:.1f}%")

            # 绘图
            fig = go.Figure()
            edges = np.arange(xmin, xmax + bw, bw)
            counts, _ = np.histogram(sub, bins=edges)
            fig.add_trace(go.Bar(x=edges[:-1]+bw/2, y=counts/len(sub), name="频率占比", marker_color='#2c3e50'))
            xl = np.linspace(xmin, xmax, 200)
            yl = stats.norm.pdf(xl, mean, std) * bw
            fig.add_trace(go.Scatter(x=xl, y=yl, mode='lines', name="拟合曲线", line=dict(color='red', width=3)))
            
            if 0 < conf < 1:
                fig.add_vrect(x0=max(ci[0], xmin), x1=min(ci[1], xmax), fillcolor="rgba(46, 204, 113, 0.2)", line_width=0)
            
            fig.update_layout(template="simple_white", height=500, xaxis_range=[xmin, xmax], title=f"{target_col} 局部分布")
            st.plotly_chart(fig, use_container_width=True)

            report_txt = f"正态分布分析报告\n生成时间: {datetime.datetime.now()}\n列名: {target_col}\n范围: {xmin} ~ {xmax}\n样本数: {len(sub)}\n均值: {mean:.6f}\n极差: {rge:.6f}\n置信区间: {ci}"

else: # --- 趋势回归模式 (多列选择) ---
    st.title("📈 多列趋势回归分析")
    
    # 动态坐标轴选择
    st.sidebar.subheader("🎯 坐标轴映射")
    sel_x = st.sidebar.selectbox("选择 X 轴 (自变量)", df_edited.columns, index=0)
    sel_y = st.sidebar.selectbox("选择 Y 轴 (因变量)", df_edited.columns, index=min(1, len(df_edited.columns)-1))
    
    # 清洗选定的两列
    reg_data = df_edited[[sel_x, sel_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(reg_data) >= 2:
        # 数值坐标范围手动输入
        st.sidebar.subheader("📐 坐标轴微调")
        cx1, cx2 = st.sidebar.columns(2)
        xmin = cx1.number_input("X 起点", value=float(reg_data[sel_x].min()))
        xmax = cx2.number_input("X 终点", value=float(reg_data[sel_x].max()))
        cy1, cy2 = st.sidebar.columns(2)
        ymin = cy1.number_input("Y 起点", value=float(reg_data[sel_y].min()))
        ymax = cy2.number_input("Y 终点", value=float(reg_data[sel_y].max()))

        # 范围过滤
        f_df = reg_data[(reg_data[sel_x]>=xmin) & (reg_data[sel_x]<=xmax) & (reg_data[sel_y]>=ymin) & (reg_data[sel_y]<=ymax)]
        
        if not f_df.empty:
            slope, intercept, r_v, p_v, std_e = stats.linregress(f_df[sel_x], f_df[sel_y])
            r_sq = r_v**2

            # 指标卡
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("判定系数 $R^2$", f"{r_sq:.4f}")
            k2.metric("相关系数 $r$", f"{r_v:.4f}")
            k3.metric("拟合斜率", f"{slope:.4f}")
            k4.metric("显著性 P", f"{p_v:.4e}")

            # 绘图
            fig_reg = go.Figure()
            fig_reg.add_trace(go.Scatter(x=f_df[sel_x], y=f_df[sel_y], mode='lines+markers', name=f"原始数据 ({sel_y})", line=dict(color='#3498db')))
            rx = np.array([xmin, xmax])
            fig_reg.add_trace(go.Scatter(x=rx, y=slope*rx+intercept, name="回归拟合线", line=dict(dash='dash', color='red')))
            
            fig_reg.update_layout(template="simple_white", height=500, xaxis_title=sel_x, yaxis_title=sel_y, xaxis_range=[xmin, xmax], yaxis_range=[ymin, ymax])
            st.plotly_chart(fig_reg, use_container_width=True)
            st.success(f"拟合方程: $y = {slope:.4f}x + {intercept:.4f}$")

            report_txt = f"回归分析报告\n生成时间: {datetime.datetime.now()}\nX轴列: {sel_x}\nY轴列: {sel_y}\nR^2: {r_sq:.6f}\n相关系数: {r_v:.6f}\n拟合方程: Y = {slope:.4f}X + {intercept:.4f}"
        else:
            st.error("此数值区间内无有效点")

# --- 4. 导出中心 ---
st.divider()
st.subheader("💾 导出与报告生成")
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button("📑 下载分析报告 (TXT)", report_txt, f"Report_{datetime.datetime.now().strftime('%m%d%H%M')}.txt", "text/plain", use_container_width=True)

with d2:
    if 'fig' in locals() or 'fig_reg' in locals():
        current_fig = fig if not mode else fig_reg
        html_buf = io.StringIO()
        current_fig.write_html(html_buf, include_plotlyjs='cdn')
        st.download_button("🖼️ 下载交互式高清图表 (HTML)", html_buf.getvalue(), "Chart.html", "text/html", use_container_width=True)

with d3:
    st.download_button("📊 下载编辑后的数据 (CSV)", df_edited.to_csv(index=False).encode('utf-8'), "Clean_Data.csv", "text/csv", use_container_width=True)

if report_txt:
    with st.expander("📄 实时报告预览"):
        st.code(report_txt)
