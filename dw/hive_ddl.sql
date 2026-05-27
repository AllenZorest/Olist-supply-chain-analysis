-- ============================================================
-- Olist 数仓 Hive DDL（生产级版本）
-- ============================================================
-- 用途: 将 MySQL 实现的数仓分层翻译为 Hive 版本
--       适用于 Hadoop + Hive 数仓环境（如唯品会数据仓库）
-- 执行方式: hive -f dw/hive_ddl.sql
-- ============================================================
-- MySQL vs Hive 关键差异:
--   1. VARCHAR(n) → STRING（Hive 不定长）
--   2. DATETIME → TIMESTAMP
--   3. TEXT → STRING
--   4. INDEX / FOREIGN KEY → 移除（Hive 不支持约束）
--   5. 新增 PARTITIONED BY（分区裁剪）、STORED AS PARQUET（列存）
--   6. 自增主键 → 移除（Hive 无自增概念）
-- ============================================================

CREATE DATABASE IF NOT EXISTS olist_supply_chain
  COMMENT 'Olist 巴西电商供应链数仓';

USE olist_supply_chain;

-- 开启 Parquet 压缩（snappy 速度优先，gzip 压缩率更高）
SET parquet.compression=SNAPPY;
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;


-- ============================================================
-- 第 1 层: ODS — 操作数据层（原始 CSV 原样入库）
-- ============================================================
-- 分区策略: 按 etl_date 分区（天级快照），支持历史回滚
-- 存储格式: Parquet 列存，查询时裁剪列，I/O 远小于 MySQL 行存
-- 分隔符: CSV 源用逗号，这里用 \t 是 Hive 默认（生产中常用 \001）
-- ============================================================

-- 1.1 ods_customers
DROP TABLE IF EXISTS ods_customers;
CREATE EXTERNAL TABLE ods_customers (
    customer_id            STRING  COMMENT '客户ID',
    customer_unique_id     STRING  COMMENT '客户唯一ID',
    customer_zip_code_prefix STRING COMMENT '邮编前缀',
    customer_city          STRING  COMMENT '城市',
    customer_state         STRING  COMMENT '州缩写'
)
COMMENT 'ODS层-客户原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.2 ods_sellers
DROP TABLE IF EXISTS ods_sellers;
CREATE EXTERNAL TABLE ods_sellers (
    seller_id              STRING  COMMENT '卖家ID',
    seller_zip_code_prefix STRING  COMMENT '邮编前缀',
    seller_city            STRING  COMMENT '城市',
    seller_state           STRING  COMMENT '州缩写'
)
COMMENT 'ODS层-卖家原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.3 ods_products
DROP TABLE IF EXISTS ods_products;
CREATE EXTERNAL TABLE ods_products (
    product_id                  STRING  COMMENT '商品ID',
    product_category_name       STRING  COMMENT '品类名（葡语）',
    product_name_length         INT     COMMENT '商品名长度',
    product_description_length  INT     COMMENT '描述长度',
    product_photos_qty          INT     COMMENT '图片数量',
    product_weight_g            DECIMAL(10,2) COMMENT '重量(g)',
    product_length_cm           DECIMAL(10,2) COMMENT '长度(cm)',
    product_height_cm           DECIMAL(10,2) COMMENT '高度(cm)',
    product_width_cm            DECIMAL(10,2) COMMENT '宽度(cm)'
)
COMMENT 'ODS层-商品原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.4 ods_product_category_translation
DROP TABLE IF EXISTS ods_product_category_translation;
CREATE EXTERNAL TABLE ods_product_category_translation (
    product_category_name          STRING COMMENT '葡语品类名',
    product_category_name_english  STRING COMMENT '英语品类名'
)
COMMENT 'ODS层-品类翻译原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.5 ods_orders
DROP TABLE IF EXISTS ods_orders;
CREATE EXTERNAL TABLE ods_orders (
    order_id                        STRING  COMMENT '订单ID',
    customer_id                     STRING  COMMENT '客户ID',
    order_status                    STRING  COMMENT '订单状态',
    order_purchase_timestamp        STRING  COMMENT '下单时间（源数据为字符串，后续ETL转时间戳）',
    order_approved_at               STRING  COMMENT '审核时间',
    order_delivered_carrier_date    STRING  COMMENT '交付承运商时间',
    order_delivered_customer_date   STRING  COMMENT '客户签收时间',
    order_estimated_delivery_date   STRING  COMMENT '预估送达时间'
)
COMMENT 'ODS层-订单原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.6 ods_order_items
DROP TABLE IF EXISTS ods_order_items;
CREATE EXTERNAL TABLE ods_order_items (
    order_id             STRING        COMMENT '订单ID',
    order_item_id        INT           COMMENT '订单行号',
    product_id           STRING        COMMENT '商品ID',
    seller_id            STRING        COMMENT '卖家ID',
    shipping_limit_date  STRING        COMMENT '最晚发货日期',
    price                DECIMAL(10,2) COMMENT '单价',
    freight_value        DECIMAL(10,2) COMMENT '运费'
)
COMMENT 'ODS层-订单商品原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.7 ods_order_payments
DROP TABLE IF EXISTS ods_order_payments;
CREATE EXTERNAL TABLE ods_order_payments (
    order_id              STRING        COMMENT '订单ID',
    payment_sequential    INT           COMMENT '支付序号',
    payment_type          STRING        COMMENT '支付方式',
    payment_installments  INT           COMMENT '分期数',
    payment_value         DECIMAL(10,2) COMMENT '支付金额'
)
COMMENT 'ODS层-支付原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;

