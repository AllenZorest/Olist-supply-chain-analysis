"""
数据加载器（数仓版本）
=====================
从 MySQL 数仓 DWS/DWD 层读取数据，
返回与旧版 CSV 加载器兼容的 data_dict 结构。

这样 Streamlit 页面无需大规模重写，
只需将 import 从 data_loader 改为 dw_loader 即可。
"""
import pandas as pd
import pymysql
import streamlit as st
from dw.config import MYSQL_CONFIG


@st.cache_data(ttl=3600)
def load_from_warehouse():
    """
    从 MySQL 数仓加载数据，返回与旧版兼容的 data_dict。

    当 MySQL 不可用时，回退到 CSV 加载（旧版 data_loader）。
    """
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        conn.ping()
    except Exception:
        st.warning("⚠ MySQL 连接失败，回退到 CSV 本地加载模式")
        from modules.data_loader import load_and_preprocess
        return load_and_preprocess()

    data_dict = {}

    # ---- DWD 层: 订单明细宽表（核心） ----
    df = pd.read_sql("""
        SELECT * FROM dwd_order_detail
        WHERE purchase_date >= '2016-09-01'
    """, conn)

    # 日期字段转换
    for col in ['purchase_date', 'delivered_date', 'estimated_date',
                'purchase_timestamp', 'delivered_timestamp']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    # 派生 Period 列（兼容旧版分析函数）
    df['purchase_year_month'] = df['purchase_date'].dt.to_period('M').astype(str)

    data_dict['delivered'] = df

    # ---- DWS 层: 聚合表 ----
    data_dict['daily_metrics'] = pd.read_sql(
        "SELECT * FROM dws_daily_metrics ORDER BY purchase_date", conn)
    data_dict['daily_metrics']['purchase_date'] = pd.to_datetime(data_dict['daily_metrics']['purchase_date'])

    data_dict['weekly_metrics'] = pd.read_sql(
        "SELECT * FROM dws_weekly_metrics ORDER BY week_start_date", conn)

    data_dict['category_summary'] = pd.read_sql(
        "SELECT * FROM dws_category_summary ORDER BY total_revenue DESC", conn)

    data_dict['state_summary'] = pd.read_sql(
        "SELECT * FROM dws_state_summary ORDER BY total_gmv DESC", conn)

    # ---- 客户RFM（DWD 实时计算） ----
    data_dict['rfm'] = pd.read_sql("""
        SELECT
            customer_unique_id,
            DATEDIFF('2018-10-01', MAX(purchase_date)) AS recency,
            COUNT(DISTINCT order_id) AS frequency,
            SUM(payment_value) AS monetary
        FROM dwd_order_detail
        WHERE customer_unique_id IS NOT NULL
        GROUP BY customer_unique_id
    """, conn)

    conn.close()

    return data_dict
