import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 页面基本配置
st.set_page_config(page_title="质量数据可视分析看板", layout="wide", initial_sidebar_state="expanded")

# 自定义 CSS 样式优化界面
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

def calculate_metrics(data, result_col="判定结果"):
    """核心统计逻辑：计算 OK, NG 和 LAR"""
    if data.empty:
        return 0, 0, 0, 0
    # 统一清洗结果列：转字符串、去空格、转大写
    results = data[result_col].astype(str).str.strip().str.upper()
    ok_count = (results == "OK").sum()
    ng_count = (results == "NG").sum()
    total = ok_count + ng_count
    lar = (ok_count / total * 100) if total > 0 else 0
    return ok_count, ng_count, total, lar

def main():
    st.title("📈 质量数据智能看板 (LAR分析)")
    
    # --- 侧边栏：数据管理 ---
    st.sidebar.header("📁 数据中心")
    uploaded_files = st.sidebar.file_uploader("上传 Excel 报表", type=["xlsx"], accept_multiple_files=True)

    if not uploaded_files:
        st.info("👋 请在左侧上传 Excel 文件开始分析。")
        return

    # 文件和子表选择
    file_mapping = {f.name: f for f in uploaded_files}
    selected_file_name = st.sidebar.selectbox("选择文件", list(file_mapping.keys()))
    file_obj = file_mapping[selected_file_name]

    try:
        xl = pd.ExcelFile(file_obj)
        selected_sheet = st.sidebar.selectbox("选择子表", xl.sheet_names)
        # 读取数据，强制将物料编码读为字符串，防止坐标轴显示错误
        df = pd.read_excel(file_obj, sheet_name=selected_sheet, dtype={'物料编码': str, '物料号': str})
        df.columns = [str(c).strip() for c in df.columns]
    except Exception as e:
        st.error(f"读取失败: {e}")
        return

    # --- 动态过滤器 ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 数据筛选")
    
    # 预定义的关键维度
    filter_cols = ["月份", "周期", "供应商", "物料编码", "产品分类", "来料日期"]
    actual_cols = [c for c in filter_cols if c in df.columns]
    
    filtered_df = df.copy()
    for col in actual_cols:
        options = sorted(df[col].dropna().unique().astype(str))
        selected = st.sidebar.multiselect(f"{col}", options)
        if selected:
            filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)]

    # --- 核心指标展示 ---
    ok, ng, total, lar = calculate_metrics(filtered_df)
    
    st.subheader("📌 核心质量指标 (Total)")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("筛选后总批数", total)
    with c2: st.metric("OK 数量", ok)
    with c3: st.metric("NG 数量", ng, delta=ng, delta_color="inverse" if ng > 0 else "normal")
    with c4: st.metric("总 LAR (合格率)", f"{lar:.2f}%")

    st.markdown("---")

    # --- 分维度深度分析 ---
    if not filtered_df.empty:
        st.subheader("📊 维度对比分析")
        
        # 让用户选择对比维度
        group_dim = st.selectbox("选择分析维度 (按此项拆分展示 LAR):", actual_cols, index=0 if actual_cols else None)
        
        if group_dim:
            # 分组计算每项的 LAR
            report = filtered_df.groupby(group_dim).apply(
                lambda x: pd.Series(calculate_metrics(x))
            ).reset_index()
            report.columns = [group_dim, 'OK', 'NG', '总数', 'LAR(%)']
            report['LAR(%)'] = report['LAR(%)'].round(2)

            tab1, tab2, tab3 = st.tabs(["📉 可视化对比图", "📋 统计明细表", "🔍 原始数据"])

            with tab1:
                # 绘制交互式柱状图
                fig = px.bar(
                    report, x=group_dim, y='LAR(%)', 
                    text='LAR(%)', color='LAR(%)',
                    color_continuous_scale='RdYlGn', # 红黄绿渐变
                    hover_data=['OK', 'NG', '总数'],
                    title=f"各{group_dim} 的 LAR 合格率对比"
                )
                # 强制 X 轴为标签型，解决物料编码数字显示问题
                fig.update_layout(xaxis_type='category') 
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                # 修正：使用 st.dataframe 代替 st.table 以获得更好的样式兼容性
                st.write(f"**各 {group_dim} 统计详情**")
                styled_report = report.style.background_gradient(subset=['LAR(%)'], cmap='RdYlGn', vmin=90, vmax=100)
                st.dataframe(styled_report, use_container_width=True)

            with tab3:
                st.dataframe(filtered_df, use_container_width=True)
                csv = filtered_df.to_csv(index=False).encode('utf_8_sig')
                st.download_button("📥 导出当前筛选明细", data=csv, file_name="quality_analysis.csv")
    else:
        st.warning("⚠️ 当前筛选条件下无数据，请重新调整筛选器。")

if __name__ == "__main__":
    main()
