"""
物流满意度归因分析 - 独立页面
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from modules.data_loader import load_and_preprocess
from modules.logistics_analysis import run_logistics_analysis

st.set_page_config(
    page_title="物流满意度归因",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 物流满意度归因分析")

with st.spinner("加载数据中..."):
    data_dict = load_and_preprocess()

run_logistics_analysis(data_dict)
