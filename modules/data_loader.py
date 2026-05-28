"""
Olist 巴西电商数据集 数据加载与预处理模块

支持两种方式加载数据：
1. 自动从 Kaggle 下载（需要 kagglehub）
2. 从本地 data/ 目录读取 CSV 文件

数据来源：https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
"""
import os
import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

# 数据目录
DATA_DIR = Path(__file__).parent.parent / "data"


def download_from_kaggle():
    """
    使用 kagglehub 自动下载 Olist 数据集
    返回数据集所在目录路径
    """
    try:
        import kagglehub
        path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
        print(f"数据集已下载到: {path}")
        return Path(path)
    except Exception as e:
        print(f"Kaggle 下载失败: {e}")
        return None


def load_raw_data(data_path=None):
    """
    加载所有原始 CSV 文件

    参数:
        data_path: 数据目录路径，若为 None 则自动检测
    返回:
        dict: 包含所有数据表的字典
    """
    if data_path is None:
        # 优先使用本地 data/ 目录
        if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
            data_path = DATA_DIR
        else:
            # 尝试从 Kaggle 下载
            data_path = download_from_kaggle()

    if data_path is None:
        raise FileNotFoundError(
            "找不到数据集！请将 CSV 文件放入 data/ 目录，"
            "或运行: pip install kagglehub && python -c \"import kagglehub; kagglehub.dataset_download('olistbr/brazilian-ecommerce')\""
        )

    csv_files = {
        'orders': 'olist_orders_dataset.csv',
        'order_items': 'olist_order_items_dataset.csv',
        'order_payments': 'olist_order_payments_dataset.csv',
        'order_reviews': 'olist_order_reviews_dataset.csv',
        'products': 'olist_products_dataset.csv',
        'sellers': 'olist_sellers_dataset.csv',
        'customers': 'olist_customers_dataset.csv',
        'category_translation': 'product_category_name_translation.csv',
    }

    data = {}
    for name, filename in csv_files.items():
        filepath = data_path / filename
        if filepath.exists():
            data[name] = pd.read_csv(filepath)
            print(f"已加载: {filename} ({len(data[name])} 行)")
        else:
            print(f"警告: 找不到 {filename}")

    return data


