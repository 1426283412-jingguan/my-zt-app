import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io

# --- 1. 页面配置 ---
st.set_page_config(page_title="综合数据分析工作站", layout="wide", page_icon="📊")

# 自定义 CSS 样式
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .plot-container { border-radius: 12px; overflow: hidden; background: white; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：数据管理 ---
with st.sidebar:
    st.title("🛠 控制中心")
    analysis_mode = st.radio("选择分析模式", ["📈 正态分布分析", "📉 折线回归分析"])
    
    st.divider()
    st.subheader("📥 数据录入")
    input_method = st.toggle("使用粘贴/编辑模式", value=False)
    
    raw_df = pd.DataFrame()
    if not input_method:
        uploaded_file = st.file_uploader("上传 Excel/CSV", type=["csv", "xlsx"])
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)
    else:
        st.caption("在下方编辑或粘贴数据 (默认第一行为表头)")
        # 提供一个初始模板
        init_data = "序号,数值\n1,10.2\n2,12.5\n3,11.8\n4,14.2\n5,13.9"
        paste_text = st.text_area("数据粘贴区", value=init_data, height=150)
        if paste_text:
            raw_df = pd.read_csv(io.StringIO(paste_text))

    if raw_df.empty:
        st.info("请先导入数据以开始")
        st.stop()

    st.divider()
    st.subheader("📝 数据在线编辑")
    # 使用 Data Editor 允许用户直接修改数据
    edited_df = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True)

# --- 3. 分析逻辑 ---

if analysis_mode == "📈 正态分布分析":
    target_col = st.sidebar.selectbox("选择分析列", edited_df.columns)
    data = pd.to_numeric(edited_df[target_col], errors='coerce').dropna()
    
    if len(data) < 2:
        st.warning("有效数据不足")
        st.stop()

    # 范围过滤
    d_min, d_max = float(data.min()), float(data.max())
    r_min, r_max = st.sidebar.slider("数值显示范围", d_min, d_max, (d_min, d_max))
    subset = data[(data >= r_min) & (data <= r_max)]
    
    # 计算
    mean, std = subset.mean(), subset.std()
    conf_level = st.sidebar.select_slider("置信水平", [0.90, 0.95, 0.99], 0.95)
    ci = stats.t.interval(conf_level, len(subset)-1, loc=mean, scale=stats.sem(subset))

    # 绘图
    fig = go.Figure()
    bins = st.sidebar.number_input("组距", value=(r_max-r_min)/15, step=0.1)
    hist_bins = np.arange(r_min, r_max + bins, bins)
    counts, _ = np.histogram(subset, bins=hist_bins)
    
    fig.add_trace(go.Bar(x=hist_bins[:-1]+bins/2, y=counts/len(subset), name="分布占比", marker_color='#34495e'))
    x_curve = np.linspace(r_min, r_max, 100)
    fig.add_trace(go.Scatter(x=x_curve, y=stats.norm.pdf(x_curve, mean, std)*bins, name="正态曲线", line=dict(color='red')))
    
    fig.update_layout(title="局部正态分布图", template="simple_white", xaxis_range=[r_min, r_max])
    
    # 展示指标
    st.title("正态分布深度分析")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("局部样本量", len(subset))
    c2.metric("极差 (Range)", f"{subset.max()-subset.min():.3f}")
    c3.metric("均值", f"{mean:.3f}")
    c4.metric("标准差", f"{std:.3f}")
    
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"💡 {conf_level*100}% 置信区间: [{ci[0]:.4f}, {ci[1]:.4f}]")

else:  # --- 折线回归分析模式 ---
    st.title("折线趋势与回归分析")
    cols = edited_df.columns.tolist()
    
    col_x = st.sidebar.selectbox("选择 X 轴 (自变量)", cols, index=0)
    col_y = st.sidebar.selectbox("选择 Y 轴 (因变量)", cols, index=min(1, len(cols)-1))
    
    # 转换为数字
    plot_df = edited_df[[col_x, col_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(plot_df) < 2:
        st.error("数据点不足以进行回归分析")
        st.stop()

    # X/Y 范围控制
    x_min_f, x_max_f = float(plot_df[col_x].min()), float(plot_df[col_x].max())
    y_min_f, y_max_f = float(plot_df[col_y].min()), float(plot_df[col_y].max())
    
    sel_x = st.sidebar.slider("X 轴范围", x_min_f, x_max_f, (x_min_f, x_max_f))
    sel_y = st.sidebar.slider("Y 轴范围", y_min_f, y_max_f, (y_min_f, y_max_f))
    
    filtered_df = plot_df[
        (plot_df[col_x] >= sel_x[0]) & (plot_df[col_x] <= sel_x[1]) &
        (plot_df[col_y] >= sel_y[0]) & (plot_df[col_y] <= sel_y[1])
    ]

    # 回归计算
    slope, intercept, r_value, p_value, std_err = stats.linregress(filtered_df[col_x], filtered_df[col_y])
    r_squared = r_value**2

    # 绘图
    fig = go.Figure()
    # 原始折线
    fig.add_trace(go.Scatter(x=filtered_df[col_x], y=filtered_df[col_y], mode='lines+markers', name="原始趋势", line=dict(color='#3498db')))
    # 回归线
    reg_x = np.array([sel_x[0], sel_x[1]])
    reg_y = slope * reg_x + intercept
    fig.add_trace(go.Scatter(x=reg_x, y=reg_y, mode='lines', name="回归拟合线", line=dict(color='red', dash='dash')))

    fig.update_layout(
        template="simple_white",
        xaxis_title=col_x, yaxis_title=col_y,
        xaxis_range=[sel_x[0], sel_x[1]], yaxis_range=[sel_y[0], sel_y[1]]
    )

    # 显示结果
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("判定系数 $R^2$", f"{r_squared:.4f}")
    m2.metric("相关系数 $r$", f"{r_value:.4f}")
    m3.metric("斜率 (Slope)", f"{slope:.4f}")
    m4.metric("截距 (Intercept)", f"{intercept:.4f}")

    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"📈 **拟合方程**: $y = {slope:.4f}x + {intercept:.4f}$")
    with st.expander("什么是 $R^2$？"):
        st.write("""
        判定系数 $R^2$ 衡量了回归方程对观测值的拟合程度。
        - $R^2 = 1$：完美拟合，所有点都在直线上。
        - $R^2 = 0$：模型完全不能解释数据的变动。
        - 通常 $R^2 > 0.8$ 被认为具有很强的相关性。
        """)

# --- 4. 数据表格导出 ---
st.divider()
st.subheader("📂 结果导出")
csv = edited_df.to_csv(index=False).encode('utf-8')
st.download_button("下载当前处理后的表格", csv, "processed_data.csv", "text/csv")
