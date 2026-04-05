import streamlit as st
import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from scipy import stats

st.set_page_config(page_title="ZT 数据正态分析专业版", layout="wide")

st.title("📊 ZT 数据正态分布分析工作站")
st.markdown("上传表格、选择数据列、实时查看正态分布与统计推断。")

# --- 侧边栏：数据导入 ---
st.sidebar.header("1. 数据导入")
uploaded_file = st.sidebar.file_input("上传 Excel 或 CSV 文件", type=["csv", "xlsx"])

data = None
column_name = None

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    st.sidebar.success("文件上传成功！")
    # 让用户选择哪一列
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    column_name = st.sidebar.selectbox("选择要分析的数字列", numeric_cols)
    data = df[column_name].dropna().values
else:
    st.info("💡 请在左侧上传文件。现在显示的是系统生成的模拟示例数据：")
    data = np.random.normal(100, 15, 500)

# --- 侧边栏：参数设置 ---
st.sidebar.header("2. 参数微调")
bin_size = st.sidebar.slider("调整组距 (Bin Width)", min_value=0.1, max_value=20.0, value=2.0)

# 横坐标范围筛选
min_val, max_val = float(np.min(data)), float(np.max(data))
range_select = st.sidebar.slider("选择横坐标分析范围", min_val, max_val, (min_val, max_val))

# --- 核心计算 ---
filtered_data = data[(data >= range_select[0]) & (data <= range_select[1])]

# 统计量计算
mean_all = np.mean(data)
mean_sel = np.mean(filtered_data) if len(filtered_data) > 0 else 0
std_all = np.std(data)
var_all = np.var(data)
n = len(data)
# 95% 置信区间
conf_int = stats.t.interval(0.95, n-1, loc=mean_all, scale=stats.sem(data))

# --- 布局：上方统计看板 ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("所有数据均值", f"{mean_all:.3f}")
col2.metric("选定范围均值", f"{mean_sel:.3f}", delta=f"{mean_sel-mean_all:.3f}")
col3.metric("标准差 (Std)", f"{std_all:.3f}")
col4.metric("样本量 (N)", f"{len(filtered_data)}")

with st.expander("查看更多详细统计信息 (方差、置信区间等)"):
    st.write(f"**方差 (Variance):** {var_all:.4f}")
    st.write(f"**95% 置信区间:** [{conf_int[0]:.3f}  至  {conf_int[1]:.3f}]")
    st.write(f"**数据范围:** 从 {np.min(data):.2f} 到 {np.max(data):.2f}")

# --- 布局：图表展示 ---
# 创建带正态曲线的直方图
fig = ff.create_distplot([filtered_data], ['数据分布'], bin_size=bin_size, 
                         show_curve=True, show_rug=False, colors=['#3498db'])

fig.update_layout(
    title=f"正态分布拟合图 (分析列: {column_name if column_name else '示例'})",
    xaxis_title="数值",
    yaxis_title="密度",
    template="plotly_white"
)

# 在柱子上添加百分比标注 (Plotly 自动处理)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("ZT 分析工具 | 所有人联网即可使用的专业质量管理软件")