-- 1.8 ods_order_reviews
DROP TABLE IF EXISTS ods_order_reviews;
CREATE EXTERNAL TABLE ods_order_reviews (
    review_id               STRING  COMMENT '评价ID',
    order_id                STRING  COMMENT '订单ID',
    review_score            INT     COMMENT '评分(1-5)',
    review_comment_title    STRING  COMMENT '评价标题',
    review_comment_message  STRING  COMMENT '评价内容',
    review_creation_date    STRING  COMMENT '评价创建时间',
    review_answer_timestamp STRING  COMMENT '商家回复时间'
)
COMMENT 'ODS层-评价原始表'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
STORED AS PARQUET;


-- ============================================================
-- 第 2 层: DWD — 明细数据层（清洗 + 维度建模）
-- ============================================================
-- 维度表不分区（数据量小，全量加载即可）
-- 事实表按业务时间分区（按月），支持时间范围查询裁剪
-- ============================================================

-- 2.1 dim_customers（客户维度）
DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    customer_unique_id      STRING  COMMENT '客户唯一ID',
    customer_state          STRING  COMMENT '所属州',
    customer_city           STRING  COMMENT '城市',
    customer_zip_prefix     STRING  COMMENT '邮编前缀',
    first_purchase_date     DATE    COMMENT '首次购买日期',
    total_orders            INT     COMMENT '累计订单数'
)
COMMENT 'DWD层-客户维度表'
STORED AS PARQUET;

-- 2.2 dim_products（商品维度）
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_id               STRING        COMMENT '商品ID',
    product_category_name    STRING        COMMENT '葡语品类名',
    category_name_english    STRING        COMMENT '英语品类名',
    product_weight_g         DECIMAL(10,2) COMMENT '重量(g)',
    product_volume_cm3       DECIMAL(10,2) COMMENT '体积(cm³)',
    product_photos_qty       INT           COMMENT '图片数量'
)
COMMENT 'DWD层-商品维度表'
STORED AS PARQUET;

-- 2.3 dim_sellers（卖家维度）
DROP TABLE IF EXISTS dim_sellers;
CREATE TABLE dim_sellers (
    seller_id           STRING        COMMENT '卖家ID',
    seller_state        STRING        COMMENT '所属州',
    seller_city         STRING        COMMENT '城市',
    seller_zip_prefix   STRING        COMMENT '邮编前缀',
    total_orders        INT           COMMENT '累计订单数',
    total_revenue       DECIMAL(14,2) COMMENT '累计收入'
)
COMMENT 'DWD层-卖家维度表'
STORED AS PARQUET;

