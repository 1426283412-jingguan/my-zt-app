import streamlit as st
import pandas as pd

# 设置页面配置：宽屏模式
st.set_page_config(page_title="LAR值分析工具", layout="wide")

def main():
    st.title("📊 LAR值分析工具")
    st.markdown("---")

    # 1. 侧边栏：文件上传
    st.sidebar.header("📁 数据导入")
    uploaded_files = st.sidebar.file_uploader(
        "上传 Excel 文件", 
        type=["xlsx"], 
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("请在左侧上传 Excel 文件开始分析。")
        return

    # 2. 选择文件
    file_names = [f.name for f in uploaded_files]
    selected_file_name = st.sidebar.selectbox("第一步：选择文件", file_names)
    file_obj = next(f for f in uploaded_files if f.name == selected_file_name)

    # 3. 核心功能：读取 Excel 的所有子表名
    try:
        excel_reader = pd.ExcelFile(file_obj)
        sheet_names = excel_reader.sheet_names
        
        # 让用户选择子表（Sheet）
        selected_sheet = st.sidebar.selectbox(
            "第二步：选择子表 (例如：2026年来料汇总表)", 
            sheet_names
        )
        
        # 加载选中的子表数据
        # 使用 str() 转换确保所有表头都是字符串，避免筛选时出错
        df = pd.read_excel(file_obj, sheet_name=selected_sheet)
        df.columns = [str(c).strip() for c in df.columns] 

    except Exception as e:
        st.error(f"读取 Excel 失败: {e}")
        return

    # 4. 动态筛选区域
    st.subheader(f"🔍 筛选条件: [{selected_file_name}] -> {selected_sheet}")
    
    # 根据你的截图，优化了筛选字段名
    potential_filters = ["月份", "周期", "供应商", "来料日期", "物料编码", "产品分类"]
    actual_columns = df.columns.tolist()
    available_filters = [col for col in potential_filters if col in actual_columns]
    
    filtered_df = df.copy()
    
    # 自动布局筛选框
    if available_filters:
        cols = st.columns(len(available_filters) if len(available_filters) < 4 else 3)
        for i, col_name in enumerate(available_filters):
            with cols[i % len(cols)]:
                # 剔除空值并排序，方便用户查找
                unique_values = sorted(df[col_name].dropna().unique().astype(str).tolist())
                selected_values = st.multiselect(f"筛选 {col_name}", unique_values)
                if selected_values:
                    # 注意：这里将数据转为字符串进行比对，兼容性更好
                    filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected_values)]

    st.markdown("---")

    # 5. LAR 指标计算 (匹配你的截图)
    # 截图显示你的列名是“判定结果”
    result_col = "判定结果" 
    
    if result_col not in actual_columns:
        st.error(f"❌ 错误：在当前子表中未找到名为“{result_col}”的列，请检查表头。")
        st.write("当前子表包含的表头有：", actual_columns)
    else:
        # 清洗数据：统一转为大写并去掉空格，防止“ok ”或“Ok”统计不到
        res_series = filtered_df[result_col].astype(str).str.upper().str.strip()
        
        ok_count = (res_series == "OK").sum()
        ng_count = (res_series == "NG").sum()
        total = ok_count + ng_count
        
        lar = (ok_count / total * 100) if total > 0 else 0

        # 展示核心指标
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总判定批数 (OK+NG)", f"{total}")
        c2.metric("OK 数量", f"{ok_count}")
        c3.metric("NG 数量", f"{ng_count}")
        c4.metric("LAR (合格率)", f"{lar:.2f}%")

        # 6. 数据显示与导出
        with st.expander("点击查看/隐藏筛选后的明细数据"):
            st.dataframe(filtered_df, use_container_width=True)

        # 导出 Excel 格式
        output_name = f"分析结果_{selected_sheet}.xlsx"
        st.download_button(
            label="📥 导出筛选后的 Excel",
            data=filtered_df.to_csv(index=False).encode('utf_8_sig'),
            file_name=output_name,
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
