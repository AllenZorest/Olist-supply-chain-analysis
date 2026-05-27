"""
ADS 层 — Streamlit 看板数据查询模块
=====================================
从 DWS/DWD 表读取聚合数据，返回 Pandas DataFrame
所有查询方法均对应一个前端页面的图表

依赖: pymysql, pandas
"""
import pandas as pd
import pymysql
from dw.config import MYSQL_CONFIG


def _query(sql: str) -> pd.DataFrame:
    """执行 SQL 查询并返回 DataFrame"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()


# ============================================================
# 概览页面 (app.py)
# ============================================================

def get_overview_kpis():
    """获取概览页面 4 个 KPI 卡片"""
    return _query("""
        SELECT
            SUM(total_orders) AS total_orders,
            SUM(total_gmv) AS total_gmv,
            AVG(avg_delivery_days) AS avg_delivery,
            AVG(delay_rate) * 100 AS delay_rate_pct
        FROM dws_daily_metrics
    """)


def get_overview_gmv_trend():
    """GMV 月度趋势"""
    return _query("""
        SELECT
            DATE_FORMAT(purchase_date, '%Y-%m') AS month,
            SUM(total_gmv) AS gmv,
            SUM(total_orders) AS orders
        FROM dws_daily_metrics
        GROUP BY DATE_FORMAT(purchase_date, '%Y-%m')
        ORDER BY month
    """)


# ============================================================
# 页面1: 供应商交付时效
# ============================================================

def get_delivery_distribution():
    """交付天数分布（用于直方图）"""
    return _query("""
        SELECT delivery_days, COUNT(*) AS cnt
        FROM dwd_order_detail
        WHERE delivery_days > 0 AND delivery_days <= 60 AND delivered_date IS NOT NULL
        GROUP BY delivery_days
        ORDER BY delivery_days
    """)


def get_delivery_monthly_trend():
    """月度平均交付天数趋势"""
    return _query("""
        SELECT purchase_date, avg_delivery_days, delay_rate
        FROM dws_daily_metrics
        ORDER BY purchase_date
    """)


def get_delivery_by_state():
    """各州平均交付天数（全局汇总）"""
    return _query("""
        SELECT state, avg_delivery_days, delay_rate, total_orders
        FROM dws_state_summary
        ORDER BY avg_delivery_days DESC
    """)


def get_delivery_by_category():
    """各品类交付时效（全局，含延迟率、订单量）"""
    return _query("""
        SELECT
            category_name,
            avg_delivery_days,
            delay_rate,
            total_orders,
            avg_review_score
        FROM dws_category_summary
        ORDER BY total_orders DESC
    """)


def get_delivery_heatmap_data():
    """月度×品类 交付天数热力图"""
    return _query("""
        SELECT
            purchase_date,
            category_name,
            avg_delivery_days
        FROM dws_daily_category
        WHERE purchase_date IS NOT NULL
    """)


def get_delayed_top_categories():
    """延迟最严重的 Top 品类"""
    return _query("""
        SELECT
            category_name,
            delay_rate,
            avg_delay_days,
            total_orders
        FROM dws_category_summary
        WHERE total_orders > 100
        ORDER BY delay_rate DESC
        LIMIT 10
    """)


# ============================================================
# 页面2: 品类库存周转
# ============================================================

def get_category_abc():
    """ABC 分类数据"""
    return _query("""
        SELECT
            category_name,
            total_revenue,
            revenue_pct,
            cumulative_pct,
            abc_class,
            total_orders,
            avg_price,
            unique_sellers,
            daily_avg_items
        FROM dws_category_summary
        ORDER BY total_revenue DESC
    """)


def get_category_treemap():
    """品类收入树状图"""
    return _query("""
        SELECT
            category_name,
            total_revenue,
            total_orders,
            avg_price,
            cumulative_pct
        FROM dws_category_summary
        ORDER BY total_revenue DESC
        LIMIT 30
    """)


def get_category_sellers():
    """品类卖家数"""
    return _query("""
        SELECT
            category_name,
            unique_sellers,
            total_orders,
            total_revenue
        FROM dws_category_summary
        ORDER BY total_orders DESC
    """)


# ============================================================
# 页面3: 物流满意度归因
# ============================================================

def get_review_vs_delivery():
    """交付天数 vs 评分散点数据（抽样）"""
    return _query("""
        SELECT
            delivery_days,
            review_score,
            delay_days,
            is_delayed,
            freight_value,
            product_weight_g
        FROM dwd_order_detail
        WHERE delivery_days > 0
          AND review_score IS NOT NULL
          AND delivery_days <= 60
        ORDER BY RAND()
        LIMIT 5000
    """)


def get_review_by_delivery_bucket():
    """按时 vs 延迟评分对比"""
    return _query("""
        SELECT
            CASE
                WHEN delivery_days <= 10 THEN '0-10天'
                WHEN delivery_days <= 20 THEN '11-20天'
                WHEN delivery_days <= 30 THEN '21-30天'
                WHEN delivery_days <= 40 THEN '31-40天'
                ELSE '40天以上'
            END AS bucket,
            AVG(review_score) AS avg_score,
            COUNT(*) AS cnt
        FROM dwd_order_detail
        WHERE delivery_days > 0 AND review_score IS NOT NULL
        GROUP BY bucket
        ORDER BY MIN(delivery_days)
    """)


def get_review_state_comparison():
    """各州满意度对比"""
    return _query("""
        SELECT
            state,
            avg_review_score,
            avg_delivery_days,
            total_orders
        FROM dws_state_summary
        WHERE total_orders > 100
        ORDER BY avg_review_score ASC
    """)


def get_correlation_data():
    """相关性分析数据（抽样）"""
    return _query("""
        SELECT
            delivery_days,
            delay_days,
            review_score,
            freight_value,
            product_weight_g,
            price
        FROM dwd_order_detail
        WHERE delivery_days > 0
          AND review_score IS NOT NULL
          AND delivery_days <= 60
        ORDER BY RAND()
        LIMIT 5000
    """)


# ============================================================
# 页面4: 销售趋势分析
# ============================================================

def get_sales_trend():
    """日度销售趋势"""
    return _query("""
        SELECT
            purchase_date,
            total_orders,
            total_gmv,
            avg_order_value,
            unique_customers
        FROM dws_daily_metrics
        ORDER BY purchase_date
    """)


def get_sales_monthly():
    """月度销售汇总"""
    return _query("""
        SELECT
            DATE_FORMAT(purchase_date, '%Y-%m') AS month,
            SUM(total_orders) AS orders,
            SUM(total_gmv) AS gmv,
            AVG(avg_order_value) AS aov,
            SUM(unique_customers) AS customers
        FROM dws_daily_metrics
        GROUP BY DATE_FORMAT(purchase_date, '%Y-%m')
        ORDER BY month
    """)


def get_sales_weekday_pattern():
    """星期几销售模式"""
    return _query("""
        SELECT
            purchase_dayofweek,
            COUNT(*) AS order_count,
            AVG(payment_value) AS avg_value
        FROM dwd_order_detail
        GROUP BY purchase_dayofweek
        ORDER BY purchase_dayofweek
    """)


def get_sales_seasonal_heatmap():
    """季节性热力图（周×月）"""
    return _query("""
        SELECT
            purchase_month,
            purchase_dayofweek,
            COUNT(*) AS cnt
        FROM dwd_order_detail
        GROUP BY purchase_month, purchase_dayofweek
    """)


def get_sales_by_state():
    """各州销售额排名"""
    return _query("""
        SELECT
            state,
            total_orders,
            total_gmv,
            unique_customers
        FROM dws_state_summary
        ORDER BY total_gmv DESC
    """)


def get_rfm_data():
    """RFM 客户分层（基于 DWD）"""
    return _query("""
        SELECT
            customer_unique_id,
            DATEDIFF('2018-10-01', MAX(purchase_date)) AS recency,
            COUNT(DISTINCT order_id) AS frequency,
            SUM(payment_value) AS monetary
        FROM dwd_order_detail
        WHERE customer_unique_id IS NOT NULL
        GROUP BY customer_unique_id
    """)


def get_category_trend():
    """Top 品类月度趋势"""
    return _query("""
        SELECT
            purchase_date,
            category_name,
            total_gmv,
            total_orders
        FROM dws_daily_category
        WHERE category_name IN (
            SELECT category_name
            FROM dws_category_summary
            ORDER BY total_revenue DESC
            LIMIT 5
        )
        ORDER BY purchase_date, category_name
    """)


# ============================================================
# 页面5: SQL 分析对比（新增数仓结构概览）
# ============================================================

def get_warehouse_stats():
    """获取数仓各层数据量统计"""
    tables = {
        'ODS (原始数据)': [
            'ods_customers', 'ods_sellers', 'ods_products',
            'ods_orders', 'ods_order_items', 'ods_order_payments', 'ods_order_reviews'
        ],
        'DWD (明细宽表)': ['dim_customers', 'dim_products', 'dim_sellers', 'dim_dates', 'dwd_order_detail'],
        'DWS (汇总表)': [
            'dws_daily_metrics', 'dws_daily_category', 'dws_daily_state',
            'dws_weekly_metrics', 'dws_category_summary', 'dws_state_summary'
        ],
    }
    result = {}
    for layer, table_list in tables.items():
        layer_stats = []
        for table in table_list:
            try:
                df = _query(f"SELECT COUNT(*) AS cnt FROM {table}")
                cnt = df['cnt'].iloc[0]
                layer_stats.append({'table': table, 'rows': cnt})
            except Exception:
                layer_stats.append({'table': table, 'rows': 0})
        result[layer] = layer_stats
    return result
