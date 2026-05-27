"""
Olist 电商平台供应链数据分析 - Streamlit 交互看板

主页面：项目概览 & 数据总览
"""
import sys
from pathlib import Path
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from modules.delivery_analysis import run_delivery_analysis
from modules.inventory_analysis import run_inventory_analysis
from modules.logistics_analysis import run_logistics_analysis
from modules.sales_analysis import run_sales_analysis
from dw.ads.dw_loader import load_from_warehouse
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="Olist 供应链数据分析",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #374151;
        border-bottom: 2px solid #3366CC;
        padding-bottom: 0.3rem;
        margin-top: 1.5rem;
    }
    .stMetric {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .stMetric label {
        font-size: 0.85rem !important;
        color: #64748b !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.image("https://img.icons8.com/color/96/warehouse-1.png", width=80)
    st.markdown("## 供应链数据分析")
    st.markdown("---")

    st.markdown("### 导航")
    st.markdown("""
    - 📋 **项目概览** (当前页)
    - 📦 **供应商交付时效**
    - 📊 **品类库存周转**
    - 🚚 **物流满意度归因**
    - 📈 **销售趋势分析**
    """)

    st.markdown("---")
    st.markdown("### 数据来源")
    st.markdown("[Olist Brazilian E-commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)")
    st.markdown("*Kaggle 公开数据集*")

    st.markdown("---")
    st.markdown("### 数据架构")
    st.markdown("""
    **数仓分层 (ODS → DWD → DWS → ADS)**
    - ODS: 原始 CSV 入库 MySQL
    - DWD: 订单宽表 + 4 张维度表
    - DWS: 6 张日/周聚合汇总表
    - ADS: Streamlit 交互看板
    """)

    st.markdown("---")
    st.markdown("### 关于项目")
    st.markdown("""
    本项目面向**供应链数据分析**岗位需求，涵盖：
    - 供应商交付时效监控
    - 品类库存周转效率
    - 物流满意度归因
    - 销售趋势预测

    技术栈：Python + MySQL + Streamlit + Plotly
    """)

    st.markdown("---")
    st.caption("Made with ❤️ by Allen | 2026")


# --- 主页面内容 ---

st.markdown('<p class="main-header">📦 Olist 巴西电商平台 — 供应链数据分析</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">供应商交付时效 | 品类库存周转 | 物流满意度归因 | 销售趋势分析 | 数仓分层架构</p>',
            unsafe_allow_html=True)

# --- 数据加载 ---
with st.spinner("正在从数仓 DWS 层加载数据..."):
    try:
        data_dict = load_from_warehouse()
        st.success("✅ 数仓数据加载完成！(ODS → DWD → DWS → ADS)")
    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        st.info("""
        ### 请先运行数仓 ETL

        ```bash
        py dw/run_all.py
        ```

        这将依次执行：
        1. ODS 层：将 CSV 原样导入 MySQL
        2. DWD 层：清洗数据，构建订单宽表 + 维度表
        3. DWS 层：计算日/周聚合汇总表

        然后重新启动 Streamlit。
        """)
        st.stop()

# --- 数据概览 ---
st.markdown('<p class="section-title">📊 数据概览（来自 DWS 汇总表）</p>', unsafe_allow_html=True)

# 从 DWS 表获取 KPI
dm = data_dict.get('daily_metrics', pd.DataFrame())
if not dm.empty:
    total_orders = int(dm['total_orders'].sum())
    total_gmv = dm['total_gmv'].sum()
    avg_delivery = dm['avg_delivery_days'].mean()
    delay_rate = dm['delay_rate'].mean() * 100
    unique_customers = int(dm['unique_customers'].sum())
    unique_sellers = int(dm['unique_sellers'].sum())
    date_range = f"{dm['purchase_date'].min().strftime('%Y-%m')} ~ {dm['purchase_date'].max().strftime('%Y-%m')}"
else:
    total_orders = total_gmv = avg_delivery = delay_rate = unique_customers = unique_sellers = 0
    date_range = "N/A"

# KPI 卡片行
cols = st.columns(6)
kpi_items = [
    ("总订单数", f"{total_orders:,}", "📦"),
    ("总GMV", f"¥{total_gmv:,.0f}", "💰"),
    ("客户数", f"{unique_customers:,}", "👥"),
    ("活跃卖家", f"{unique_sellers:,}", "🏪"),
    ("平均交付(天)", f"{avg_delivery:.1f}", "⏱️"),
    ("延迟率", f"{delay_rate:.1f}%", "⚠️"),
]
for col, (label, value, icon) in zip(cols, kpi_items):
    col.metric(f"{icon} {label}", value)

st.caption(f"数据时间范围: {date_range}")

st.markdown("---")

# --- 快速预览 tab ---
st.markdown('<p class="section-title">🔍 快速预览</p>', unsafe_allow_html=True)

tabs = st.tabs(["📦 交付时效", "📊 库存周转", "🚚 满意度", "📈 销售趋势"])

# 在每个 tab 中运行对应的分析模块
with tabs[0]:
    run_delivery_analysis(data_dict)

with tabs[1]:
    run_inventory_analysis(data_dict)

with tabs[2]:
    run_logistics_analysis(data_dict)

with tabs[3]:
    run_sales_analysis(data_dict)
