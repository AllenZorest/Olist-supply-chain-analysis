"""
数仓全流程 ETL 编排脚本
================================
执行顺序: ODS → DWD → DWS
每层完成后再启动下一层

使用方法:
  py dw/run_all.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
import pandas as pd
from datetime import date, timedelta
from dw.config import MYSQL_CONFIG, DATA_DIR, SQL_DIR, CSV_TABLE_MAP


# ============================================================
# 工具函数
# ============================================================

def get_conn():
    """获取 MySQL 连接"""
    return pymysql.connect(**MYSQL_CONFIG)


def execute_sql_file(conn, filepath, skip_patterns=None):
    """执行 SQL 文件，跳过指定模式的行"""
    if skip_patterns is None:
        skip_patterns = []
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    cursor = conn.cursor()
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if not stmt:
            continue
        skip = False
        for pat in skip_patterns:
            if pat.upper() in stmt.upper():
                skip = True
                break
        if skip:
            continue
        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"  ⚠ {e}")
    conn.commit()
    cursor.close()


def step_header(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ============================================================
# 第 1 层: ODS — CSV → MySQL 原样入库
# ============================================================

def run_ods():
    """CSV 原样导入 ODS 表"""
    step_header("第 1 层: ODS — CSV 原样入库")

    # 1.1 创建 ODS 表
    print("[1/3] 创建 ODS 表...")
    conn = get_conn()
    execute_sql_file(conn, SQL_DIR / "ods_setup.sql")
    conn.close()
    print("  ✓ ODS 表已就绪")

    # 1.2 批量导入 CSV
    print("[2/3] 导入 CSV 数据...")
    today = date.today().isoformat()

    import_order = [
        'customers', 'sellers', 'products', 'product_category_translation',
        'orders', 'order_items', 'order_payments', 'order_reviews'
    ]

    conn = get_conn()
    cursor = conn.cursor()

    # 清空 ODS 表（幂等重跑）
    for table in reversed(import_order):
        cursor.execute(f"DELETE FROM ods_{table}")
    conn.commit()

    for table_name in import_order:
        filename = CSV_TABLE_MAP[table_name]
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"  ✗ 文件不存在: {filepath}")
            continue

        df = pd.read_csv(filepath)
        # 修正 Kaggle 数据集中的拼写错误 (lenght → length)
        df.rename(columns={
            'product_name_lenght': 'product_name_length',
            'product_description_lenght': 'product_description_length'
        }, inplace=True)
        ods_table = f"ods_{table_name}"

        # 构造 INSERT
        cols = [c for c in df.columns]
        all_cols = cols + ['etl_date']
        placeholders = ', '.join(['%s'] * len(all_cols))

        batch_size = 1000
        total = len(df)
        for start in range(0, total, batch_size):
            batch = df.iloc[start:start + batch_size]
            values = []
            for row in batch.itertuples(index=False):
                vals = tuple(
                    None if pd.isna(v) else (
                        v.isoformat() if isinstance(v, pd.Timestamp) else v
                    ) for v in row
                )
                vals = vals + (today,)
                values.append(vals)
            sql = f"INSERT INTO `{ods_table}` ({', '.join(f'`{c}`' for c in all_cols)}) VALUES ({placeholders})"
            cursor.executemany(sql, values)
        conn.commit()
        print(f"  ✓ {ods_table}: {total} 行")

    cursor.close()
    conn.close()

    # 1.3 验证
    print("[3/3] 验证行数...")
    conn = get_conn()
    cursor = conn.cursor()
    for table_name in import_order:
        cursor.execute(f"SELECT COUNT(*) FROM ods_{table_name}")
        cnt = cursor.fetchone()[0]
        print(f"  ods_{table_name}: {cnt} 行")
    cursor.close()
    conn.close()
    print("  ✓ ODS 层完成")


# ============================================================
# 第 2 层: DWD — ODS 清洗 → 维度表 + 订单宽表
# ============================================================

def run_dwd():
    """从 ODS 清洗并构建 DWD 层"""
    step_header("第 2 层: DWD — 明细宽表 + 维度表")

    conn = get_conn()
    cursor = conn.cursor()

    # 2.1 创建 DWD 表
    print("[1/6] 创建 DWD 表...")
    execute_sql_file(conn, SQL_DIR / "dwd_setup.sql")
    print("  ✓ DWD 表已创建")

    today = date.today().isoformat()

    # 2.2 dim_dates — 日期维度
    print("[2/6] 构建 dim_dates...")
    cursor.execute("DELETE FROM dim_dates")

    start_date = date(2016, 1, 1)
    end_date = date(2019, 1, 1)
    d = start_date
    dates = []
    while d < end_date:
        dates.append((
            d.isoformat(),
            d.year, (d.month - 1) // 3 + 1, d.month,
            d.strftime('%B'), d.isocalendar()[1],
            d.day, d.isoweekday(), d.strftime('%A'),
            1 if d.isoweekday() >= 6 else 0,
            d.strftime('%Y-%m')
        ))
        d += timedelta(days=1)

    cursor.executemany(
        "INSERT INTO `dim_dates` (`date_id`,`year`,`quarter`,`month`,`month_name`,`week_of_year`,"
        "`day_of_month`,`day_of_week`,`day_name`,`is_weekend`,`year_month`) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        dates
    )
    conn.commit()
    print(f"  ✓ dim_dates: {len(dates)} 行")

    # 2.3 dim_customers — 客户维度
    print("[3/6] 构建 dim_customers...")
    cursor.execute("DELETE FROM dim_customers")
    cursor.execute("""
        INSERT INTO dim_customers
            (customer_unique_id, customer_state, customer_city,
             customer_zip_prefix, first_purchase_date)
        SELECT
            c.customer_unique_id,
            MAX(c.customer_state),
            MAX(c.customer_city),
            MAX(c.customer_zip_code_prefix),
            MIN(DATE(o.order_purchase_timestamp)) AS first_purchase_date
        FROM ods_customers c
        LEFT JOIN ods_orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_unique_id
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dim_customers")
    print(f"  ✓ dim_customers: {cursor.fetchone()[0]} 行")

    # 2.4 dim_products — 商品维度
    print("[4/6] 构建 dim_products...")
    cursor.execute("DELETE FROM dim_products")
    cursor.execute("""
        INSERT INTO dim_products
            (product_id, product_category_name, category_name_english,
             product_weight_g, product_length_cm, product_height_cm,
             product_width_cm, product_volume_cm3, product_photos_qty)
        SELECT
            p.product_id,
            p.product_category_name,
            COALESCE(t.product_category_name_english, p.product_category_name),
            p.product_weight_g,
            p.product_length_cm,
            p.product_height_cm,
            p.product_width_cm,
            p.product_length_cm * p.product_height_cm * p.product_width_cm,
            p.product_photos_qty
        FROM ods_products p
        LEFT JOIN ods_product_category_translation t
            ON p.product_category_name = t.product_category_name
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dim_products")
    print(f"  ✓ dim_products: {cursor.fetchone()[0]} 行")

    # 2.5 dim_sellers — 卖家维度
    print("[5/6] 构建 dim_sellers...")
    cursor.execute("DELETE FROM dim_sellers")
    cursor.execute("""
        INSERT INTO dim_sellers
            (seller_id, seller_state, seller_city, seller_zip_prefix)
        SELECT seller_id, seller_state, seller_city, seller_zip_code_prefix
        FROM ods_sellers
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dim_sellers")
    print(f"  ✓ dim_sellers: {cursor.fetchone()[0]} 行")

    # 2.6 dwd_order_detail — 订单明细宽表（核心）
    print("[6/6] 构建 dwd_order_detail（最耗时）...")
    cursor.execute("DELETE FROM dwd_order_detail")
    cursor.execute("""
        INSERT INTO dwd_order_detail (
            order_id, order_item_id,
            order_status, purchase_date, purchase_timestamp,
            delivered_date, delivered_timestamp, estimated_date,
            delivery_days, carrier_days, is_delayed, delay_days,
            purchase_year, purchase_month, purchase_year_month, purchase_dayofweek, is_weekend,
            customer_unique_id, customer_state,
            product_id, category_name, product_weight_g,
            seller_id, seller_state,
            price, freight_value,
            payment_value, payment_type,
            review_score,
            etl_date
        )
        SELECT
            o.order_id,
            oi.order_item_id,
            o.order_status,
            DATE(o.order_purchase_timestamp),
            o.order_purchase_timestamp,
            DATE(o.order_delivered_customer_date),
            o.order_delivered_customer_date,
            DATE(o.order_estimated_delivery_date),
            -- 交付时效特征
            DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp),
            DATEDIFF(o.order_delivered_customer_date, o.order_delivered_carrier_date),
            CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END,
            GREATEST(DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date), 0),
            -- 时间维度
            YEAR(o.order_purchase_timestamp),
            MONTH(o.order_purchase_timestamp),
            DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m'),
            DAYOFWEEK(o.order_purchase_timestamp),
            CASE WHEN DAYOFWEEK(o.order_purchase_timestamp) IN (1, 7) THEN 1 ELSE 0 END,
            -- 客户
            c.customer_unique_id,
            c.customer_state,
            -- 商品
            dp.product_id,
            dp.category_name_english,
            dp.product_weight_g,
            -- 卖家
            s.seller_id,
            s.seller_state,
            -- 交易
            oi.price,
            oi.freight_value,
            -- 支付（订单级聚合）
            op.payment_value,
            op.payment_type,
            -- 评价
            r.review_score,
            -- 审计
            CURDATE()
        FROM ods_orders o
        INNER JOIN ods_order_items oi ON o.order_id = oi.order_id
        LEFT JOIN ods_customers c ON o.customer_id = c.customer_id
        LEFT JOIN dim_products dp ON oi.product_id = dp.product_id
        LEFT JOIN ods_sellers s ON oi.seller_id = s.seller_id
        LEFT JOIN (
            SELECT order_id, SUM(payment_value) AS payment_value, MAX(payment_type) AS payment_type
            FROM ods_order_payments GROUP BY order_id
        ) op ON o.order_id = op.order_id
        LEFT JOIN (
            SELECT order_id, AVG(review_score) AS review_score
            FROM ods_order_reviews GROUP BY order_id
        ) r ON o.order_id = r.order_id
        WHERE o.order_status IN ('delivered', 'shipped')
          AND o.order_purchase_timestamp IS NOT NULL
          AND o.order_delivered_customer_date IS NOT NULL
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dwd_order_detail")
    print(f"  ✓ dwd_order_detail: {cursor.fetchone()[0]} 行")

    # 更新维度表统计
    print("  更新维度表统计...")
    cursor.execute("""
        UPDATE dim_sellers ds
        SET total_orders = (SELECT COUNT(*) FROM dwd_order_detail WHERE seller_id = ds.seller_id),
            total_revenue = (SELECT COALESCE(SUM(price), 0) FROM dwd_order_detail WHERE seller_id = ds.seller_id)
    """)
    cursor.execute("""
        UPDATE dim_customers dc
        SET total_orders = (SELECT COUNT(DISTINCT order_id) FROM dwd_order_detail WHERE customer_unique_id = dc.customer_unique_id)
    """)
    conn.commit()

    cursor.close()
    conn.close()
    print("  ✓ DWD 层完成")


# ============================================================
# 第 3 层: DWS — DWD 聚合 → 汇总表
# ============================================================

def run_dws():
    """从 DWD 聚合生成 DWS 汇总表"""
    step_header("第 3 层: DWS — 日/周聚合")

    conn = get_conn()
    cursor = conn.cursor()

    # 3.1 创建 DWS 表
    print("[1/7] 创建 DWS 表...")
    execute_sql_file(conn, SQL_DIR / "dws_setup.sql")
    print("  ✓ DWS 表已创建")

    today = date.today().isoformat()

    # 3.2 dws_daily_metrics — 日度核心指标
    print("[2/7] 构建 dws_daily_metrics...")
    cursor.execute("DELETE FROM dws_daily_metrics")
    cursor.execute("""
        INSERT INTO dws_daily_metrics (
            purchase_date, total_orders, total_items, total_gmv, total_revenue,
            total_freight, avg_order_value, delivered_orders,
            avg_delivery_days, delay_rate, avg_delay_days,
            avg_review_score, unique_customers, unique_sellers, etl_date
        )
        SELECT
            purchase_date,
            COUNT(DISTINCT order_id) AS total_orders,
            COUNT(*) AS total_items,
            SUM(payment_value) AS total_gmv,
            SUM(price) AS total_revenue,
            SUM(freight_value) AS total_freight,
            SUM(payment_value) / NULLIF(COUNT(DISTINCT order_id), 0) AS avg_order_value,
            COUNT(DISTINCT CASE WHEN delivered_date IS NOT NULL THEN order_id END) AS delivered_orders,
            AVG(CASE WHEN delivery_days > 0 THEN delivery_days END) AS avg_delivery_days,
            AVG(is_delayed) AS delay_rate,
            AVG(CASE WHEN is_delayed = 1 THEN delay_days END) AS avg_delay_days,
            AVG(review_score) AS avg_review_score,
            COUNT(DISTINCT customer_unique_id) AS unique_customers,
            COUNT(DISTINCT seller_id) AS unique_sellers,
            CURDATE()
        FROM dwd_order_detail
        GROUP BY purchase_date
        ORDER BY purchase_date
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dws_daily_metrics")
    print(f"  ✓ dws_daily_metrics: {cursor.fetchone()[0]} 行")

    # 3.3 dws_daily_category — 日品类汇总
    print("[3/7] 构建 dws_daily_category...")
    cursor.execute("DELETE FROM dws_daily_category")
    cursor.execute("""
        INSERT INTO dws_daily_category (
            purchase_date, category_name, total_orders, total_gmv, total_revenue,
            avg_price, avg_delivery_days, delay_rate, avg_review_score, etl_date
        )
        SELECT
            purchase_date,
            category_name,
            COUNT(DISTINCT order_id),
            SUM(payment_value),
            SUM(price),
            AVG(price),
            AVG(CASE WHEN delivery_days > 0 THEN delivery_days END),
            AVG(is_delayed),
            AVG(review_score),
            CURDATE()
        FROM dwd_order_detail
        WHERE category_name IS NOT NULL AND category_name != ''
        GROUP BY purchase_date, category_name
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dws_daily_category")
    print(f"  ✓ dws_daily_category: {cursor.fetchone()[0]} 行")

    # 3.4 dws_daily_state — 日州级汇总
    print("[4/7] 构建 dws_daily_state...")
    cursor.execute("DELETE FROM dws_daily_state")
    cursor.execute("""
        INSERT INTO dws_daily_state (
            purchase_date, state, total_orders, total_gmv,
            avg_delivery_days, delay_rate, avg_review_score, etl_date
        )
        SELECT
            purchase_date,
            customer_state,
            COUNT(DISTINCT order_id),
            SUM(payment_value),
            AVG(CASE WHEN delivery_days > 0 THEN delivery_days END),
            AVG(is_delayed),
            AVG(review_score),
            CURDATE()
        FROM dwd_order_detail
        WHERE customer_state IS NOT NULL
        GROUP BY purchase_date, customer_state
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dws_daily_state")
    print(f"  ✓ dws_daily_state: {cursor.fetchone()[0]} 行")

    # 3.5 dws_weekly_metrics — 周度汇总
    print("[5/7] 构建 dws_weekly_metrics...")
    cursor.execute("DELETE FROM dws_weekly_metrics")
    cursor.execute("""
        INSERT INTO dws_weekly_metrics (
            year_week, week_start_date, week_end_date,
            total_orders, total_gmv, avg_daily_orders,
            avg_delivery_days, delay_rate, avg_review_score, etl_date
        )
        SELECT
            CONCAT(YEAR(purchase_date), '-W', LPAD(WEEK(purchase_date, 1), 2, '0')) AS year_week,
            MIN(purchase_date) AS week_start_date,
            MAX(purchase_date) AS week_end_date,
            SUM(total_orders),
            SUM(total_gmv),
            SUM(total_orders) / 7.0,
            AVG(avg_delivery_days),
            AVG(delay_rate),
            AVG(avg_review_score),
            CURDATE()
        FROM dws_daily_metrics
        GROUP BY YEAR(purchase_date), WEEK(purchase_date, 1)
        ORDER BY week_start_date
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dws_weekly_metrics")
    print(f"  ✓ dws_weekly_metrics: {cursor.fetchone()[0]} 行")

    # 3.6 dws_category_summary — 品类全局汇总（含 ABC）
    print("[6/7] 构建 dws_category_summary（含 ABC 分类）...")
    cursor.execute("DELETE FROM dws_category_summary")
    cursor.execute("""
        INSERT INTO dws_category_summary (
            category_name, total_orders, total_gmv, total_revenue,
            avg_price, avg_delivery_days, delay_rate, avg_review_score,
            unique_sellers, daily_avg_items, etl_date
        )
        SELECT
            category_name,
            COUNT(DISTINCT order_id),
            SUM(payment_value),
            SUM(price),
            AVG(price),
            AVG(CASE WHEN delivery_days > 0 THEN delivery_days END),
            AVG(is_delayed),
            AVG(review_score),
            COUNT(DISTINCT seller_id),
            COUNT(*) / NULLIF(DATEDIFF(MAX(purchase_date), MIN(purchase_date)), 0),
            CURDATE()
        FROM dwd_order_detail
        WHERE category_name IS NOT NULL AND category_name != ''
        GROUP BY category_name
    """)
    # 计算收入占比和累计占比（ABC 分类）
    cursor.execute("SET @total := (SELECT SUM(total_revenue) FROM dws_category_summary)")
    cursor.execute("SET @cum := 0")
    cursor.execute("""
        UPDATE dws_category_summary
        SET revenue_pct = total_revenue / @total,
            cumulative_pct = (@cum := @cum + total_revenue / @total)
        ORDER BY total_revenue DESC
    """)
    # ABC 分类标签
    cursor.execute("""
        UPDATE dws_category_summary
        SET abc_class = CASE
            WHEN cumulative_pct <= 0.70 THEN 'A'
            WHEN cumulative_pct <= 0.90 THEN 'B'
            ELSE 'C'
        END
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dws_category_summary")
    print(f"  ✓ dws_category_summary: {cursor.fetchone()[0]} 行")

    # 3.7 dws_state_summary — 州级全局汇总
    print("[7/7] 构建 dws_state_summary...")
    cursor.execute("DELETE FROM dws_state_summary")
    cursor.execute("""
        INSERT INTO dws_state_summary (
            state, total_orders, total_gmv, avg_delivery_days,
            delay_rate, avg_review_score, unique_customers, etl_date
        )
        SELECT
            customer_state,
            COUNT(DISTINCT order_id),
            SUM(payment_value),
            AVG(CASE WHEN delivery_days > 0 THEN delivery_days END),
            AVG(is_delayed),
            AVG(review_score),
            COUNT(DISTINCT customer_unique_id),
            CURDATE()
        FROM dwd_order_detail
        WHERE customer_state IS NOT NULL
        GROUP BY customer_state
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM dws_state_summary")
    print(f"  ✓ dws_state_summary: {cursor.fetchone()[0]} 行")

    cursor.close()
    conn.close()
    print("  ✓ DWS 层完成")


# ============================================================
# 全流程编排
# ============================================================

def run_all(layer=None):
    """依次执行 ODS → DWD → DWS（可指定单层）
    layer: None=全量, 'ods', 'dwd', 'dws'
    """
    layers = {
        'ods': ('ODS', run_ods),
        'dwd': ('DWD', run_dwd),
        'dws': ('DWS', run_dws),
    }

    if layer:
        if layer not in layers:
            print(f"❌ 未知层级: {layer}, 可选: {list(layers.keys())}")
            return
        targets = [layers[layer]]
    else:
        targets = list(layers.values())

    print("=" * 60)
    print("  Olist 数仓 ETL")
    print(f"  目标数据库: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    print(f"  执行层级: {' → '.join(t[0] for t in targets)}")
    print("=" * 60)

    try:
        for name, func in targets:
            func()

        if layer is None:
            step_header("🎉 数仓 ETL 全部完成！")
            print()
            print("  数仓分层表结构:")
            print("  ┌─────────────────────────────────────────┐")
            print("  │  ADS  ← Streamlit 看板（读取 DWS 聚合表）│")
            print("  │  DWS  ← 6 张聚合汇总表                   │")
            print("  │  DWD  ← 1 张订单宽表 + 4 张维度表          │")
            print("  │  ODS  ← 8 张原始数据表                    │")
            print("  └─────────────────────────────────────────┘")
            print()
            print("  启动看板: streamlit run datall.py")
    except pymysql.err.OperationalError as e:
        print(f"\n❌ MySQL 连接失败: {e}")
        print("\n请确认 MySQL 服务已启动，并修改 dw/config.py 中的连接信息")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Olist 数仓 ETL')
    parser.add_argument('--layer', choices=['ods', 'dwd', 'dws'], help='只运行指定层，不传则全量')
    args = parser.parse_args()
    run_all(layer=args.layer)