-- 2.4 dim_dates（日期维度）
DROP TABLE IF EXISTS dim_dates;
CREATE TABLE dim_dates (
    date_id        DATE    COMMENT '日期',
    year           SMALLINT COMMENT '年',
    quarter        TINYINT  COMMENT '季度(1-4)',
    month          TINYINT  COMMENT '月(1-12)',
    month_name     STRING   COMMENT '月份英文名',
    week_of_year   TINYINT  COMMENT '年内第几周',
    day_of_month   TINYINT  COMMENT '日(1-31)',
    day_of_week    TINYINT  COMMENT '星期几(1=周一,7=周日)',
    day_name       STRING   COMMENT '星期英文名',
    is_weekend     TINYINT  COMMENT '是否周末(0/1)',
    year_month     STRING   COMMENT '年-月(YYYY-MM)'
)
COMMENT 'DWD层-日期维度表（2016-2018）'
STORED AS PARQUET;

-- 2.5 dwd_order_detail（订单明细宽表 — 核心事实表）
-- 分区策略: 按月分区 purchase_year_month，典型数仓做法
-- 一条记录 = 一个已完成订单的商品行
DROP TABLE IF EXISTS dwd_order_detail;
CREATE TABLE dwd_order_detail (
    -- 主键（Hive 中仅作标识，无约束）
    order_id            STRING  COMMENT '订单ID',
    order_item_id       INT     COMMENT '订单行号',

    -- 订单维度
    order_status        STRING  COMMENT '订单状态',
    purchase_date       DATE    COMMENT '下单日期',
    purchase_timestamp  TIMESTAMP COMMENT '下单时间戳',
    delivered_date      DATE    COMMENT '签收日期',
    delivered_timestamp TIMESTAMP COMMENT '签收时间戳',
    estimated_date      DATE    COMMENT '预估送达日期',

    -- 交付时效特征（核心派生字段）
    delivery_days       INT     COMMENT '交付时长(天)',
    carrier_days        INT     COMMENT '承运时长(天)',
    is_delayed          TINYINT COMMENT '是否延迟(1=延迟)',
    delay_days          INT     COMMENT '延迟天数',

    -- 时间维度
    purchase_year       SMALLINT COMMENT '下单年份',
    purchase_month      TINYINT  COMMENT '下单月份',
    purchase_dayofweek  TINYINT  COMMENT '下单星期(1-7)',
    is_weekend          TINYINT  COMMENT '是否周末下单',

    -- 客户维度
    customer_unique_id  STRING  COMMENT '客户唯一ID',
    customer_state      STRING  COMMENT '客户所在州',

    -- 商品维度
    product_id          STRING        COMMENT '商品ID',
    category_name       STRING        COMMENT '品类名(英文)',
    product_weight_g    DECIMAL(10,2) COMMENT '商品重量(g)',

    -- 卖家维度
    seller_id           STRING  COMMENT '卖家ID',
    seller_state        STRING  COMMENT '卖家所在州',

    -- 交易字段
    price               DECIMAL(10,2) COMMENT '商品单价',
    freight_value       DECIMAL(10,2) COMMENT '运费',

    -- 支付字段（订单级聚合）
    payment_value       DECIMAL(10,2) COMMENT '订单总支付金额',
    payment_type        STRING        COMMENT '支付方式',

    -- 评价字段
    review_score        INT     COMMENT '评分(1-5)'
)
COMMENT 'DWD层-订单明细宽表（核心事实表）'
PARTITIONED BY (purchase_year_month STRING COMMENT '下单年月(YYYY-MM)')
STORED AS PARQUET;


-- ============================================================
-- 第 3 层: DWS — 汇总数据层（日/周/品类/州多粒度聚合）
-- ============================================================
-- 日度表按 etl_date 分区，汇总表不分区（行数少）
-- ============================================================

