"""
SQL 分析引擎模块

支持两种数据库后端：
1. MySQL（需要本地 MySQL 服务运行）
2. SQLite（零配置，开箱即用）

工作流程模拟真实场景：
  CSV 数据 → 导入数据库 → 写 SQL 查询 → 返回结果 → Streamlit 展示

使用方式:
  from sql.sql_analyzer import SQLAnalyzer
  analyzer = SQLAnalyzer(use_mysql=True)  # 或 use_mysql=False 用 SQLite
  df = analyzer.execute("SELECT * FROM v_order_full LIMIT 10")
"""
import sqlite3
import pandas as pd
from pathlib import Path
import re
import streamlit as st

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"


class SQLAnalyzer:
    """
    SQL 分析引擎
    - 自动选择 MySQL 或 SQLite 后端
    - 支持 CSV 数据导入
    - 封装常用分析查询
    """

    def __init__(self, use_mysql=True, mysql_config=None):
        """
        参数:
            use_mysql: True=MySQL, False=SQLite
            mysql_config: dict with host, port, user, password, database
        """
        self.use_mysql = use_mysql
        self.mysql_config = mysql_config or {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password': '',
            'database': 'olist_supply_chain',
            'charset': 'utf8mb4',
        }
        self.conn = None
        self.engine_type = 'unknown'

    def connect(self):
        """建立数据库连接"""
        if self.use_mysql:
            try:
                import pymysql
                self.conn = pymysql.connect(**self.mysql_config)
                self.engine_type = 'MySQL'
                return True
            except ImportError:
                print("pymysql 未安装，回退到 SQLite。安装: pip install pymysql")
                self.use_mysql = False
            except Exception as e:
                print(f"MySQL 连接失败: {e}，回退到 SQLite")
                self.use_mysql = False

        # SQLite 回退
        db_path = DATA_DIR / "olist.db"
        self.conn = sqlite3.connect(str(db_path))
        self.engine_type = 'SQLite'
        return True

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

    def execute(self, sql: str) -> pd.DataFrame:
        """执行 SQL 查询，返回 DataFrame"""
        # SQLite 不兼容的 MySQL 语法转换
        if not self.use_mysql:
            sql = self._mysql_to_sqlite(sql)

        try:
            return pd.read_sql_query(sql, self.conn)
        except Exception as e:
            # 尝试去掉注释再执行
            clean_sql = '\n'.join(
                line for line in sql.split('\n')
                if not line.strip().startswith('--')
            )
            return pd.read_sql_query(clean_sql, self.conn)

    def _mysql_to_sqlite(self, sql: str) -> str:
        """将 MySQL 特有语法转为 SQLite 兼容语法"""
        # DATE_FORMAT → strftime
        sql = re.sub(
            r"DATE_FORMAT\((\w+),\s*'%Y-%m'\)",
            r"strftime('%Y-%m', \1)",
            sql
        )
        # DAYOFWEEK: MySQL 1=Sunday, SQLite 0=Sunday
        sql = sql.replace(
            "DAYOFWEEK(order_purchase_timestamp)",
            "CAST(strftime('%w', order_purchase_timestamp) AS INTEGER) + 1"
        )
        # NTILE → 用 PERCENT_RANK 近似替代
        sql = re.sub(
            r"NTILE\(4\)\s*OVER\s*\(ORDER BY\s*(\w+)\s*(DESC|ASC)\)",
            lambda m: (
                "CASE WHEN percent_rank() OVER (ORDER BY "
                + m.group(1) + " " + m.group(2)
                + ") <= 0.25 THEN 1 WHEN ... THEN 4 END"
            ),
            sql
        )
        return sql

    # ---- 批量执行分析查询 ----

    def run_all_analysis(self):
        """执行所有分析查询，返回 {查询名称: DataFrame} 字典"""
        queries = self._get_analysis_queries()
        results = {}
        for name, sql in queries.items():
            try:
                results[name] = self.execute(sql)
            except Exception as e:
                results[name] = pd.DataFrame({'error': [str(e)]})
        return results

    def run_module_queries(self, module_name: str):
        """执行指定模块的查询"""
        all_queries = self._get_analysis_queries()
        module_queries = {
            k: v for k, v in all_queries.items()
            if k.startswith(module_name)
        }
        results = {}
        for name, sql in module_queries.items():
            try:
                results[name] = self.execute(sql)
            except Exception as e:
                results[name] = pd.DataFrame({'error': [str(e)]})
        return results

    def _get_analysis_queries(self):
        """定义所有分析查询（与 analysis_queries.sql 保持同步）"""
        queries = {}

        # ---- 📦 交付时效 ----
        queries['delivery_kpi'] = """
            SELECT
                COUNT(DISTINCT order_id) AS total_delivered,
                ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
                ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
                ROUND(AVG(CASE WHEN is_delayed = 1 THEN delay_days END), 1) AS avg_delay_when_late
            FROM v_order_full
            WHERE order_status = 'delivered'
        """

        queries['delivery_monthly_trend'] = """
            SELECT
                purchase_year_month,
                ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
                ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
                COUNT(DISTINCT order_id) AS order_count
            FROM v_order_full
            WHERE order_status = 'delivered'
            GROUP BY purchase_year_month
            ORDER BY purchase_year_month
        """

        queries['delivery_by_state'] = """
            SELECT
                customer_state,
                ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
                ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
                COUNT(DISTINCT order_id) AS order_count
            FROM v_order_full
            WHERE order_status = 'delivered' AND customer_state IS NOT NULL
            GROUP BY customer_state
            HAVING order_count >= 50
            ORDER BY avg_delivery_days DESC
        """

        queries['delivery_by_category'] = """
            SELECT
                category_name,
                ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
                ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
                COUNT(DISTINCT order_id) AS order_count
            FROM v_order_full
            WHERE order_status = 'delivered' AND category_name IS NOT NULL
            GROUP BY category_name
            ORDER BY delay_rate_pct DESC
            LIMIT 15
        """

        queries['delivery_bad_sellers'] = """
            SELECT
                seller_id,
                ROUND(AVG(delivery_days), 1) AS avg_delivery_days,
                ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
                COUNT(DISTINCT order_id) AS total_orders
            FROM v_order_full
            WHERE order_status = 'delivered' AND seller_id IS NOT NULL
            GROUP BY seller_id
            ORDER BY delay_rate_pct DESC
            LIMIT 10
        """

        # ---- 📊 库存周转 ----
        queries['inventory_abc'] = """
            WITH category_revenue AS (
                SELECT
                    category_name,
                    SUM(price) AS revenue,
                    COUNT(DISTINCT order_id) AS orders
                FROM v_order_full
                WHERE order_status = 'delivered' AND category_name IS NOT NULL
                GROUP BY category_name
            ),
            total AS (
                SELECT SUM(revenue) AS total_rev FROM category_revenue
            )
            SELECT
                cr.category_name,
                ROUND(cr.revenue, 0) AS revenue,
                ROUND(cr.revenue / t.total_rev * 100, 1) AS revenue_pct,
                ROUND(SUM(cr.revenue) OVER (ORDER BY cr.revenue DESC) / t.total_rev * 100, 1) AS cum_pct,
                CASE
                    WHEN SUM(cr.revenue) OVER (ORDER BY cr.revenue DESC) / t.total_rev * 100 <= 70 THEN 'A类(核心)'
                    WHEN SUM(cr.revenue) OVER (ORDER BY cr.revenue DESC) / t.total_rev * 100 <= 90 THEN 'B类(重要)'
                    ELSE 'C类(长尾)'
                END AS abc_class
            FROM category_revenue cr, total t
            ORDER BY cr.revenue DESC
        """

        # ---- 🚚 满意度 ----
        queries['satisfaction_delayed_vs_ontime'] = """
            SELECT
                CASE WHEN is_delayed = 1 THEN '延迟交付' ELSE '按时交付' END AS delivery_type,
                COUNT(DISTINCT v.order_id) AS order_count,
                ROUND(AVG(r.review_score), 2) AS avg_score
            FROM v_order_full v
            INNER JOIN order_reviews r ON v.order_id = r.order_id
            WHERE v.order_status = 'delivered'
            GROUP BY is_delayed
        """

        queries['satisfaction_by_range'] = """
            SELECT
                CASE
                    WHEN delivery_days <= 5 THEN '0-5天'
                    WHEN delivery_days <= 10 THEN '6-10天'
                    WHEN delivery_days <= 15 THEN '11-15天'
                    WHEN delivery_days <= 20 THEN '16-20天'
                    WHEN delivery_days <= 30 THEN '21-30天'
                    ELSE '30天以上'
                END AS delivery_range,
                COUNT(DISTINCT v.order_id) AS order_count,
                ROUND(AVG(r.review_score), 2) AS avg_score
            FROM v_order_full v
            INNER JOIN order_reviews r ON v.order_id = r.order_id
            WHERE v.order_status = 'delivered'
            GROUP BY 1
            ORDER BY MIN(delivery_days)
        """

        queries['satisfaction_by_state'] = """
            SELECT
                v.customer_state,
                ROUND(AVG(v.is_delayed) * 100, 1) AS delay_rate_pct,
                ROUND(AVG(r.review_score), 2) AS avg_score,
                COUNT(DISTINCT v.order_id) AS order_count
            FROM v_order_full v
            INNER JOIN order_reviews r ON v.order_id = r.order_id
            WHERE v.order_status = 'delivered' AND v.customer_state IS NOT NULL
            GROUP BY v.customer_state
            HAVING order_count >= 50
            ORDER BY avg_score ASC
        """

        # ---- 📈 销售趋势 ----
        queries['sales_monthly'] = """
            SELECT
                purchase_year_month,
                COUNT(DISTINCT order_id) AS monthly_orders,
                ROUND(SUM(price), 0) AS monthly_revenue,
                COUNT(DISTINCT customer_unique_id) AS unique_customers,
                ROUND(SUM(price) / COUNT(DISTINCT order_id), 0) AS avg_order_value
            FROM v_order_full
            WHERE order_status = 'delivered'
            GROUP BY purchase_year_month
            ORDER BY purchase_year_month
        """

        queries['sales_by_state'] = """
            SELECT
                customer_state,
                COUNT(DISTINCT order_id) AS total_orders,
                ROUND(SUM(price), 0) AS total_revenue,
                COUNT(DISTINCT customer_unique_id) AS customer_count
            FROM v_order_full
            WHERE order_status = 'delivered' AND customer_state IS NOT NULL
            GROUP BY customer_state
            ORDER BY total_revenue DESC
        """

        queries['sales_rfm'] = """
            WITH rfm_base AS (
                SELECT
                    customer_unique_id,
                    julianday((SELECT MAX(order_purchase_timestamp) FROM v_order_full WHERE order_status = 'delivered')) -
                    julianday(MAX(order_purchase_timestamp)) AS recency_days,
                    COUNT(DISTINCT order_id) AS frequency,
                    SUM(price) AS monetary
                FROM v_order_full
                WHERE order_status = 'delivered'
                GROUP BY customer_unique_id
            ),
            rfm_ranked AS (
                SELECT *,
                    NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
                    NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
                    NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
                FROM rfm_base
            ),
            rfm_segmented AS (
                SELECT *,
                    r_score + f_score + m_score AS rfm_total,
                    CASE
                        WHEN r_score + f_score + m_score >= 10 THEN '高价值客户'
                        WHEN r_score + f_score + m_score >= 7 THEN '潜力客户'
                        WHEN r_score + f_score + m_score >= 5 THEN '一般客户'
                        ELSE '流失风险客户'
                    END AS segment
                FROM rfm_ranked
            )
            SELECT
                segment,
                COUNT(*) AS customer_count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct,
                ROUND(AVG(monetary), 0) AS avg_lifetime_value
            FROM rfm_segmented
            GROUP BY segment
            ORDER BY
                CASE segment
                    WHEN '高价值客户' THEN 1
                    WHEN '潜力客户' THEN 2
                    WHEN '一般客户' THEN 3
                    WHEN '流失风险客户' THEN 4
                END
        """

        queries['sales_funnel'] = """
            SELECT
                order_status,
                COUNT(DISTINCT order_id) AS count
            FROM orders
            GROUP BY order_status
            ORDER BY count DESC
        """

        return queries


