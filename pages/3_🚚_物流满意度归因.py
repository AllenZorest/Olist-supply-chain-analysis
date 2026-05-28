"""
物流满意度归因分析 - 独立页面
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from modules.logistics_analysis import run_logistics_analysis

# 页面标题/icon 由 datall.py 的 st.set_page_config 统一设置
# 从 session_state 读取数据源选择（由 datall.py 侧边栏设置）
data_source = st.session_state.get("data_source_radio", "📁 CSV（本地文件）")
use_warehouse = (data_source == "🗄️ MySQL 数仓")

st.title("🚚 物流满意度归因分析")
st.caption(f"数据源: {'MySQL 数仓 DWS/DWD 层' if use_warehouse else 'CSV 本地文件（稳定版）'}")

with st.spinner("正在加载数据..."):
    if use_warehouse:
        from dw.ads.dw_loader import load_from_warehouse
        try:
            data_dict = load_from_warehouse()
        except Exception as e:
            st.error(f"❌ 数仓加载失败: {e}")
            st.info("请先运行 `py dw/run_all.py` 构建数仓")
            st.stop()
    else:
        from modules.data_loader import load_and_preprocess
        data_dict = load_and_preprocess()

run_logistics_analysis(data_dict)
