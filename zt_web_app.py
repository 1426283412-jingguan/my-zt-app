import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 页面配置：使用专业深色/浅色融合主题
st.set_page_config(page_title="SQE 质量数据决策看板", layout="wide")

# 自定义 UI 样式
st.markdown("""
    <style>
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stPlotlyChart { background-color: #ffffff; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

def clean_data(df):
    """强制转换关键列类型，防止科学计数法"""
    str_cols = ['物料编码', '供应商', '物料号', '送检单号', '周期']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False)
    
    # 尝试转换日期
    date_cols = ['来料日期', '入库日期', '日期']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def calculate_lar_metrics(data):
    """计算核心质量指标"""
    result_col = "判定结果"
    if result_col not in data.columns:
        return None
    
    # 清洗：去除空格、转大写，兼容“合格/不合格”
    res = data[result_col].astype(str).str.strip().str.upper()
    ok_mask = res.isin(['OK', '合格', 'PASS'])
    ng_mask = res.isin(['NG', '不合格', 'FAIL', 'REJECT'])
    
    ok_count = ok_mask.sum()
    ng_count = ng_mask.sum()
    total = ok_count + ng_count
    lar = (ok_count / total * 100) if total > 0 else 0
    return {"OK": ok_count, "NG": ng_count, "Total": total, "LAR": lar}

def main():
    st.title("📊 SQE 供应链质量监控看板")
    st.caption("支持多表切换、维度钻取及不良分布分析")

    # --- 侧边栏：数据中心 ---
    st.sidebar.header("📥 数据导入")
    uploaded_files = st.sidebar.file_uploader("上传 Excel 报表", type=["xlsx"], accept_multiple_files=True)

    if not uploaded_files:
        st.info("💡 请在左侧上传 Excel 文件。建议包含列：判定结果、供应商、物料编码、来料日期、不良描述。")
        return

    # 文件与子表选择
    file_map = {f.name: f for f in uploaded_files}
    sel_file_name = st.sidebar.selectbox("选择文件", list(file_map.keys()))
    
    try:
        xl = pd.ExcelFile(file_map[sel_file_name])
        sel_sheet = st.sidebar.selectbox("选择子表", xl.sheet_names)
        df = pd.read_excel(file_map[sel_file_name], sheet_name=sel_sheet)
        df.columns = [str(c).strip() for c in df.columns]
        df = clean_data(df)
    except Exception as e:
        st.error(f"解析失败: {e}")
        return

    # --- 动态过滤器 ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 筛选中心")
    
    filter_dims = ["供应商", "物料编码", "产品分类", "月份", "周期"]
    actual_filters = [c for c in filter_dims if c in df.columns]
    
    f_df = df.copy()
    for col in actual_filters:
        opts = sorted(df[col].dropna().unique().astype(str))
        sel = st.sidebar.multiselect(f"筛选 {col}", opts)
        if sel:
            f_df = f_df[f_df[col].astype(str).isin(sel)]

    # --- 1. 核心指标面板 ---
    metrics = calculate_lar_metrics(f_df)
    if not metrics:
        st.error("未在表中找到 '判定结果' 列")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总判定批数", metrics["Total"])
    c2.metric("OK 批次", metrics["OK"])
    c3.metric("NG 批次", metrics["NG"], delta=f"{metrics['NG']} 待处理", delta_color="inverse")
    c4.metric("LAR (合格率)", f"{metrics['LAR']:.2f}%")

    st.markdown("---")

    # --- 2. 深度分析区 ---
    t1, t2, t3 = st.tabs(["📈 趋势与维度对比", "⚠️ 不良项分析", "📋 数据明细"])

    with t1:
        col_left, col_right = st.columns([1, 1])
        
        # A. 维度对比 (柱状图)
        with col_left:
            group_col = st.selectbox("对比维度:", actual_filters if actual_filters else [df.columns[0]])
            group_res = f_df.groupby(group_col).apply(lambda x: calculate_lar_metrics(x)["LAR"]).reset_index()
            group_res.columns = [group_col, 'LAR(%)']
            
            fig_bar = px.bar(group_res, x=group_col, y='LAR(%)', color='LAR(%)',
                            color_continuous_scale='RdYlGn', text_auto='.1f',
                            title=f"各{group_col} 合格率对比")
            fig_bar.update_layout(xaxis_type='category')
            st.plotly_chart(fig_bar, use_container_width=True)

        # B. 趋势分析 (折线图)
        with col_right:
            date_col = next((c for c in ['来料日期', '入库日期', '日期'] if c in f_df.columns), None)
            if date_col:
                trend_df = f_df.copy()
                trend_df['时间序列'] = trend_df[date_col].dt.strftime('%Y-%W') # 按周统计
                trend_res = trend_df.groupby('时间序列').apply(lambda x: calculate_lar_metrics(x)["LAR"]).reset_index()
                trend_res.columns = ['周次', 'LAR(%)']
                
                fig_line = px.line(trend_res, x='周次', y='LAR(%)', markers=True,
                                  title="品质稳定性趋势 (按周计算)", line_shape="spline")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.warning("表中缺少日期列，无法生成趋势图")

    with t2:
        # 不良分布 (Pareto Chart)
        defect_col = next((c for c in ['不良描述', '不良原因', '缺陷'] if c in f_df.columns), None)
        if defect_col:
            st.subheader("🌋 不良项分布 (Pareto)")
            defect_counts = f_df[defect_col].value_counts().reset_index()
            defect_counts.columns = ['缺陷描述', '频次']
            
            fig_pie = px.pie(defect_counts, names='缺陷描述', values='频次', hole=0.4,
                            title="不良构成比例")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("未检测到“不良描述”列，无法进行缺陷分析")

    with t3:
        # 统计表格显示 (修复 Styler 报错)
        st.subheader("📊 统计摘要")
        summary_table = f_df.groupby(group_col).apply(
            lambda x: pd.Series(calculate_metrics_full(x))
        ).reset_index()
        
        # 使用 st.dataframe 的内置列着色，更稳定
        st.dataframe(
            summary_table.style.highlight_min(subset=['LAR(%)'], color='#ffcccc')
                               .highlight_max(subset=['LAR(%)'], color='#ccffcc'),
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("📄 原始明细数据导出")
        st.dataframe(f_df, use_container_width=True)
        
        csv = f_df.to_csv(index=False).encode('utf_8_sig')
        st.download_button("📥 导出筛选后的报表", data=csv, file_name="Quality_Report.csv")

def calculate_metrics_full(data):
    m = calculate_lar_metrics(data)
    return {'OK数量': m['OK'], 'NG数量': m['NG'], '总批数': m['Total'], 'LAR(%)': round(m['LAR'], 2)}

if __name__ == "__main__":
    main()
