"""
Olist 电商平台供应链数据分析 - Streamlit 交互看板

启动: streamlit run datall.py

架构:
  - 数据总览页: 全局 KPI + 各模块关键图表摘要
  - 子页面: 每个分析模块的完整详细视图
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd

# ============================================================
# 页面配置（全局生效，子页面的 set_page_config 会被忽略）
# ============================================================
st.set_page_config(
    page_title="数据总览 · Olist 供应链分析",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 自定义 CSS
# ============================================================
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
    .nav-hint {
        font-size: 0.9rem;
        color: #6b7280;
        padding: 0.5rem 0;
        border-top: 1px solid #e5e7eb;
        margin-top: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 侧边栏（所有页面共享，出现在导航下方）
# ============================================================
with st.sidebar:
    st.markdown("### 数据源")
    data_source = st.radio(
        "加载方式",
        ["📁 CSV（本地文件）", "🗄️ MySQL 数仓"],
        index=0,
        key="data_source_radio",
        help="CSV = 稳定版，直接可用 | 数仓 = 需先运行 dw/run_all.py 构建"
    )

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
    st.markdown("### 关于")
    st.markdown("[Olist Brazilian E-commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)")
    st.caption("Kaggle 公开数据集")
    st.caption("Python + MySQL + Streamlit + Plotly")
    st.caption("Made with ❤️ by Allen | 2026")


# ============================================================
# 数据总览页面内容
# ============================================================
def overview():
    """
    数据总览页：全局 KPI + 各模块关键图表摘要
    完整分析请点击左侧导航进入子页面
    """
    from dw.ads.dw_loader import load_from_warehouse

    st.markdown(
        '<p class="main-header">📦 Olist 巴西电商 — 供应链数据分析</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">供应商交付时效 | 品类库存周转 | 物流满意度归因 | 销售趋势分析</p>',
        unsafe_allow_html=True,
    )

    # --- 数据加载 ---
    use_warehouse = (data_source == "🗄️ MySQL 数仓")

    with st.spinner("正在加载数据..."):
        if use_warehouse:
            try:
                data_dict = load_from_warehouse()
                st.success("✅ 数仓数据加载完成 (ODS → DWD → DWS → ADS)")
            except Exception as e:
                st.error(f"❌ 数仓加载失败: {e}")
                st.info("请先运行 `py dw/run_all.py` 构建数仓，然后重启 Streamlit。")
                st.stop()
        else:
            from modules.data_loader import load_and_preprocess

            data_dict = load_and_preprocess()
            st.success("✅ CSV 数据加载完成")

    # --- 全局 KPI 卡片 ---
    source_label = "DWS 汇总表" if use_warehouse else "CSV 本地文件"
    st.markdown(f'<p class="section-title">📊 数据概览（{source_label}）</p>', unsafe_allow_html=True)

    delivered_df = data_dict.get("delivered", pd.DataFrame())
    monthly = data_dict.get("monthly_summary", pd.DataFrame())

    if not delivered_df.empty:
        total_orders = delivered_df["order_id"].nunique()
        total_gmv = delivered_df["price"].sum()
        avg_delivery = delivered_df["delivery_time_days"].mean()
        delay_rate = delivered_df["is_delayed"].mean() * 100
        unique_customers = delivered_df["customer_unique_id"].nunique()
        unique_sellers = (
            delivered_df["seller_id"].nunique()
            if "seller_id" in delivered_df.columns
            else 0
        )
        date_min = delivered_df["purchase_date"].min()
        date_max = delivered_df["purchase_date"].max()
        date_range = f"{date_min.strftime('%Y-%m')} ~ {date_max.strftime('%Y-%m')}"
    elif not monthly.empty:
        total_orders = int(monthly["total_orders"].sum())
        total_gmv = monthly["total_revenue"].sum()
        avg_delivery = monthly["avg_delivery_days"].mean()
        delay_rate = monthly["delay_rate"].mean()
        unique_customers = (
            int(monthly["unique_customers"].sum())
            if "unique_customers" in monthly.columns
            else 0
        )
        unique_sellers = 0
        date_range = "N/A"
    else:
        total_orders = total_gmv = avg_delivery = delay_rate = unique_customers = unique_sellers = 0
        date_range = "N/A"

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

    # --- 模块关键图表摘要 ---
    st.markdown('<p class="section-title">🔍 各模块关键指标</p>', unsafe_allow_html=True)
    st.caption("点击左侧导航栏查看各模块完整分析（含全部图表和数据表）")

    tabs = st.tabs(["📦 交付时效", "📊 库存周转", "🚚 满意度", "📈 销售趋势"])

    # ---- Tab 1: 交付时效 ----
    with tabs[0]:
        from modules.delivery_analysis import (
            delivery_kpi_cards,
            plot_delivery_distribution,
            plot_monthly_delivery_trend,
            plot_delivery_by_category,
        )

        delivery_kpi_cards(data_dict)
        plot_delivery_distribution(data_dict)
        col1, col2 = st.columns(2)
        with col1:
            plot_monthly_delivery_trend(data_dict)
        with col2:
            plot_delivery_by_category(data_dict)
        st.markdown(
            '<p class="nav-hint">📋 点击左侧「📦 供应商交付时效」查看完整分析（各州对比、热力图等）</p>',
            unsafe_allow_html=True,
        )

    # ---- Tab 2: 库存周转 ----
    with tabs[1]:
        from modules.inventory_analysis import (
            inventory_kpi_cards,
            plot_category_treemap,
            plot_category_concentration,
            plot_sales_velocity,
        )

        inventory_kpi_cards(data_dict)
        plot_category_treemap(data_dict)
        col1, col2 = st.columns(2)
        with col1:
            plot_category_concentration(data_dict)
        with col2:
            plot_sales_velocity(data_dict)
        st.markdown(
            '<p class="nav-hint">📋 点击左侧「📊 品类库存周转」查看完整分析（卖家网络、月度动态、数据明细等）</p>',
            unsafe_allow_html=True,
        )

    # ---- Tab 3: 满意度 ----
    with tabs[2]:
        from modules.logistics_analysis import (
            satisfaction_kpi_cards,
            plot_delivery_vs_score,
            plot_score_distribution,
            plot_correlation_heatmap,
        )

        satisfaction_kpi_cards(data_dict)
        col1, col2 = st.columns(2)
        with col1:
            plot_delivery_vs_score(data_dict)
        with col2:
            plot_score_distribution(data_dict)
        plot_correlation_heatmap(data_dict)
        st.markdown(
            '<p class="nav-hint">📋 点击左侧「🚚 物流满意度归因」查看完整分析（各州满意度、因素分解等）</p>',
            unsafe_allow_html=True,
        )

    # ---- Tab 4: 销售趋势 ----
    with tabs[3]:
        from modules.sales_analysis import (
            sales_kpi_cards,
            plot_revenue_trend,
            plot_category_trend,
            plot_rfm_analysis,
        )

        sales_kpi_cards(data_dict)
        plot_revenue_trend(data_dict)
        col1, col2 = st.columns(2)
        with col1:
            plot_category_trend(data_dict)
        with col2:
            plot_rfm_analysis(data_dict)
        st.markdown(
            '<p class="nav-hint">📋 点击左侧「📈 销售趋势分析」查看完整分析（季节性、地理分布、漏斗等）</p>',
            unsafe_allow_html=True,
        )


# ============================================================
# 页面导航（st.navigation 实现自定义标题 + 集中路由）
# ============================================================
overview_page = st.Page(overview, title="数据总览", icon="🏠", default=True)
delivery_page = st.Page("pages/1_📦_供应商交付时效.py")
inventory_page = st.Page("pages/2_📊_品类库存周转.py")
logistics_page = st.Page("pages/3_🚚_物流满意度归因.py")
sales_page = st.Page("pages/4_📈_销售趋势分析.py")
sql_page = st.Page("pages/5_💾_SQL分析对比.py")

pg = st.navigation(
    [overview_page, delivery_page, inventory_page, logistics_page, sales_page, sql_page],
    position="sidebar",
)
pg.run()
