-- ============================================================
-- DWD 层 (Data Warehouse Detail)
-- 对 ODS 数据进行清洗、标准化、维度建模
-- 表命名: dwd_{事实表} / dim_{维度表}
-- ============================================================

USE olist_supply_chain;

-- ============================================================
-- 维度表: dim_customers (客户维度)
-- 去重后的唯一客户，保留核心地理信息
-- ============================================================
DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    customer_unique_id      VARCHAR(64)  NOT NULL COMMENT '客户唯一ID（主键）',
    customer_state          VARCHAR(2)   COMMENT '所属州',
    customer_city           VARCHAR(100) COMMENT '城市',
    customer_zip_prefix     VARCHAR(10)  COMMENT '邮编前缀',
    first_purchase_date     DATE         COMMENT '首次购买日期',
    total_orders            INT DEFAULT 0 COMMENT '累计订单数',
    PRIMARY KEY (customer_unique_id),
    INDEX idx_dim_cust_state (customer_state)
) COMMENT 'DWD层-客户维度表';

-- ============================================================
-- 维度表: dim_products (商品维度)
-- 翻译品类名，补充体积、重量等供应链属性
-- ============================================================
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    product_id               VARCHAR(64)   NOT NULL COMMENT '商品ID',
    product_category_name    VARCHAR(100)  COMMENT '葡语品类名',
    category_name_english    VARCHAR(100)  COMMENT '英语品类名',
    product_weight_g         DECIMAL(10,2) COMMENT '重量(g)',
    product_length_cm       DECIMAL(10,2) COMMENT '长度(cm)',
    product_height_cm       DECIMAL(10,2) COMMENT '高度(cm)',
    product_width_cm        DECIMAL(10,2) COMMENT '宽度(cm)',
    product_volume_cm3      DECIMAL(10,2) COMMENT '体积(cm³)',
    product_photos_qty      INT           COMMENT '图片数量',
    PRIMARY KEY (product_id),
    INDEX idx_dim_prod_cat (category_name_english),
    INDEX idx_dim_prod_weight (product_weight_g)
) COMMENT 'DWD层-商品维度表';

-- ============================================================
-- 维度表: dim_sellers (卖家维度)
-- ============================================================
DROP TABLE IF EXISTS dim_sellers;
CREATE TABLE dim_sellers (
    seller_id           VARCHAR(64)  NOT NULL COMMENT '卖家ID',
    seller_state        VARCHAR(2)   COMMENT '所属州',
    seller_city         VARCHAR(100) COMMENT '城市',
    seller_zip_prefix   VARCHAR(10)  COMMENT '邮编前缀',
    total_orders        INT DEFAULT 0 COMMENT '累计订单数',
    total_revenue       DECIMAL(14,2) DEFAULT 0 COMMENT '累计收入',
    PRIMARY KEY (seller_id),
    INDEX idx_dim_seller_state (seller_state)
) COMMENT 'DWD层-卖家维度表';

-- ============================================================
-- 维度表: dim_dates (日期维度)
-- 生成2016-2018年每日记录，支撑时间维度分析
-- ============================================================
DROP TABLE IF EXISTS dim_dates;
CREATE TABLE `dim_dates` (
    `date_id`        DATE         NOT NULL COMMENT '日期（主键）',
    `year`           SMALLINT     COMMENT '年',
    `quarter`        TINYINT      COMMENT '季度(1-4)',
    `month`          TINYINT      COMMENT '月(1-12)',
    `month_name`     VARCHAR(10)  COMMENT '月份英文名',
    `week_of_year`   TINYINT      COMMENT '年内第几周',
    `day_of_month`   TINYINT      COMMENT '日(1-31)',
    `day_of_week`    TINYINT      COMMENT '星期几(1=周一,7=周日)',
    `day_name`       VARCHAR(10)  COMMENT '星期英文名',
    `is_weekend`     TINYINT      COMMENT '是否周末(0/1)',
    `year_month`     VARCHAR(7)   COMMENT '年-月(YYYY-MM)',
    PRIMARY KEY (`date_id`)
) COMMENT 'DWD层-日期维度表';

-- ============================================================
-- 事实表: dwd_order_detail (订单明细宽表)
-- 一条记录 = 一个订单商品行，关联所有维度
-- 核心分析表，后续 DWS/ADS 都从此表派生
-- ============================================================
DROP TABLE IF EXISTS dwd_order_detail;
CREATE TABLE dwd_order_detail (
    -- 主键
    order_id            VARCHAR(64)  NOT NULL COMMENT '订单ID',
    order_item_id       INT          NOT NULL COMMENT '订单行号',

    -- 订单维度
    order_status        VARCHAR(20)  COMMENT '订单状态',
    purchase_date       DATE         COMMENT '下单日期',
    purchase_timestamp  DATETIME     COMMENT '下单时间戳',
    delivered_date      DATE         COMMENT '签收日期',
    delivered_timestamp DATETIME     COMMENT '签收时间戳',
    estimated_date      DATE         COMMENT '预估送达日期',

    -- 交付时效特征（核心派生字段）
    delivery_days       INT          COMMENT '交付时长(天)',
    carrier_days        INT          COMMENT '承运时长(天)',
    is_delayed          TINYINT      COMMENT '是否延迟(1=延迟)',
    delay_days          INT          COMMENT '延迟天数',

    -- 时间维度
    purchase_year       SMALLINT     COMMENT '下单年份',
    purchase_month      TINYINT      COMMENT '下单月份',
    purchase_year_month VARCHAR(7)   COMMENT '下单年月(YYYY-MM)',
    purchase_dayofweek  TINYINT      COMMENT '下单星期(1-7)',
    is_weekend          TINYINT      COMMENT '是否周末下单',

    -- 客户维度
    customer_unique_id  VARCHAR(64)  COMMENT '客户唯一ID',
    customer_state      VARCHAR(2)   COMMENT '客户所在州',

    -- 商品维度
    product_id          VARCHAR(64)  COMMENT '商品ID',
    category_name       VARCHAR(100) COMMENT '品类名(英文)',
    product_weight_g    DECIMAL(10,2) COMMENT '商品重量(g)',

    -- 卖家维度
    seller_id           VARCHAR(64)  COMMENT '卖家ID',
    seller_state        VARCHAR(2)   COMMENT '卖家所在州',

    -- 交易字段
    price               DECIMAL(10,2) COMMENT '商品单价',
    freight_value       DECIMAL(10,2) COMMENT '运费',

    -- 支付字段（订单级聚合）
    payment_value       DECIMAL(10,2) COMMENT '订单总支付金额',
    payment_type        VARCHAR(20)   COMMENT '支付方式',

    -- 评价字段
    review_score        INT           COMMENT '评分(1-5)',

    -- 审计
    etl_date            DATE          COMMENT 'ETL日期',

    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_dwd_od_date (purchase_date),
    INDEX idx_dwd_od_status (order_status),
    INDEX idx_dwd_od_delivery (delivery_days),
    INDEX idx_dwd_od_delayed (is_delayed),
    INDEX idx_dwd_od_product (product_id),
    INDEX idx_dwd_od_category (category_name),
    INDEX idx_dwd_od_customer (customer_unique_id),
    INDEX idx_dwd_od_seller (seller_id),
    INDEX idx_dwd_od_ym (purchase_year_month),
    INDEX idx_dwd_od_cust_state (customer_state)
) COMMENT 'DWD层-订单明细宽表（核心事实表，一条=一个订单商品行）';