-- 3.1 dws_daily_metrics（日度核心指标）
DROP TABLE IF EXISTS dws_daily_metrics;
CREATE TABLE dws_daily_metrics (
    purchase_date       DATE          COMMENT '下单日期',
    total_orders        INT           COMMENT '订单总量',
    total_items         INT           COMMENT '商品总件数',
    total_gmv           DECIMAL(16,2) COMMENT 'GMV(订单总金额)',
    total_revenue       DECIMAL(16,2) COMMENT '商品收入(不含运费)',
    total_freight       DECIMAL(16,2) COMMENT '运费总额',
    avg_order_value     DECIMAL(10,2) COMMENT '客单价',
    delivered_orders    INT           COMMENT '已签收订单数',
    avg_delivery_days   DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate          DECIMAL(6,4)  COMMENT '延迟率',
    avg_delay_days      DECIMAL(6,2)  COMMENT '平均延迟天数',
    avg_review_score    DECIMAL(4,2)  COMMENT '平均评分',
    unique_customers    INT           COMMENT '下单用户数',
    unique_sellers      INT           COMMENT '活跃卖家数'
)
COMMENT 'DWS层-日度核心指标汇总'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
STORED AS PARQUET;

-- 3.2 dws_daily_category（日度品类汇总）
DROP TABLE IF EXISTS dws_daily_category;
CREATE TABLE dws_daily_category (
    purchase_date        DATE          COMMENT '下单日期',
    category_name        STRING        COMMENT '品类名(英文)',
    total_orders         INT           COMMENT '订单数',
    total_gmv            DECIMAL(14,2) COMMENT 'GMV',
    total_revenue        DECIMAL(14,2) COMMENT '商品收入',
    avg_price            DECIMAL(10,2) COMMENT '均价',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分'
)
COMMENT 'DWS层-日度品类汇总'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
STORED AS PARQUET;

-- 3.3 dws_daily_state（日度州级汇总）
DROP TABLE IF EXISTS dws_daily_state;
CREATE TABLE dws_daily_state (
    purchase_date        DATE          COMMENT '下单日期',
    state                STRING        COMMENT '客户州缩写',
    total_orders         INT           COMMENT '订单数',
    total_gmv            DECIMAL(14,2) COMMENT 'GMV',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分'
)
COMMENT 'DWS层-日度州级汇总'
PARTITIONED BY (etl_date STRING COMMENT 'ETL日期(YYYY-MM-DD)')
STORED AS PARQUET;

-- 3.4 dws_weekly_metrics（周度核心指标 — 小表，不分区）
DROP TABLE IF EXISTS dws_weekly_metrics;
CREATE TABLE dws_weekly_metrics (
    year_week           STRING        COMMENT '年-周(YYYY-Www)',
    week_start_date     DATE          COMMENT '周起始日(周一)',
    week_end_date       DATE          COMMENT '周结束日(周日)',
    total_orders        INT           COMMENT '周订单总量',
    total_gmv           DECIMAL(16,2) COMMENT '周GMV',
    avg_daily_orders    DECIMAL(8,1)  COMMENT '日均订单数',
    avg_delivery_days   DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate          DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score    DECIMAL(4,2)  COMMENT '平均评分'
)
COMMENT 'DWS层-周度核心指标汇总'
STORED AS PARQUET;

-- 3.5 dws_category_summary（品类全局汇总 — 含 ABC 分类）
DROP TABLE IF EXISTS dws_category_summary;
CREATE TABLE dws_category_summary (
    category_name        STRING        COMMENT '品类名',
    total_orders         INT           COMMENT '累计订单数',
    total_gmv            DECIMAL(14,2) COMMENT '累计GMV',
    total_revenue        DECIMAL(14,2) COMMENT '累计收入(不含运费)',
    avg_price            DECIMAL(10,2) COMMENT '均价',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    revenue_pct          DECIMAL(6,4)  COMMENT '收入占比',
    cumulative_pct       DECIMAL(6,4)  COMMENT '累计收入占比(ABC分析)',
    abc_class            STRING        COMMENT 'ABC分类(A/B/C)',
    unique_sellers       INT           COMMENT '卖家数',
    daily_avg_items      DECIMAL(8,1)  COMMENT '日均销量'
)
COMMENT 'DWS层-品类全局汇总（含ABC分类）'
STORED AS PARQUET;

