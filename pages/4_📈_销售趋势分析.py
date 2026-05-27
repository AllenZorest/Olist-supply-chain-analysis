"""
销售趋势分析 - 独立页面
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from modules.sales_analysis import run_sales_analysis
from dw.ads.dw_loader import load_from_warehouse

st.set_page_config(
    page_title="销售趋势分析",
    page_icon="📈",
    layout="wide",
)

st.title("📈 销售趋势分析")
st.caption("数据源: MySQL 数仓 DWS/DWD 层")

with st.spinner("从数仓加载数据中..."):
    data_dict = load_from_warehouse()

run_sales_analysis(data_dict)
