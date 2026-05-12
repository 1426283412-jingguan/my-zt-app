import streamlit as st
import pandas as pd

# 设置页面配置
st.set_page_config(page_title="质量数据分析终端", layout="wide")

def main():
    st.title("📊 质量数据分析与 LAR 统计工具")
    st.markdown("---")

    # 1. 文件上传
    st.sidebar.header("📁 数据导入")
    uploaded_files = st.sidebar.file_uploader(
        "上传一个或多个 Excel/CSV 文件", 
        type=["xlsx", "csv"], 
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("请在左侧侧边栏上传需要分析的表格文件。")
        return

    # 2. 选择要分析的表格
    file_names = [f.name for f in uploaded_files]
    selected_file_name = st.sidebar.selectbox("选择当前分析的表格", file_names)
    
    # 查找选中的文件对象
    file_obj = next(f for f in uploaded_files if f.name == selected_file_name)

    # 读取数据
    try:
        if selected_file_name.endswith('.csv'):
            df = pd.read_csv(file_obj)
        else:
            df = pd.read_excel(file_obj)
    except Exception as e:
        st.error(f"读取文件失败: {e}")
        return

    # 3. 动态筛选器设计
    st.subheader(f"🔍 筛选条件: {selected_file_name}")
    
    # 预设可能的表头，如果不存在则忽略
    potential_filters = ["月份", "周期", "供应商", "来料日期", "物料编码", "产品分类"]
    actual_columns = df.columns.tolist()
    
    # 自动识别存在的筛选列
    available_filters = [col for col in potential_filters if col in actual_columns]
    
    # 创建布局：每行 3 个筛选下拉框
    cols = st.columns(3)
    filtered_df = df.copy()

    for i, col_name in enumerate(available_filters):
        with cols[i % 3]:
            unique_values = df[col_name].dropna().unique().tolist()
            selected_values = st.multiselect(f"筛选 {col_name}", unique_values)
            if selected_values:
                filtered_df = filtered_df[filtered_df[col_name].isin(selected_values)]

    st.markdown("---")

    # 4. LAR 指标计算
    # 假设判定结果列名为 "判定结果"，如果是其他名称请手动适配
    result_col = "判定结果" 
    
    if result_col not in actual_columns:
        st.warning(f"未在表格中找到 '{result_col}' 列，请检查表头。")
    else:
        # 统计 OK 和 NG
        counts = filtered_df[result_col].value_counts()
        ok_count = counts.get("OK", 0)
        ng_count = counts.get("NG", 0)
        total = ok_count + ng_count
        
        lar = (ok_count / total * 100) if total > 0 else 0

        # 5. 美观的数据面板展示
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("总判定批数", f"{total}")
        m2.metric("OK 数量", f"{ok_count}", delta_color="normal")
        m3.metric("NG 数量", f"{ng_count}", delta_color="inverse")
        m4.metric("LAR (批次合格率)", f"{lar:.2f}%")

        # 6. 数据可视化预览
        st.subheader("📋 筛选后的明细数据")
        st.dataframe(filtered_df, use_container_width=True)

        # 下载筛选后的数据
        csv = filtered_df.to_csv(index=False).encode('utf_8_sig')
        st.download_button(
            label="📥 下载当前筛选报表",
            data=csv,
            file_name=f"Filtered_{selected_file_name}.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
