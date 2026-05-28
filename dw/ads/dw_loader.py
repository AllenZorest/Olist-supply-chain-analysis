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
    # 关联 dim_products 获取产品尺寸字段（库存分析模块需要）
    df = pd.read_sql("""
        SELECT
            d.*,
            p.product_length_cm,
            p.product_height_cm,
            p.product_width_cm,
            p.product_weight_g
        FROM dwd_order_detail d
        LEFT JOIN dim_products p ON d.product_id = p.product_id
        WHERE d.purchase_date >= '2016-09-01'
    """, conn)

    # 日期字段转换
    for col in ['purchase_date', 'delivered_date', 'estimated_date',
                'purchase_timestamp', 'delivered_timestamp']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])

    # 兼容旧模块列名（旧 CSV 用 delivery_time_days，数仓用 delivery_days）
    df.rename(columns={'delivery_days': 'delivery_time_days'}, inplace=True)

    # 类型兼容：MySQL TINYINT → bool（旧 CSV 加载器直接给 bool）
    if 'is_delayed' in df.columns:
        df['is_delayed'] = df['is_delayed'].astype(bool)

    # 兼容旧模块列名：purchase_timestamp → order_purchase_timestamp
    if 'purchase_timestamp' in df.columns and 'order_purchase_timestamp' not in df.columns:
        df['order_purchase_timestamp'] = df['purchase_timestamp']

    # 兼容旧模块列名：delivered_timestamp → order_delivered_customer_date
    if 'delivered_timestamp' in df.columns and 'order_delivered_customer_date' not in df.columns:
        df['order_delivered_customer_date'] = df['delivered_timestamp']

    # 兼容旧模块列名：estimated_date → order_estimated_delivery_date
    if 'estimated_date' in df.columns and 'order_estimated_delivery_date' not in df.columns:
        df['order_estimated_delivery_date'] = pd.to_datetime(df['estimated_date'])

    # 派生时间维度列（兼容旧版分析函数）
    if 'purchase_date' in df.columns:
        df['purchase_year']      = df['purchase_date'].dt.year
        df['purchase_month']     = df['purchase_date'].dt.month
        df['purchase_dayofweek'] = df['purchase_date'].dt.dayofweek
        df['purchase_week']      = df['purchase_date'].dt.isocalendar().week.astype(int)
        df['purchase_year_month'] = df['purchase_date'].dt.to_period('M').astype(str)

    data_dict['delivered'] = df

    # 兼容 sales_analysis 的订单漏斗图（需要 data_dict['raw']['orders']）
    data_dict['raw'] = {
        'orders': df[['order_id', 'order_status']].drop_duplicates('order_id')
    }

    # 月度汇总（兼容旧模块的 monthly_summary）
    monthly = df.groupby('purchase_year_month').agg(
        total_orders=('order_id', 'nunique'),
        total_revenue=('price', 'sum'),
        avg_delivery_days=('delivery_time_days', 'mean'),
        delay_rate=('is_delayed', 'mean'),
        unique_customers=('customer_unique_id', 'nunique'),
    ).reset_index()
    monthly['delay_rate'] = (monthly['delay_rate'] * 100).round(1)
    monthly['purchase_year_month'] = monthly['purchase_year_month'].astype(str)
    data_dict['monthly_summary'] = monthly

    # ---- DWS 层: 聚合表 ----
    data_dict['daily_metrics'] = pd.read_sql(
        "SELECT * FROM dws_daily_metrics ORDER BY purchase_date", conn)
    data_dict['daily_metrics']['purchase_date'] = pd.to_datetime(data_dict['daily_metrics']['purchase_date'])

    data_dict['weekly_metrics'] = pd.read_sql(
        "SELECT * FROM dws_weekly_metrics ORDER BY week_start_date", conn)

    data_dict['category_summary'] = pd.read_sql(
        "SELECT * FROM dws_category_summary ORDER BY total_revenue DESC", conn)

    # delay_rate 转百分比（DWS 存小数如 0.085，CSV 版本存 8.5）
    data_dict['category_summary']['delay_rate'] = (
        data_dict['category_summary']['delay_rate'] * 100
    ).round(1)

    # DWS 表中没有 unique_products 字段，从 delivered 实时计算并合并
    prod_counts = df.groupby('category_name')['product_id'].nunique().reset_index()
    prod_counts.columns = ['category_name', 'unique_products']
    data_dict['category_summary'] = data_dict['category_summary'].merge(
        prod_counts, on='category_name', how='left'
    )
    data_dict['category_summary']['unique_products'] = (
        data_dict['category_summary']['unique_products'].fillna(0).astype(int)
    )

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
