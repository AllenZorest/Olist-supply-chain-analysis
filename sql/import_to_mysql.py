"""
CSV 数据导入 MySQL 脚本

将 Olist 数据集的 CSV 文件导入本地 MySQL 数据库

使用方法：
  # 先修改下面的 MySQL 连接信息（用户名、密码）
  python sql/import_to_mysql.py

依赖：
  pip install pymysql pandas
"""
import pandas as pd
from pathlib import Path
import pymysql
import sys

# ========================================
# 修改这里的 MySQL 连接信息
# ========================================
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',           # 改成你的 MySQL 用户名
    'password': '',           # 改成你的 MySQL 密码
    'database': 'olist_supply_chain',
    'charset': 'utf8mb4',
}

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"

# CSV 文件映射
CSV_FILES = {
    'customers':                     'olist_customers_dataset.csv',
    'sellers':                       'olist_sellers_dataset.csv',
    'products':                      'olist_products_dataset.csv',
    'product_category_translation':  'product_category_name_translation.csv',
    'orders':                        'olist_orders_dataset.csv',
    'order_items':                   'olist_order_items_dataset.csv',
    'order_payments':                'olist_order_payments_dataset.csv',
    'order_reviews':                 'olist_order_reviews_dataset.csv',
}


def create_database():
    """创建数据库"""
    config = MYSQL_CONFIG.copy()
    db_name = config.pop('database')
    config.pop('charset', None)

    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} "
                   f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()
    conn.close()
    print(f"✓ 数据库 {db_name} 已就绪")


def execute_schema():
    """执行建表 SQL"""
    config = MYSQL_CONFIG.copy()
    conn = pymysql.connect(**config)

    schema_path = SQL_DIR / "schema.sql"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    cursor = conn.cursor()

    # 逐条执行（跳过 USE 和 CREATE DATABASE）
    for statement in schema_sql.split(';'):
        stmt = statement.strip()
        if not stmt:
            continue
        if stmt.upper().startswith('USE ') or stmt.upper().startswith('CREATE DATABASE'):
            continue

        # 跳过视图创建（等数据导入后再创建）
        if 'CREATE OR REPLACE VIEW' in stmt.upper():
            continue

        try:
            cursor.execute(stmt)
        except pymysql.err.OperationalError as e:
            if 'already exists' in str(e) or 'Duplicate' in str(e):
                print(f"  跳过（已存在）: {stmt[:50]}...")
            else:
                print(f"  ⚠ {e}: {stmt[:80]}...")

    conn.commit()
    cursor.close()
    print("✓ 数据表已创建")


def import_csv():
    """逐个导入 CSV 文件"""
    config = MYSQL_CONFIG.copy()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    # 先清空已有数据
    for table in reversed(list(CSV_FILES.keys())):
        try:
            cursor.execute(f"DELETE FROM {table}")
        except:
            pass
    conn.commit()

    # 按导入顺序（先导主表，再导从表）
    for table, filename in CSV_FILES.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"✗ 找不到文件: {filepath}")
            continue

        print(f"正在导入 {table}...", end=' ')
        df = pd.read_csv(filepath)

        # 日期字段特殊处理
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'timestamp' in col.lower()]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].where(df[col].notna(), None)

        # 数值字段处理
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = df[col].where(df[col].notna(), None)

        # 批量 INSERT
        cols = ', '.join(f'`{c}`' for c in df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))

        # 分批插入（每批 1000 行）
        batch_size = 1000
        total = len(df)

        for start in range(0, total, batch_size):
            batch = df.iloc[start:start + batch_size]
            values = [tuple(
                None if pd.isna(v) else (v.isoformat() if isinstance(v, pd.Timestamp) else v)
                for v in row
            ) for row in batch.itertuples(index=False)]

            sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
            cursor.executemany(sql, values)

        conn.commit()
        print(f"✓ {total} 行")

    cursor.close()
    conn.close()
    print("\n✓ 数据导入完成！")


def create_views():
    """创建分析视图"""
    config = MYSQL_CONFIG.copy()
    conn = pymysql.connect(**config)

    schema_path = SQL_DIR / "schema.sql"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    cursor = conn.cursor()

    for statement in schema_sql.split(';'):
        stmt = statement.strip()
        if 'CREATE OR REPLACE VIEW' in stmt.upper():
            try:
                cursor.execute(stmt)
                print(f"✓ 视图已创建")
            except Exception as e:
                print(f"⚠ 视图创建警告: {e}")

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Olist 数据导入 MySQL")
    print("=" * 60)
    print(f"连接目标: {MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
    print(f"数据目录: {DATA_DIR}")
    print()

    if not DATA_DIR.exists() or not any(DATA_DIR.glob('*.csv')):
        print("=" * 60)
        print("错误: data/ 目录下没有 CSV 文件！")
        print("请先下载数据集:")
        print("  python -c \"import kagglehub; print(kagglehub.dataset_download('olistbr/brazilian-ecommerce'))\"")
        print("然后将 CSV 文件复制到 data/ 目录")
        print("=" * 60)
        sys.exit(1)

    try:
        create_database()
        execute_schema()
        import_csv()
        create_views()
        print("\n🎉 全部完成！MySQL 中已有完整的 Olist 分析数据库")
        print("\n可以运行 Streamlit 查看 SQL 分析结果:")
        print("  streamlit run app.py")
    except pymysql.err.OperationalError as e:
        print(f"\n❌ MySQL 连接失败: {e}")
        print("\n请检查:")
        print("1. MySQL 服务是否启动（services.msc → MySQL80）")
        print("2. 用户名密码是否正确（修改脚本中的 MYSQL_CONFIG）")
        print("3. 端口 3306 是否被占用")