@st.cache_data(ttl=3600)
def load_and_preprocess():
    """
    加载数据并执行完整的预处理流水线
    返回预处理后的合并数据集和各种分析用中间表
    """
    # 加载原始数据
    raw = load_raw_data()

    # ---- 日期字段转换 ----
    date_cols = [
        'order_purchase_timestamp', 'order_approved_at',
        'order_delivered_carrier_date', 'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    for col in date_cols:
        if col in raw['orders'].columns:
            raw['orders'][col] = pd.to_datetime(raw['orders'][col])

    if 'shipping_limit_date' in raw['order_items'].columns:
        raw['order_items']['shipping_limit_date'] = pd.to_datetime(
            raw['order_items']['shipping_limit_date']
        )

    if 'review_creation_date' in raw['order_reviews'].columns:
        raw['order_reviews']['review_creation_date'] = pd.to_datetime(
            raw['order_reviews']['review_creation_date']
        )
    if 'review_answer_timestamp' in raw['order_reviews'].columns:
        raw['order_reviews']['review_answer_timestamp'] = pd.to_datetime(
            raw['order_reviews']['review_answer_timestamp']
        )

    # ---- 合并主数据 ----
    # orders + order_items + products + sellers + customers
    df = raw['orders'].merge(
        raw['order_items'], on='order_id', how='left'
    ).merge(
        raw['products'], on='product_id', how='left'
    ).merge(
        raw['sellers'], on='seller_id', how='left'
    ).merge(
        raw['customers'], on='customer_id', how='left'
    )

    # 合并品类翻译
    if 'category_translation' in raw and raw['category_translation'] is not None:
        df = df.merge(
            raw['category_translation'],
            on='product_category_name', how='left'
        )
        # 优先使用英文品类名
        df['category_name'] = df['product_category_name_english'].fillna(
            df['product_category_name']
        )
    else:
        df['category_name'] = df['product_category_name']

    # ---- 特征工程 ----

    # 1. 交付时效特征
    df['delivery_time_days'] = (
        df['order_delivered_customer_date'] - df['order_purchase_timestamp']
    ).dt.days

    df['estimated_delivery_days'] = (
        df['order_estimated_delivery_date'] - df['order_purchase_timestamp']
    ).dt.days

    df['carrier_time_days'] = (
        df['order_delivered_customer_date'] - df['order_delivered_carrier_date']
    ).dt.days

    # 2. 是否延迟交付
    df['is_delayed'] = (
        df['order_delivered_customer_date'] > df['order_estimated_delivery_date']
    )

    df['delay_days'] = (
        df['order_delivered_customer_date'] - df['order_estimated_delivery_date']
    ).dt.days
    df.loc[df['delay_days'] < 0, 'delay_days'] = 0

    # 3. 时间维度拆解
    df['purchase_year'] = df['order_purchase_timestamp'].dt.year
    df['purchase_month'] = df['order_purchase_timestamp'].dt.month
    df['purchase_dayofweek'] = df['order_purchase_timestamp'].dt.dayofweek
    df['purchase_week'] = df['order_purchase_timestamp'].dt.isocalendar().week.astype(int)
    df['purchase_year_month'] = df['order_purchase_timestamp'].dt.to_period('M')

    # 4. 客户州信息
    df['customer_state_name'] = df['customer_state'].map(
        __import__('utils.helpers', fromlist=['STATE_MAP']).STATE_MAP
    )

    # 5. 仅保留已交付订单用于供应量分析
    df_delivered = df[df['order_status'] == 'delivered'].copy()

    # ---- 构建分析用聚合表 ----

    # 供应商（卖家）汇总
    seller_summary = df_delivered.groupby('seller_id').agg(
        total_orders=('order_id', 'nunique'),
        total_revenue=('price', 'sum'),
        avg_delivery_days=('delivery_time_days', 'mean'),
        delay_rate=('is_delayed', 'mean'),
        avg_freight=('freight_value', 'mean'),
        seller_city=('seller_city', 'first'),
        seller_state=('seller_state', 'first'),
    ).reset_index()
    seller_summary['delay_rate'] = (seller_summary['delay_rate'] * 100).round(1)

    # 品类汇总
    category_summary = df_delivered.groupby('category_name').agg(
        total_orders=('order_id', 'nunique'),
        total_revenue=('price', 'sum'),
        avg_price=('price', 'mean'),
        avg_delivery_days=('delivery_time_days', 'mean'),
        delay_rate=('is_delayed', 'mean'),
        unique_products=('product_id', 'nunique'),
        unique_sellers=('seller_id', 'nunique'),
    ).reset_index()
    category_summary['delay_rate'] = (category_summary['delay_rate'] * 100).round(1)

    # 月度汇总
    monthly_summary = df_delivered.groupby('purchase_year_month').agg(
        total_orders=('order_id', 'nunique'),
        total_revenue=('price', 'sum'),
        avg_delivery_days=('delivery_time_days', 'mean'),
        delay_rate=('is_delayed', 'mean'),
        unique_customers=('customer_unique_id', 'nunique'),
    ).reset_index()
    monthly_summary['delay_rate'] = (monthly_summary['delay_rate'] * 100).round(1)
    monthly_summary['purchase_year_month'] = monthly_summary['purchase_year_month'].astype(str)

    # 合并评论数据
    reviews_agg = raw['order_reviews'].groupby('order_id')['review_score'].mean().reset_index()
    df_delivered = df_delivered.merge(reviews_agg, on='order_id', how='left')

    # 统一列名：让 datall.py 两种数据源用同一套列名
    if 'order_purchase_timestamp' in df.columns and 'purchase_date' not in df.columns:
        df['purchase_date'] = df['order_purchase_timestamp']
    if 'order_purchase_timestamp' in df_delivered.columns and 'purchase_date' not in df_delivered.columns:
        df_delivered['purchase_date'] = df_delivered['order_purchase_timestamp']

    return {
        'main': df,
        'delivered': df_delivered,
        'raw': raw,
        'seller_summary': seller_summary,
        'category_summary': category_summary,
        'monthly_summary': monthly_summary,
        'reviews': raw['order_reviews'],
        'payments': raw['order_payments'],
    }


def get_data_summary(data_dict):
    """生成数据集概览信息"""
    df = data_dict['delivered']

    summary = {
        '总订单数': f"{df['order_id'].nunique():,}",
        '已交付订单': f"{df['order_id'].nunique():,}",
        '总销售额': f"R$ {df['price'].sum():,.0f}",
        '商品品类数': df['category_name'].nunique(),
        '卖家数': df['seller_id'].nunique(),
        '客户数': df['customer_unique_id'].nunique(),
        '平均交付天数': f"{df['delivery_time_days'].mean():.1f} 天",
        '延迟交付率': f"{(df['is_delayed'].mean() * 100):.1f}%",
        '数据时间范围': f"{df['order_purchase_timestamp'].min().date()} ~ {df['order_purchase_timestamp'].max().date()}",
    }

    return summary