def import_csv_to_sqlite(csv_dir=None):
    """
    将 CSV 数据导入 SQLite 数据库（零配置方案）
    用于无法连接 MySQL 时

    参数:
        csv_dir: CSV 文件所在目录，默认 data/
    """
    import sqlite3

    if csv_dir is None:
        csv_dir = PROJECT_ROOT / "data"

    db_path = DATA_DIR / "olist.db"

    # 读取 schema 并执行
    schema_path = SQL_DIR / "schema.sql"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 简化 schema 为 SQLite 兼容
    # 去掉 MySQL 特有语法
    schema_sql = schema_sql.replace('AUTO_INCREMENT', '')
    schema_sql = re.sub(r'ENGINE=\w+', '', schema_sql)
    schema_sql = re.sub(r'CHARACTER SET \w+', '', schema_sql)
    schema_sql = re.sub(r'COLLATE \w+', '', schema_sql)
    schema_sql = re.sub(r'COMMENT\s+[^\n]+', '', schema_sql)
    schema_sql = schema_sql.replace('DATETIME', 'TEXT')
    schema_sql = schema_sql.replace('DECIMAL(10,2)', 'REAL')
    schema_sql = schema_sql.replace('INT', 'INTEGER')

    # 逐条执行 CREATE TABLE
    statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
    for stmt in statements:
        if stmt.upper().startswith('CREATE TABLE') or stmt.upper().startswith('CREATE DATABASE'):
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError as e:
                print(f"跳过: {e}")

    conn.commit()

    # 导入 CSV
    csv_files = {
        'customers': 'olist_customers_dataset.csv',
        'sellers': 'olist_sellers_dataset.csv',
        'products': 'olist_products_dataset.csv',
        'product_category_translation': 'product_category_name_translation.csv',
        'orders': 'olist_orders_dataset.csv',
        'order_items': 'olist_order_items_dataset.csv',
        'order_payments': 'olist_order_payments_dataset.csv',
        'order_reviews': 'olist_order_reviews_dataset.csv',
    }

    for table, filename in csv_files.items():
        filepath = csv_dir / filename
        if filepath.exists():
            df = pd.read_csv(filepath)
            df.to_sql(table, conn, if_exists='replace', index=False)
            print(f"已导入: {table} ({len(df)} 行)")

    conn.close()
    print(f"\nSQLite 数据库已创建: {db_path}")

    return db_path
