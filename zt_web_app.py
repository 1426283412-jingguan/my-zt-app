import streamlit as st
import pandas as pd
import plotly.express as px

# 页面配置
st.set_page_config(page_title="高级质量数据分析终端", layout="wide")

def calculate_lar(data, result_col):
    """通用 LAR 计算函数"""
    res_series = data[result_col].astype(str).str.upper().str.strip()
    ok = (res_series == "OK").sum()
    ng = (res_series == "NG").sum()
    total = ok + ng
    lar = (ok / total * 100) if total > 0 else 0
    return ok, ng, total, lar

def main():
    st.title("🚀 高级质量数据分析与可视化平台")
    st.markdown("---")

    # 1. 侧边栏：数据导入
    st.sidebar.header("📁 数据中心")
    uploaded_files = st.sidebar.file_uploader("上传 Excel", type=["xlsx"], accept_multiple_files=True)

    if not uploaded_files:
        st.info("💡 请在左侧上传 Excel 文件以开启分析。")
        return

    # 选择文件与子表
    file_names = [f.name for f in uploaded_files]
    selected_file = st.sidebar.selectbox("选择文件", file_names)
    file_obj = next(f for f in uploaded_files if f.name == selected_file)

    try:
        excel_reader = pd.ExcelFile(file_obj)
        selected_sheet = st.sidebar.selectbox("选择子表", excel_reader.sheet_names)
        df = pd.read_excel(file_obj, sheet_name=selected_sheet)
        df.columns = [str(c).strip() for c in df.columns]
    except Exception as e:
        st.error(f"读取失败: {e}")
        return

    # 2. 动态筛选器
    st.subheader("🛠️ 数据筛选与维度选择")
    potential_filters = ["月份", "周期", "供应商", "物料编码", "产品分类"]
    actual_columns = df.columns.tolist()
    available_filters = [col for col in potential_filters if col in actual_columns]
    
    filtered_df = df.copy()
    
    # 筛选布局
    if available_filters:
        f_cols = st.columns(len(available_filters))
        for i, col_name in enumerate(available_filters):
            with f_cols[i]:
                unique_vals = sorted(df[col_name].dropna().unique().astype(str).tolist())
                selected_vals = st.multiselect(f"{col_name}", unique_vals)
                if selected_vals:
                    filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected_vals)]

    # 3. 维度拆分设置 (核心优化点)
    st.markdown("---")
    analysis_col1, analysis_col2 = st.columns([1, 3])
    
    with analysis_col1:
        st.write("📊 **分析维度设置**")
        group_by_col = st.selectbox("选择要单独输出 LAR 的维度:", available_filters if available_filters else ["无"])
        result_col = "判定结果"

    if result_col not in actual_columns:
        st.error(f"未找到“{result_col}”列")
        return

    # 4. 计算总 LAR
    total_ok, total_ng, total_sum, total_lar = calculate_lar(filtered_df, result_col)

    # 5. 计算分组 LAR
    if group_by_col != "无":
        # 按照选定维度进行聚合计算
        def get_group_stats(group):
            ok, ng, tot, lar = calculate_lar(group, result_col)
            return pd.Series({'OK': ok, 'NG': ng, '总数': tot, 'LAR(%)': round(lar, 2)})

        group_stats = filtered_df.groupby(group_by_col).apply(get_group_stats).reset_index()
    else:
        group_stats = pd.DataFrame()

    # 6. 结果展示
    # 顶部总览
    st.subheader("📌 核心指标总览 (Total Overview)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("筛选后总批数", f"{total_sum}")
    m2.metric("总 OK 数量", f"{total_ok}")
    m3.metric("总 NG 数量", f"{total_ng}", delta=None, delta_color="inverse")
    m4.metric("总 LAR", f"{total_lar:.2f}%")

    st.markdown("---")

    # 细节对比展示
    if not group_stats.empty:
        tab1, tab2 = st.tabs(["📈 可视化图表", "📋 详细数据表"])
        
        with tab1:
            st.write(f"**各 {group_by_col} LAR 值对比图**")
            # 绘制柱状图
            fig = px.bar(
                group_stats, 
                x=group_by_col, 
                y='LAR(%)',
                text='LAR(%)',
                color='LAR(%)',
                color_continuous_scale='RdYlGn', # 红色到绿色的渐变
                hover_data=['OK', 'NG', '总数'],
                height=500
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.write(f"**各 {group_by_col} 统计明细**")
            st.table(group_stats.style.background_gradient(subset=['LAR(%)'], cmap='RdYlGn'))
    
    # 7. 明细导出
    st.markdown("---")
    with st.expander("查看当前筛选的原始明细数据"):
        st.dataframe(filtered_df, use_container_width=True)
        csv = filtered_df.to_csv(index=False).encode('utf_8_sig')
        st.download_button("📥 导出当前明细", data=csv, file_name="analysis_export.csv", mime="text/csv")

if __name__ == "__main__":
    main()
