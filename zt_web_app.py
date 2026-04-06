import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io
import datetime

# --- 1. 页面级整体配置 ---
st.set_page_config(
    page_title="高级数据统计实验室 V4.0",
    layout="wide",
    page_icon="🧪"
)

# 自定义 UI 样式美化
st.markdown("""
    <style>
    .report-box { background-color: #fcfcfc; padding: 20px; border-radius: 12px; border: 1px solid #f0f2f6; }
    .stMetric { border-left: 5px solid #2c3e50; background-color: #ffffff; padding: 10px; border-radius: 8px; }
    div[data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：统一数据录入与导航 ---
with st.sidebar:
    st.title("🛠 控制中心")
    
    # 【需求 2 & 3】采用并列单选按钮，不再使用 On/Off
    st.subheader("🎯 选择分析模块")
    analysis_type = st.radio(
        "导航：",
        ["正态分布分析", "趋势回归分析"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.subheader("📥 数据录入引擎")
    up_file = st.file_uploader("1. 上传 Excel/CSV 文件", type=["csv", "xlsx"])
    ps_text = st.text_area("2. 或者粘贴数据 (含表头)", height=100, placeholder="序号\t测量值...")

    # 数据解析逻辑
    df_raw = pd.read_csv(io.StringIO(ps_text), sep='\t' if '\t' in ps_text else ',') if ps_text else pd.DataFrame()
    if up_file:
        df_raw = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
    
    if df_raw.empty:
        # 默认多列演示数据
        np.random.seed(42)
        df_raw = pd.DataFrame({
            "实验批次": range(1, 101),
            "温度(℃)": np.random.normal(25, 2, 100).round(2),
            "压力(Mpa)": np.linspace(10, 20, 100) + np.random.normal(0, 0.5, 100),
            "合格率": np.random.uniform(0.9, 1.0, 100).round(4)
        })
        st.info("💡 已加载演示数据，请导入您自己的数据。")

    st.subheader("📝 在线数据编辑器")
    # 可直接编辑、粘贴增加数据的表格
    df_edited = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True, key="main_editor")

# --- 初始化导出变量 ---
report_content = ""
current_fig = None

# =========================================
# --- 3. 分析模式 1：正态分布 (含占比标注) ---
# =========================================
if analysis_type == "正态分布分析":
    st.title("📊 正态分布深度统计与区间占比")
    
    target_col = st.sidebar.selectbox("选择目标分析列", df_edited.columns)
    valid_series = pd.to_numeric(df_edited[target_col], errors='coerce').dropna()
    
    if not valid_series.empty:
        st.sidebar.subheader("📐 数值边界输入 (精准极差分析)")
        # 【需求：数值输入框】
        c1, c2 = st.sidebar.columns(2)
        xmin_in = c1.number_input("起点值", value=float(valid_series.min()))
        xmax_in = c2.number_input("终点值", value=float(valid_series.max()))
        
        bw_in = st.sidebar.number_input("设置组距", value=(xmax_in-xmin_in)/15 if xmax_in != xmin_in else 1.0, step=0.1)
        # 【需求：置信区间 0-100】
        conf_in = st.sidebar.slider("置信水平 (%)", 0.0, 100.0, 95.0) / 100.0

        # 基于手动输入范围的数据切片
        f_subset = valid_series[(valid_series >= xmin_in) & (valid_series <= xmax_in)]
        
        if not f_subset.empty:
            # 统计计算
            mean_v, std_v = f_subset.mean(), f_subset.std()
            # 【需求：指定范围极差分析】
            range_v = f_subset.max() - f_subset.min()
            
            # 置信区间数学处理
            if 0 < conf_in < 1:
                ci_v = stats.t.interval(conf_in, len(f_subset)-1, loc=mean_v, scale=stats.sem(f_subset))
            elif conf_in <= 0:
                ci_v = (mean_v, mean_v)
            else: ci_v = (float('-inf'), float('inf'))

            # 指标展示
            m_cols = st.columns(4)
            m_cols[0].metric("局部样本数", len(f_subset))
            m_cols[1].metric("范围均值", f"{mean_v:.4f}")
            m_cols[2].metric("范围极差", f"{range_v:.4f}")
            m_cols[3].metric("范围标准差", f"{std_v:.4f}")

            # 【需求 1】直方图与占比分析（柱状图顶部标注百分比）
            bin_edges = np.arange(xmin_in, xmax_in + bw_in, bw_in)
            # 计算局部频数
            counts, _ = np.histogram(f_subset, bins=bin_edges)
            # 计算局部占比
            proportions = counts / len(f_subset)
            
            current_fig = go.Figure()
            
            # 1. 频率直方图柱状图 trace
            current_fig.add_trace(go.Bar(
                x=bin_edges[:-1] + bw_in/2, 
                y=proportions, 
                name="频率占比柱状图",
                marker=dict(color='#34495e', opacity=0.8),
                # 【关键核心：在柱状图顶部添加 text 文本并设置 textposition】
                text=[f"{(p * 100):.1f}%" if p > 0 else "" for p in proportions],
                textposition='outside', # 标注在柱体上方
                textfont=dict(color='#2c3e50', size=11),
                error_y=None # 清除错误线
            ))
            
            # 2. 正态分布拟合曲线 trace
            xl_curve = np.linspace(xmin_in, xmax_in, 200)
            yl_curve = stats.norm.pdf(xl_curve, mean_v, std_v) * bw_in # 缩放 PDF 以匹配占比
            current_fig.add_trace(go.Scatter(x=xl_curve, y=yl_curve, mode='lines', name="局部拟合曲线", line=dict(color='#e74c3c', width=3)))
            
            # 3. 置信区间阴影
            if 0 < conf_in < 1:
                current_fig.add_vrect(x0=max(ci_v[0], xmin_in), x1=min(ci_v[1], xmax_in), fillcolor="rgba(46, 204, 113, 0.15)", line_width=0)
            
            # 图表布局
            current_fig.update_layout(
                template="simple_white", height=550, title=f"选定区间局部分布与占比详图 ({target_col})",
                xaxis=dict(title=target_col, range=[xmin_in, xmax_in]),
                yaxis=dict(title="局部出现频率占比"),
                margin=dict(t=80), hovermode="x unified"
            )
            st.plotly_chart(current_fig, use_container_width=True)

            # 生成文本报告
            report_content = f"""正态分布深度分析报告
====================================
分析时间: {datetime.datetime.now()}
目标列: {col_target}
用户指定范围: {xmin_in} ~ {xmax_in}

统计结果 (基于选定范围数据):
- 范围样本数: {len(f_subset)}
- 范围均值: {mean_v:.6f}
- 范围极差 (Range): {range_v:.6f}
- 范围标准差: {std_v:.6f}
- 用户置信水平: {conf_in*100}%
- 均值置信区间: [{ci_v[0]:.6f}, {ci_v[1]:.6f}]

(报告由高级统计实验室重计算生成)
"""
        else:
            st.warning("您指定的数值范围内没有有效的数据点。")

# ========================================
# --- 4. 分析模式 2：趋势回归 (横纵选择) ---
# ========================================
else:
    st.title("📈 趋势折线与多列线性回归")
    
    # 【需求：可以选择某一列作为横坐标】
    st.sidebar.subheader("🎯 坐标轴列映射")
    col_x = st.sidebar.selectbox("选择 X 轴 (自变量)", df_edited.columns, index=0)
    col_y = st.sidebar.selectbox("选择 Y 轴 (因变量)", df_edited.columns, index=min(1, len(df_edited.columns)-1))
    
    # 清洗选定的两列数据
    reg_clean = df_edited[[col_x, col_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(reg_clean) >= 2:
        # 【需求：数值范围可以选择输入】
        st.sidebar.subheader("📐 坐标轴微调输入")
        cx1, cx2 = st.sidebar.columns(2)
        xmin_t = cx1.number_input("X 起", value=float(reg_clean[col_x].min()))
        xmax_t = cx2.number_input("X 止", value=float(reg_clean[col_x].max()))
        cy1, cy2 = st.sidebar.columns(2)
        ymin_t = cy1.number_input("Y 起", value=float(reg_clean[col_y].min()))
        ymax_t = cy2.number_input("Y 止", value=float(reg_clean[col_y].max()))

        # 数据过滤
        f_reg = reg_clean[(reg_data[sel_x]>=xmin_t) & (reg_data[sel_x]<=xmax_t) & (reg_data[sel_y]>=ymin_t) & (reg_data[sel_y]<=ymax_t)]
        
        if not f_reg.empty:
            # 统计计算
            slope, intercept, r_v, p_v, std_e = stats.linregress(f_df[sel_x], f_df[sel_y])
            # 【需求：衡量的参数值比如 R2】
            r_sq = r_v**2
            
            # 布局
            kcols = st.columns(4)
            kcols[0].metric("判定系数 $R^2$", f"{r_sq:.4f}")
            kcols[1].metric("相关系数 $r$", f"{r_v:.4f}")
            kcols[2].metric("斜率", f"{slope:.4f}")
            kcols[3].metric("显著性 P", f"{p_v:.4e}")

            # 绘图
            current_fig = go.Figure()
            # 折线数据
            current_fig.add_trace(go.Scatter(x=f_df[sel_x], y=f_df[sel_y], mode='lines+markers', name="实测趋势"))
            # 回归拟合线
            reg_xl = np.array([xmin_t, xmax_t])
            reg_yl = slope * reg_xl + intercept
            current_fig.add_trace(go.Scatter(x=reg_xl, y=reg_yl, mode='lines', name="回归拟合线", line=dict(dash='dash', color='red')))
            
            current_fig.update_layout(template="simple_white", height=500, xaxis_title=sel_x, yaxis_title=sel_y, xaxis_range=[xmin_t, xmax_t], yaxis_range=[ymin_t, ymax_t], legend=dict(orientation="h", y=1.1))
            st.plotly_chart(current_fig, use_container_width=True)
            st.success(f"📈 线性拟合方程: $y = {slope:.4f}x + {intercept:.4f}$")

            # 生成报告
            report_content = f"""回归分析报告
====================================
生成时间: {datetime.datetime.now()}
变量关系: {sel_x} (X轴) vs {sel_y} (Y轴)
数值局部范围: X[{xmin_t}, {xmax_t}], Y[{ymin_t}, {ymax_t}]

统计结果 (基于选定局部数据):
- 数据点数: {len(f_df)}
- 判定系数 R^2: {r_sq:.6f}
- 相关系数 r: {r_v:.6f}
- 斜率 (Slope): {slope:.6f}
- 截距 (Intercept): {intercept:.6f}
- P-Value (显著性): {p_v:.4e}
- 拟合公式: Y = {slope:.4f} * X + {intercept:.4f}
"""
        else:
            st.error("您选定的数值局部范围内没有有效坐标点。")
    else:
        st.warning("数据量不足，无法生成回归拟合。需要至少两组 X-Y 坐标数值点。")

# ==============================
# --- 5. 统一数据导出工具 ---
# ==============================
st.divider()
st.subheader("💾 分析报告与结果导出")
dcols = st.columns(3)

with dcols[0]:
    st.download_button("📑 下载分析报告 (TXT)", report_content, f"Lab_Report_{datetime.datetime.now().strftime('%m%d_%H%M')}.txt", "text/plain", use_container_width=True)

with dcols[1]:
    if current_fig is not None:
        html_buf = io.StringIO()
        current_fig.write_html(html_buf, include_plotlyjs='cdn')
        st.download_button("🖼️ 下载交互式图表 (HTML)", html_buf.getvalue(), "Interactive_Chart.html", "text/html", use_container_width=True)

with dcols[2]:
    st.download_button("📊 下载编辑后的纯数据 (CSV)", df_edited.to_csv(index=False).encode('utf-8'), "Edited_Data.csv", "text/csv", use_container_width=True)

if report_content:
    with st.expander("📄 分析报告预览"):
        st.code(report_content)
