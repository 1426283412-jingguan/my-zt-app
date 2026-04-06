import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import io
import datetime

# --- 1. 页面级配置 ---
st.set_page_config(page_title="数据统计实验室 V6.0", layout="wide", page_icon="🧪")

# 自定义 CSS：增强卡片对比度
st.markdown("""
    <style>
    .stMetric { border-left: 5px solid #3498db; background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：导航与数据导入 ---
with st.sidebar:
    st.title("🔬 实验控制台")
    
    # 【需求】并列可选的分析模块
    analysis_type = st.radio("选择分析引擎：", ["📊 正态分布分析", "📈 趋势回归分析"])
    
    st.divider()
    st.subheader("📥 数据录入")
    up_file = st.file_uploader("1. 上传 Excel/CSV 文件", type=["csv", "xlsx"])
    ps_text = st.text_area("2. 或者：直接在此粘贴 Excel 数据", height=120, placeholder="序号\t数值...")

    # 数据解析逻辑
    df_raw = pd.DataFrame()
    if up_file:
        df_raw = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
    elif ps_text:
        df_raw = pd.read_csv(io.StringIO(ps_text), sep='\t' if '\t' in ps_text else ',')
    
    # 默认演示数据逻辑 (已修正语法)
    if df_raw.empty:
        np.random.seed(42)
        df_raw = pd.DataFrame({
            "序号": range(1, 101),
            "测量值(mm)": np.random.normal(10.5, 0.2, 100).round(3),
            "偏移趋势": np.linspace(0, 0.5, 100) + np.random.normal(0, 0.05, 100)
        })
        st.info("💡 当前使用内置演示数据。")

    st.subheader("📝 在线编辑器")
    df_active = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True)

# 初始化全局变量
report_content = ""
final_fig = None

# =========================================
# --- 3. 分析模块 A：正态分布分析 ---
# =========================================
if analysis_type == "📊 正态分布分析":
    st.title("正态分布统计与置信区间深度分析")
    
    target_col = st.sidebar.selectbox("选择分析列", df_active.columns)
    valid_data = pd.to_numeric(df_active[target_col], errors='coerce').dropna()
    
    if not valid_data.empty:
        st.sidebar.subheader("📐 数值范围与组距")
        c1, c2 = st.sidebar.columns(2)
        # 【需求】数值范围直接输入
        xmin = c1.number_input("起点数值", value=float(valid_data.min()))
        xmax = c2.number_input("终点数值", value=float(valid_data.max()))
        
        bw = st.sidebar.number_input("设置组距", value=(xmax-xmin)/15 if xmax!=xmin else 0.1, step=0.01)
        # 【需求】置信区间范围 0-100%
        conf_percent = st.sidebar.slider("置信水平 (%)", 0.0, 100.0, 95.0)
        conf_val = conf_percent / 100.0

        # 数据切片
        subset = valid_data[(valid_data >= xmin) & (valid_data <= xmax)]
        
        if not subset.empty:
            mean_v, std_v = subset.mean(), subset.std()
            range_v = subset.max() - subset.min()
            
            # 【需求核心】计算置信区间的数值边界
            if 0 < conf_val < 1:
                # 使用 t 分布计算均值的置信区间
                ci_low, ci_high = stats.t.interval(conf_val, len(subset)-1, loc=mean_v, scale=stats.sem(subset))
            elif conf_val >= 1:
                ci_low, ci_high = subset.min(), subset.max()
            else:
                ci_low, ci_high = mean_v, mean_v

            # 指标卡展示
            m = st.columns(4)
            m[0].metric("有效样本量", len(subset))
            m[1].metric("范围均值", f"{mean_v:.4f}")
            m[2].metric("范围极差", f"{range_v:.4f}")
            # 【新增显示】置信区间具体数值范围
            m[3].metric(f"{conf_percent}% 置信区间", f"[{ci_low:.3f}, {ci_high:.3f}]")

            # 绘图逻辑
            final_fig = go.Figure()
            bins = np.arange(xmin, xmax + bw, bw)
            counts, _ = np.histogram(subset, bins=bins)
            props = counts / len(subset) # 占比分析
            
            # 【需求】柱状图标注占比
            final_fig.add_trace(go.Bar(
                x=bins[:-1] + bw/2, y=props,
                text=[f"{(p*100):.1f}%" for p in props],
                textposition='outside', name="频率占比", marker_color='#2c3e50'
            ))
            
            # 正态曲线拟合
            xl = np.linspace(xmin, xmax, 200)
            yl = stats.norm.pdf(xl, mean_v, std_v) * bw
            final_fig.add_trace(go.Scatter(x=xl, y=yl, mode='lines', name="正态拟合", line=dict(color='red', width=3)))
            
            # 图表上绘制置信区间阴影
            if 0 < conf_val < 1:
                final_fig.add_vrect(x0=max(ci_low, xmin), x1=min(ci_high, xmax), fillcolor="rgba(46, 204, 113, 0.15)", line_width=0, annotation_text="置信范围")

            final_fig.update_layout(template="simple_white", height=500, xaxis_title=target_col, yaxis_title="占比频率")
            st.plotly_chart(final_fig, use_container_width=True)

            # 生成报告文本
            report_content = f"""【正态分布分析报告】
------------------------------------
生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
分析目标列: {target_col}
用户设定范围: {xmin} 至 {xmax}
有效样本量: {len(subset)}

统计摘要:
- 均值 (Mean): {mean_v:.6f}
- 极差 (Range): {range_v:.6f}
- 标准差 (Std): {std_v:.6f}
- 置信水平: {conf_percent}%
- 置信区间数值范围: [{ci_low:.6f} , {ci_high:.6f}]

(报告由数据专家系统自动生成)
"""
        else:
            st.warning("所选范围内无有效数据点。")

# =========================================
# --- 4. 分析模块 B：趋势回归分析 ---
# =========================================
else:
    st.title("趋势折线与多列线性回归分析")
    
    # 【需求】自由选择横纵坐标列
    col_x = st.sidebar.selectbox("选择 X 轴 (自变量)", df_active.columns, index=0)
    col_y = st.sidebar.selectbox("选择 Y 轴 (因变量)", df_active.columns, index=min(1, len(df_active.columns)-1))
    
    reg_df = df_active[[col_x, col_y]].apply(pd.to_numeric, errors='coerce').dropna()
    
    if len(reg_df) >= 2:
        st.sidebar.subheader("📐 坐标轴数值限制")
        cx1, cx2 = st.sidebar.columns(2)
        xmin_r = cx1.number_input("X 起点", value=float(reg_df[col_x].min()))
        xmax_r = cx2.number_input("X 终点", value=float(reg_df[col_x].max()))
        
        f_reg = reg_df[(reg_df[col_x] >= xmin_r) & (reg_df[col_x] <= xmax_r)]
        
        if not f_reg.empty:
            slope, intercept, r_v, p_v, std_e = stats.linregress(f_reg[col_x], f_reg[col_y])
            r_sq = r_v**2
            
            k = st.columns(4)
            k[0].metric("判定系数 $R^2$", f"{r_sq:.4f}")
            k[1].metric("相关系数 $r$", f"{r_v:.4f}")
            k[2].metric("回归斜率", f"{slope:.4f}")
            k[3].metric("显著性 P", f"{p_v:.4e}")

            final_fig = go.Figure()
            final_fig.add_trace(go.Scatter(x=f_reg[col_x], y=f_reg[col_y], mode='lines+markers', name="实测趋势"))
            # 拟合线
            rx = np.array([xmin_r, xmax_r])
            ry = slope * rx + intercept
            final_fig.add_trace(go.Scatter(x=rx, y=ry, name="回归拟合线", line=dict(dash='dash', color='red')))
            
            final_fig.update_layout(template="simple_white", height=500, xaxis_title=col_x, yaxis_title=col_y)
            st.plotly_chart(final_fig, use_container_width=True)
            st.success(f"📈 回归方程: $y = {slope:.4f}x + {intercept:.4f}$")

            report_content = f"""【趋势回归分析报告】
------------------------------------
变量关系: {col_x} (X) vs {col_y} (Y)
数据点数: {len(f_reg)}
判定系数 R^2: {r_sq:.6f}
线性方程: Y = {slope:.4f}X + {intercept:.4f}
"""
        else:
            st.error("范围内无有效点。")

# =========================================
# --- 5. 导出与预览区 ---
# =========================================
st.divider()
st.subheader("📥 结果导出中心")
dcols = st.columns(3)

with dcols[0]:
    st.download_button("📑 下载分析报告 (TXT)", report_content, f"Report_{datetime.datetime.now().strftime('%m%d%H%M')}.txt", use_container_width=True)

with dcols[1]:
    if final_fig:
        html_buf = io.StringIO()
        final_fig.write_html(html_buf, include_plotlyjs='cdn')
        st.download_button("🖼️ 下载交互式图表 (HTML)", html_buf.getvalue(), "Chart.html", "text/html", use_container_width=True)

with dcols[2]:
    st.download_button("📊 下载清洗后的数据 (CSV)", df_active.to_csv(index=False).encode('utf-8'), "Clean_Data.csv", "text/csv", use_container_width=True)

if report_content:
    with st.expander("📄 报告内容实时预览"):
        st.code(report_content, language="markdown")
