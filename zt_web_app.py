import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io

# --- 1. 页面整体配置 ---
st.set_page_config(page_title="高级数据分析工作站", layout="wide", page_icon="🧪")

# 自定义 UI 样式
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #f0f2f6; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #eee; }
    .plot-container { border: 1px solid #f0f2f6; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：数据中心 ---
with st.sidebar:
    st.title("⚙️ 控制面板")
    analysis_type = st.segmented_control(
        "选择分析模式", ["正态分布", "趋势回归"], default="正态分布"
    )
    
    st.divider()
    st.subheader("📁 数据录入")
    upload_tab, paste_tab = st.tabs(["文件上传", "文本粘贴"])
    
    df_input = pd.DataFrame()
    
    with upload_tab:
        uploaded_file = st.file_uploader("拖拽 Excel/CSV", type=["csv", "xlsx"])
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
                
    with paste_tab:
        paste_text = st.text_area("从 Excel 复制列并粘贴 (含表头)", height=150, placeholder="序号\t数值\n1\t10.5\n2\t11.2...")
        if paste_text:
            df_input = pd.read_csv(io.StringIO(paste_text), sep='\t' if '\t' in paste_text else ',')

    if df_input.empty:
        # 提供默认展示数据
        df_input = pd.DataFrame({
            "序号": np.arange(1, 51),
            "数值": np.random.normal(100, 15, 50).round(2)
        })
        st.info("💡 当前显示演示数据，请上传或粘贴您的数据。")

    st.divider()
    st.subheader("📝 在线数据编辑")
    # 允许用户直接在网页上修改、增加、删除数据
    working_df = st.data_editor(
        df_input, 
        num_rows="dynamic", 
        use_container_width=True,
        key="data_editor"
    )

# --- 3. 核心分析逻辑 ---

if analysis_type == "正态分布":
    st.title("📊 局部正态分布与极差分析")
    
    col_name = st.sidebar.selectbox("选择分析列", working_df.columns)
    # 清洗非数值
    clean_data = pd.to_numeric(working_df[col_name], errors='coerce').dropna()
    
    if len(clean_data) > 1:
        # 局部范围控制
        d_min, d_max = float(clean_data.min()), float(clean_data.max())
        range_val = st.sidebar.slider("🔍 选定分析范围", d_min, d_max, (d_min, d_max))
        
        # 统计计算
        subset = clean_data[(clean_data >= range_val[0]) & (clean_data <= range_val[1])]
        
        if not subset.empty:
            # 指标计算
            sub_mean = subset.mean()
            sub_std = subset.std()
            sub_range = subset.max() - subset.min()
            sub_ratio = (len(subset) / len(clean_data)) * 100
            
            # 绘图设置
            bin_w = st.sidebar.number_input("组距 (Bin Width)", value=(range_val[1]-range_val[0])/15, step=0.1)
            conf_level = st.sidebar.selectbox("置信区间水平", [0.90, 0.95, 0.99], index=1)
            ci = stats.t.interval(conf_level, len(subset)-1, loc=sub_mean, scale=stats.sem(subset))

            # 展示指标卡
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("局部样本量", len(subset))
            m2.metric("局部极差 (Range)", f"{sub_range:.3f}")
            m3.metric("样本占比", f"{sub_ratio:.1f}%")
            m4.metric("局部均值", f"{sub_mean:.3f}")

            # 绘制图表
            fig = go.Figure()
            bins_edges = np.arange(range_val[0], range_val[1] + bin_w, bin_w)
            counts, _ = np.histogram(subset, bins=bins_edges)
            
            fig.add_trace(go.Bar(
                x=bins_edges[:-1] + bin_w/2, y=counts/len(subset),
                name="分布频率", marker_color='rgba(52, 73, 94, 0.6)',
                text=[f"{(c/len(subset))*100:.1f}%" for c in counts], textposition='outside'
            ))
            
            x_line = np.linspace(range_val[0], range_val[1], 200)
            y_line = stats.norm.pdf(x_line, sub_mean, sub_std) * bin_w
            fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', name="局部理论曲线", line=dict(color='#e74c3c', width=3)))
            
            fig.add_vrect(x0=ci[0], x1=ci[1], fillcolor="rgba(46, 204, 113, 0.15)", line_width=0, annotation_text="置信区间")

            fig.update_layout(template="simple_white", height=550, xaxis_range=[range_val[0], range_val[1]], hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f"💡 **结论**：在当前范围内，均值有 {int(conf_level*100)}% 的概率落在 `[{ci[0]:.4f}, {ci[1]:.4f}]` 之间。")
        else:
            st.error("此范围内无数据。")

else:  # --- 趋势回归 (折线图) 模式 ---
    st.title("📈 折线趋势与回归分析")
    
    col_x = st.sidebar.selectbox("选择 X 轴 (横轴)", working_df.columns, index=0)
    col_y = st.sidebar.selectbox("选择 Y 轴 (纵轴)", working_df.columns, index=min(1, len(working_df.columns)-1))
    
    # 清洗数据
    reg_df = working_df[[col_x, col_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(reg_df) >= 2:
        # X轴和Y轴双向范围控制
        x_lim = st.sidebar.slider("X轴显示范围", float(reg_df[col_x].min()), float(reg_df[col_x].max()), (float(reg_df[col_x].min()), float(reg_df[col_x].max())))
        y_lim = st.sidebar.slider("Y轴显示范围", float(reg_df[col_y].min()), float(reg_df[col_y].max()), (float(reg_df[col_y].min()), float(reg_df[col_y].max())))
        
        # 过滤数据
        f_df = reg_df[
            (reg_df[col_x] >= x_lim[0]) & (reg_df[col_x] <= x_lim[1]) &
            (reg_df[col_y] >= y_lim[0]) & (reg_df[col_y] <= y_lim[1])
        ]
        
        if not f_df.empty:
            # 回归计算
            slope, intercept, r_val, p_val, std_err = stats.linregress(f_df[col_x], f_df[col_y])
            r_sq = r_val**2
            
            # 指标展示
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("判定系数 $R^2$", f"{r_sq:.4f}")
            c2.metric("相关系数 $r$", f"{r_val:.4f}")
            c3.metric("拟合斜率", f"{slope:.4f}")
            c4.metric("P值 (显著性)", f"{p_val:.4e}")

            # 绘图
            fig = go.Figure()
            # 原始折线
            fig.add_trace(go.Scatter(x=f_df[col_x], y=f_df[col_y], mode='lines+markers', name="原始趋势", line=dict(color='#3498db', width=2)))
            # 回归拟合线
            line_x = np.array([x_lim[0], x_lim[1]])
            line_y = slope * line_x + intercept
            fig.add_trace(go.Scatter(x=line_x, y=line_y, mode='lines', name="拟合回归线", line=dict(color='#e74c3c', dash='dash')))

            fig.update_layout(
                template="simple_white", height=550,
                xaxis=dict(title=col_x, range=[x_lim[0], x_lim[1]]),
                yaxis=dict(title=col_y, range=[y_lim[0], y_lim[1]]),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.success(f"线性回归方程：$y = {slope:.4f}x + {intercept:.4f}$")
        else:
            st.error("选定范围内没有有效坐标点。")
    else:
        st.warning("数据量不足以进行回归拟合。")

# --- 4. 底部工具栏 ---
st.divider()
st.subheader("📂 结果处理")
col_down, col_info = st.columns([1, 4])
with col_down:
    st.download_button(
        "导出当前表格为 CSV",
        working_df.to_csv(index=False).encode('utf-8'),
        "processed_data.csv",
        "text/csv"
    )
with col_info:
    st.caption("提示：在左侧编辑器中修改数据后，右侧所有统计量（包括 $R^2$、极差、正态曲线）将自动重算。")