-- 3.6 dws_state_summary（州级全局汇总）
DROP TABLE IF EXISTS dws_state_summary;
CREATE TABLE dws_state_summary (
    state                STRING        COMMENT '州缩写',
    total_orders         INT           COMMENT '累计订单数',
    total_gmv            DECIMAL(14,2) COMMENT '累计GMV',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    unique_customers     INT           COMMENT '下单用户数'
)
COMMENT 'DWS层-州级全局汇总'
STORED AS PARQUET;


-- ============================================================
-- 附录: Hive ETL 示例（从 ODS 到 DWD 的 INSERT 语法）
-- ============================================================
-- 注意: Hive 的 INSERT 和 MySQL 有差异
--   1. 使用 INSERT OVERWRITE TABLE ... PARTITION (key)
--   2. 字符串转日期: TO_DATE()、UNIX_TIMESTAMP() 替代 MySQL 的 DATE()
--   3. 日期差: DATEDIFF() 支持但不完全相同
--   4. 不支持 MySQL 的 DATE_FORMAT() → 用 FROM_UNIXTIME() 或 DATE_FORMAT()
--   5. 窗口函数、CASE WHEN 语法一致
-- ============================================================

/*
-- 示例: ODS → DWD dwd_order_detail（核心宽表构建）
-- 对比 MySQL 版本 (run_all.py)，核心变化:
--   - STR_TO_DATE() → TO_DATE() / CAST(... AS TIMESTAMP)
--   - DATE_FORMAT() → DATE_FORMAT() (Hive 也支持，但格式不同)
--   - DAYOFWEEK() → DAYOFWEEK() (Hive: 1=周日，MySQL: 1=周日，基本一致)

INSERT OVERWRITE TABLE dwd_order_detail
PARTITION (purchase_year_month)
SELECT
    o.order_id,
    oi.order_item_id,
    o.order_status,
    TO_DATE(o.order_purchase_timestamp)      AS purchase_date,
    CAST(o.order_purchase_timestamp AS TIMESTAMP)  AS purchase_timestamp,
    TO_DATE(o.order_delivered_customer_date) AS delivered_date,
    CAST(o.order_delivered_customer_date AS TIMESTAMP) AS delivered_timestamp,
    TO_DATE(o.order_estimated_delivery_date) AS estimated_date,

    -- 交付时效特征
    DATEDIFF(TO_DATE(o.order_delivered_customer_date), TO_DATE(o.order_purchase_timestamp)) AS delivery_days,
    DATEDIFF(TO_DATE(o.order_delivered_customer_date), TO_DATE(o.order_delivered_carrier_date)) AS carrier_days,
    CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END AS is_delayed,
    GREATEST(DATEDIFF(TO_DATE(o.order_delivered_customer_date), TO_DATE(o.order_estimated_delivery_date)), 0) AS delay_days,

    -- 时间维度
    YEAR(TO_DATE(o.order_purchase_timestamp))  AS purchase_year,
    MONTH(TO_DATE(o.order_purchase_timestamp)) AS purchase_month,
    DAYOFWEEK(TO_DATE(o.order_purchase_timestamp)) AS purchase_dayofweek,
    CASE WHEN DAYOFWEEK(TO_DATE(o.order_purchase_timestamp)) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend,

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

    -- 分区键（必须放最后）
    DATE_FORMAT(TO_DATE(o.order_purchase_timestamp), 'yyyy-MM') AS purchase_year_month
FROM ods_orders o
INNER JOIN ods_order_items oi ON o.order_id = oi.order_id
LEFT JOIN ods_customers c ON o.customer_id = c.customer_id
LEFT JOIN dim_products dp ON oi.product_id = dp.product_id
LEFT JOIN ods_sellers s ON oi.seller_id = s.seller_id
LEFT JOIN (
    SELECT order_id,
           SUM(payment_value) AS payment_value,
           MAX(payment_type)  AS payment_type
    FROM ods_order_payments
    GROUP BY order_id
) op ON o.order_id = op.order_id
LEFT JOIN ods_order_reviews r ON o.order_id = r.order_id
WHERE o.order_status IN ('delivered', 'shipped')
  AND o.order_purchase_timestamp IS NOT NULL
  AND o.order_delivered_customer_date IS NOT NULL;
*/
