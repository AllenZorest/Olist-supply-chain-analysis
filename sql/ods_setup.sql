-- ============================================================
-- ODS 层 (Operational Data Store)
-- 原始 CSV 原样入库，不做任何清洗和转换
-- 表命名: ods_{业务表名}
-- 新增审计字段: etl_date（数据入库日期）
-- ============================================================

USE olist_supply_chain;

-- -------------------------------------------------------
-- 1. ods_customers — 客户原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_customers;
CREATE TABLE ods_customers (
    customer_id            VARCHAR(64)  COMMENT '客户ID',
    customer_unique_id     VARCHAR(64)  COMMENT '客户唯一ID',
    customer_zip_code_prefix VARCHAR(10) COMMENT '邮编前缀',
    customer_city          VARCHAR(100) COMMENT '城市',
    customer_state         VARCHAR(2)   COMMENT '州缩写',
    etl_date               DATE         COMMENT 'ETL日期',
    PRIMARY KEY (customer_id),
    INDEX idx_ods_cust_uid (customer_unique_id),
    INDEX idx_ods_cust_state (customer_state)
) COMMENT 'ODS层-客户原始表';

-- -------------------------------------------------------
-- 2. ods_sellers — 卖家原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_sellers;
CREATE TABLE ods_sellers (
    seller_id              VARCHAR(64)  COMMENT '卖家ID',
    seller_zip_code_prefix VARCHAR(10) COMMENT '邮编前缀',
    seller_city            VARCHAR(100) COMMENT '城市',
    seller_state           VARCHAR(2)   COMMENT '州缩写',
    etl_date               DATE         COMMENT 'ETL日期',
    PRIMARY KEY (seller_id),
    INDEX idx_ods_seller_state (seller_state)
) COMMENT 'ODS层-卖家原始表';

-- -------------------------------------------------------
-- 3. ods_products — 商品原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_products;
CREATE TABLE ods_products (
    product_id                  VARCHAR(64)   COMMENT '商品ID',
    product_category_name       VARCHAR(100)  COMMENT '品类名（葡语）',
    product_name_length         INT           COMMENT '商品名长度',
    product_description_length  INT           COMMENT '描述长度',
    product_photos_qty          INT           COMMENT '图片数量',
    product_weight_g            DECIMAL(10,2) COMMENT '重量(g)',
    product_length_cm           DECIMAL(10,2) COMMENT '长度(cm)',
    product_height_cm           DECIMAL(10,2) COMMENT '高度(cm)',
    product_width_cm            DECIMAL(10,2) COMMENT '宽度(cm)',
    etl_date                    DATE          COMMENT 'ETL日期',
    PRIMARY KEY (product_id),
    INDEX idx_ods_prod_cat (product_category_name)
) COMMENT 'ODS层-商品原始表';

-- -------------------------------------------------------
-- 4. ods_product_category_translation — 品类翻译原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_product_category_translation;
CREATE TABLE ods_product_category_translation (
    product_category_name          VARCHAR(100) COMMENT '葡语品类名',
    product_category_name_english  VARCHAR(100) COMMENT '英语品类名',
    etl_date                       DATE         COMMENT 'ETL日期',
    PRIMARY KEY (product_category_name)
) COMMENT 'ODS层-品类翻译原始表';

-- -------------------------------------------------------
-- 5. ods_orders — 订单原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_orders;
CREATE TABLE ods_orders (
    order_id                        VARCHAR(64) COMMENT '订单ID',
    customer_id                     VARCHAR(64) COMMENT '客户ID',
    order_status                    VARCHAR(20) COMMENT '订单状态',
    order_purchase_timestamp        VARCHAR(30) COMMENT '下单时间（原样存为字符串）',
    order_approved_at               VARCHAR(30) COMMENT '审核时间',
    order_delivered_carrier_date    VARCHAR(30) COMMENT '交付承运商时间',
    order_delivered_customer_date   VARCHAR(30) COMMENT '客户签收时间',
    order_estimated_delivery_date   VARCHAR(30) COMMENT '预估送达时间',
    etl_date                        DATE        COMMENT 'ETL日期',
    PRIMARY KEY (order_id),
    INDEX idx_ods_order_status (order_status)
) COMMENT 'ODS层-订单原始表（日期字段按原样存储）';

-- -------------------------------------------------------
-- 6. ods_order_items — 订单商品原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_order_items;
CREATE TABLE ods_order_items (
    order_id             VARCHAR(64)   COMMENT '订单ID',
    order_item_id        INT           COMMENT '订单行号',
    product_id           VARCHAR(64)   COMMENT '商品ID',
    seller_id            VARCHAR(64)   COMMENT '卖家ID',
    shipping_limit_date  VARCHAR(30)   COMMENT '最晚发货日期',
    price                DECIMAL(10,2) COMMENT '单价',
    freight_value        DECIMAL(10,2) COMMENT '运费',
    etl_date             DATE          COMMENT 'ETL日期',
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_ods_oi_product (product_id),
    INDEX idx_ods_oi_seller (seller_id)
) COMMENT 'ODS层-订单商品原始表';

-- -------------------------------------------------------
-- 7. ods_order_payments — 支付原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_order_payments;
CREATE TABLE ods_order_payments (
    order_id              VARCHAR(64)   COMMENT '订单ID',
    payment_sequential    INT           COMMENT '支付序号',
    payment_type          VARCHAR(20)   COMMENT '支付方式',
    payment_installments  INT           COMMENT '分期数',
    payment_value         DECIMAL(10,2) COMMENT '支付金额',
    etl_date              DATE          COMMENT 'ETL日期',
    PRIMARY KEY (order_id, payment_sequential),
    INDEX idx_ods_pay_type (payment_type)
) COMMENT 'ODS层-支付原始表';

-- -------------------------------------------------------
-- 8. ods_order_reviews — 评价原始表
-- -------------------------------------------------------
DROP TABLE IF EXISTS ods_order_reviews;
CREATE TABLE ods_order_reviews (
    review_id               VARCHAR(64)  COMMENT '评价ID',
    order_id                VARCHAR(64)  COMMENT '订单ID',
    review_score            INT          COMMENT '评分(1-5)',
    review_comment_title    TEXT         COMMENT '评价标题',
    review_comment_message  TEXT         COMMENT '评价内容',
    review_creation_date    VARCHAR(30)  COMMENT '评价创建时间',
    review_answer_timestamp VARCHAR(30)  COMMENT '商家回复时间',
    etl_date                DATE         COMMENT 'ETL日期',
    PRIMARY KEY (review_id, order_id),
    INDEX idx_ods_rev_order (order_id),
    INDEX idx_ods_rev_score (review_score)
) COMMENT 'ODS层-评价原始表';
