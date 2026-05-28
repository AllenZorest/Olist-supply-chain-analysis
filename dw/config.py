"""
数仓配置文件
统一管理 MySQL 连接信息
"""
from pathlib import Path

# ========================================
# MySQL 连接配置
# ========================================
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',        # 修改为你的 MySQL 密码
    'database': 'olist_supply_chain',
    'charset': 'utf8mb4',
}

# ========================================
# 项目路径
# ========================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"

# ========================================
# CSV → 表名映射
# ========================================
CSV_TABLE_MAP = {
    'customers':                     'olist_customers_dataset.csv',
    'sellers':                       'olist_sellers_dataset.csv',
    'products':                      'olist_products_dataset.csv',
    'product_category_translation':  'product_category_name_translation.csv',
    'orders':                        'olist_orders_dataset.csv',
    'order_items':                   'olist_order_items_dataset.csv',
    'order_payments':                'olist_order_payments_dataset.csv',
    'order_reviews':                 'olist_order_reviews_dataset.csv',
}
