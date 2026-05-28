"""
品类库存周转分析 - 独立页面
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from modules.inventory_analysis import run_inventory_analysis

# 页面标题/icon 由 datall.py 的 st.set_page_config 统一设置
# 根据 session_state 选择数据源
data_source = st.session_state.get("data_source_radio", "📁 CSV（本地文件）")
use_warehouse = (data_source == "🗄️ MySQL 数仓")

if use_warehouse:
    from dw.ads.dw_loader import load_from_warehouse
    st.caption("数据源: MySQL 数仓 DWS/DWD 层")
    with st.spinner("正在从数仓加载数据..."):
        data_dict = load_from_warehouse()
else:
    from modules.data_loader import load_and_preprocess
    st.caption("数据源: 本地 CSV 文件（稳定版）")
    with st.spinner("正在从本地 CSV 加载数据..."):
        data_dict = load_and_preprocess()

st.title("📊 品类库存周转分析")
run_inventory_analysis(data_dict)
