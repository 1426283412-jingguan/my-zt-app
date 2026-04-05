import streamlit as st
import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from scipy import stats

# 网页基本配置
st.set_page_config(page_title="ZT 数据正态分析专业版", layout="wide")

st.title("📊 ZT 数据正态分布分析工作站")
st.markdown("上传表格、选择数据列、实时查看正态分布与统计推断。")

# --- 侧边栏：数据导入 ---
st.sidebar.header("1. 数据导入")
uploaded_file = st.sidebar.file_uploader("上传 Excel 或 CSV 文件", type=["csv", "xlsx"])

if uploaded_file:
    # 根据文件后缀读取数据
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        # 读取 Excel 需要 openpyxl 库
        df = pd.read_excel(uploaded_file)

    st.sidebar.success("文件上传成功！")

    # 筛选出数字列供用户选择
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        column_name = st.sidebar.selectbox("选择要分析的数字列", numeric_cols)

        if column_name:
            st.subheader(f"📈 {column_name} 的正态分布分析")
            
            # 1. 提取数据并剔除空值
            plot_data = df[column_name].dropna()

            if len(plot_data) > 0:
                # 2. 使用 Plotly 生成直方图和拟合曲线
                hist_data = [plot_data]
                group_labels = [column_name]

                # 创建带正态分布曲线的图表
                fig = ff.create_distplot(hist_data, group_labels, bin_size=.5, show_rug=False)
                
                # 3. 在网页上显示图表
                st.plotly_chart(fig, use_container_width=True)
                
                # 4. 展示核心统计指标
                st.markdown("### 核心统计指标")
                col1, col2, col3 = st.columns(3)
                col1.metric("均值 (Mean)", f"{plot_data.mean():.2f}")
                col2.metric("标准差 (Std)", f"{plot_data.std():.2f}")
                col3.metric("样本量 (Count)", f"{len(plot_data)}")
            else:
                st.warning("选中列中没有有效数字数据。")
    else:
        st.error("表格中没有发现数字列，请检查数据格式。")

else:
    # 未上传文件时的默认提示
    st.info("💡 请在左侧侧边栏上传您的数据文件（CSV 或 Excel）。")
    
    # 模拟一个示例展示
    st.subheader("示例展示（模拟正态分布数据）")
    example_data = np.random.normal(100, 15, 500)
    fig_ex = ff.create_distplot([example_data], ['示例数据'], bin_size=2, show_rug=False)
    st.plotly_chart(fig_ex, use_container_width=True)
