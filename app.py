"""
Olist 电商平台供应链数据分析 - Streamlit 交互看板

主页面：项目概览 & 数据总览
"""
import sys
from pathlib import Path
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from modules.data_loader import load_and_preprocess, get_data_summary
from modules.delivery_analysis import run_delivery_analysis
from modules.inventory_analysis import run_inventory_analysis
from modules.logistics_analysis import run_logistics_analysis
from modules.sales_analysis import run_sales_analysis
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
    st.markdown("### 关于项目")
    st.markdown("""
    本项目面向**供应链数据分析**岗位需求，涵盖：
    - 供应商交付时效监控
    - 品类库存周转效率
    - 物流满意度归因
    - 销售趋势预测

    技术栈：Python + Streamlit + Plotly
    """)

    st.markdown("---")
    st.caption("Made with ❤️ by Allen | 2024")


# --- 主页面内容 ---

st.markdown('<p class="main-header">📦 Olist 巴西电商平台 — 供应链数据分析</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">供应商交付时效 | 品类库存周转 | 物流满意度归因 | 销售趋势分析</p>',
            unsafe_allow_html=True)

# --- 数据加载 ---
with st.spinner("正在加载和预处理数据... 首次运行需要下载数据集，请耐心等待"):
    try:
        data_dict = load_and_preprocess()
        st.success("✅ 数据加载完成！")
    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        st.info("""
        ### 如何获取数据？

        请确保数据集CSV文件放在 `data/` 目录下，或使用以下命令自动下载：

        ```bash
        pip install kagglehub
        python -c "import kagglehub; kagglehub.dataset_download('olistbr/brazilian-ecommerce')"
        ```

        也可以在 Kaggle 手动下载：[Olist Brazilian E-commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
        """)
        st.stop()

# --- 数据概览 ---
st.markdown('<p class="section-title">📊 数据概览</p>', unsafe_allow_html=True)

summary = get_data_summary(data_dict)

# KPI 卡片行 - 第一行
cols = st.columns(6)
kpi_items = [
    ("总订单数", summary['总订单数'], "📦"),
    ("已交付订单", summary['已交付订单'], "✅"),
    ("总销售额", summary['总销售额'], "💰"),
    ("商品品类数", str(summary['商品品类数']), "🏷️"),
    ("卖家数", str(summary['卖家数']), "🏪"),
    ("客户数", str(summary['客户数']), "👥"),
]
for col, (label, value, icon) in zip(cols, kpi_items):
    col.metric(f"{icon} {label}", value)

# KPI 卡片行 - 第二行
st.markdown("")
cols = st.columns(4)
kpi_items2 = [
    ("平均交付天数", summary['平均交付天数'], "⏱️"),
    ("延迟交付率", summary['延迟交付率'], "⚠️"),
    ("数据时间范围", summary['数据时间范围'], "📅"),
]
for col, (label, value, icon) in zip(cols[:3], kpi_items2):
    col.metric(f"{icon} {label}", value)

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
