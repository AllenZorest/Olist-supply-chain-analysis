-- ============================================================
-- Olist 电商数据库 Schema
-- 模拟真实企业数据仓库的表结构设计
-- 兼容 MySQL 8.0+
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS olist_supply_chain
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE olist_supply_chain;

-- ============================================================
-- 1. 客户表 (customers)
-- 业务场景：记录客户基本信息，用于区域分析、RFM分层
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id            VARCHAR(64) NOT NULL COMMENT '客户ID（每笔订单唯一）',
    customer_unique_id     VARCHAR(64) NOT NULL COMMENT '客户唯一ID（同一人多次购买不变）',
    customer_zip_code_prefix INT       COMMENT '邮编前缀',
    customer_city          VARCHAR(100) COMMENT '城市',
    customer_state         VARCHAR(2)  COMMENT '州（缩写，如SP）',
    PRIMARY KEY (customer_id),
    INDEX idx_customer_unique (customer_unique_id),
    INDEX idx_customer_state (customer_state)
) COMMENT '客户信息表';

-- ============================================================
-- 2. 卖家/供应商表 (sellers)
-- 业务场景：供应商维度分析交付时效、商品结构
-- ============================================================
CREATE TABLE IF NOT EXISTS sellers (
    seller_id              VARCHAR(64) NOT NULL COMMENT '卖家ID',
    seller_zip_code_prefix INT         COMMENT '邮编前缀',
    seller_city            VARCHAR(100) COMMENT '城市',
    seller_state           VARCHAR(2)  COMMENT '州',
    PRIMARY KEY (seller_id),
    INDEX idx_seller_state (seller_state)
) COMMENT '卖家/供应商信息表';

-- ============================================================
-- 3. 商品表 (products)
-- 业务场景：SKU管理、品类分析
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    product_id                  VARCHAR(64)  NOT NULL COMMENT '商品ID',
    product_category_name       VARCHAR(100) COMMENT '品类名（葡语）',
    product_name_length         INT          COMMENT '商品名长度',
    product_description_length  INT          COMMENT '描述长度',
    product_photos_qty          INT          COMMENT '图片数量',
    product_weight_g            DECIMAL(10,2) COMMENT '重量（克）',
    product_length_cm           DECIMAL(10,2) COMMENT '长度（厘米）',
    product_height_cm           DECIMAL(10,2) COMMENT '高度（厘米）',
    product_width_cm            DECIMAL(10,2) COMMENT '宽度（厘米）',
    PRIMARY KEY (product_id),
    INDEX idx_category (product_category_name),
    INDEX idx_weight (product_weight_g)
) COMMENT '商品信息表';

-- ============================================================
-- 4. 品类翻译表 (product_category_translation)
-- 业务场景：葡语品类名 → 英语品类名
-- ============================================================
CREATE TABLE IF NOT EXISTS product_category_translation (
    product_category_name          VARCHAR(100) NOT NULL COMMENT '葡语品类名',
    product_category_name_english  VARCHAR(100) COMMENT '英语品类名',
    PRIMARY KEY (product_category_name)
) COMMENT '品类名翻译表';

-- ============================================================
-- 5. 订单表 (orders)
-- 业务场景：核心交易表，含完整的时间链路
--   下单 → 审核 → 交付给承运商 → 客户签收
--   这些时间戳是供应链时效分析的核心
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id                        VARCHAR(64) NOT NULL COMMENT '订单ID',
    customer_id                     VARCHAR(64) NOT NULL COMMENT '客户ID',
    order_status                    VARCHAR(20) COMMENT '订单状态',
    order_purchase_timestamp        DATETIME    COMMENT '下单时间',
    order_approved_at               DATETIME    COMMENT '审核时间',
    order_delivered_carrier_date    DATETIME    COMMENT '交付给承运商时间',
    order_delivered_customer_date   DATETIME    COMMENT '客户签收时间',
    order_estimated_delivery_date   DATETIME    COMMENT '预估到达时间（用于判断是否延迟）',
    PRIMARY KEY (order_id),
    INDEX idx_customer (customer_id),
    INDEX idx_purchase_time (order_purchase_timestamp),
    INDEX idx_status (order_status),
    INDEX idx_delivered_time (order_delivered_customer_date),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
) COMMENT '订单主表（含完整物流时间链路）';

-- ============================================================
-- 6. 订单商品表 (order_items)
-- 业务场景：一笔订单可能包含多个商品，拆分行记录
-- ============================================================
CREATE TABLE IF NOT EXISTS order_items (
    order_id                VARCHAR(64)  NOT NULL COMMENT '订单ID',
    order_item_id           INT          NOT NULL COMMENT '订单内的行号',
    product_id              VARCHAR(64)  NOT NULL COMMENT '商品ID',
    seller_id               VARCHAR(64)  NOT NULL COMMENT '卖家ID',
    shipping_limit_date     DATETIME     COMMENT '最晚发货日期',
    price                   DECIMAL(10,2) COMMENT '商品单价',
    freight_value           DECIMAL(10,2) COMMENT '运费',
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_product (product_id),
    INDEX idx_seller (seller_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
) COMMENT '订单商品明细表';

-- ============================================================
-- 7. 订单支付表 (order_payments)
-- 业务场景：支付方式分析、客单价统计
-- ============================================================
CREATE TABLE IF NOT EXISTS order_payments (
    order_id              VARCHAR(64)  NOT NULL COMMENT '订单ID',
    payment_sequential    INT          NOT NULL COMMENT '支付序号（分期时为1,2,3...）',
    payment_type          VARCHAR(20)  COMMENT '支付方式',
    payment_installments  INT          COMMENT '分期数',
    payment_value         DECIMAL(10,2) COMMENT '支付金额',
    PRIMARY KEY (order_id, payment_sequential),
    INDEX idx_payment_type (payment_type),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
) COMMENT '订单支付表';

-- ============================================================
-- 8. 订单评价表 (order_reviews)
-- 业务场景：客户满意度分析，与物流时效关联分析
-- ============================================================
CREATE TABLE IF NOT EXISTS order_reviews (
    review_id               VARCHAR(64) NOT NULL COMMENT '评价ID',
    order_id                VARCHAR(64) NOT NULL COMMENT '订单ID',
    review_score            INT         COMMENT '评分（1-5）',
    review_comment_title    TEXT        COMMENT '评价标题',
    review_comment_message  TEXT        COMMENT '评价内容',
    review_creation_date    DATETIME    COMMENT '评价创建时间',
    review_answer_timestamp DATETIME    COMMENT '商家回复时间',
    PRIMARY KEY (review_id, order_id),
    INDEX idx_order (order_id),
    INDEX idx_score (review_score),
    INDEX idx_review_time (review_creation_date),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
) COMMENT '订单评价表';

-- ============================================================
-- 9. 创建分析视图（模拟数据仓库中的宽表）
-- 业务场景：实际工作中会建视图方便日常取数
-- ============================================================
CREATE OR REPLACE VIEW v_order_full AS
SELECT
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    -- 交付时效特征
    DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp) AS delivery_days,
    DATEDIFF(o.order_delivered_customer_date, o.order_delivered_carrier_date) AS carrier_days,
    CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1
        ELSE 0
    END AS is_delayed,
    GREATEST(DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date), 0) AS delay_days,
    -- 时间维度
    YEAR(o.order_purchase_timestamp) AS purchase_year,
    MONTH(o.order_purchase_timestamp) AS purchase_month,
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS purchase_year_month,
    -- 客户信息
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,
    -- 商品信息
    p.product_id,
    p.product_category_name,
    COALESCE(t.product_category_name_english, p.product_category_name) AS category_name,
    p.product_weight_g,
    -- 交易信息
    oi.seller_id,
    s.seller_state,
    s.seller_city,
    oi.price,
    oi.freight_value,
    -- 支付
    op.payment_type,
    op.payment_installments,
    op.payment_value
FROM orders o
LEFT JOIN order_items oi     ON o.order_id = oi.order_id
LEFT JOIN products p         ON oi.product_id = p.product_id
LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
LEFT JOIN sellers s          ON oi.seller_id = s.seller_id
LEFT JOIN customers c        ON o.customer_id = c.customer_id
LEFT JOIN (
    -- 订单可能分多期支付，取总额
    SELECT order_id,
           MAX(payment_type) AS payment_type,
           MAX(payment_installments) AS payment_installments,
           SUM(payment_value) AS payment_value
    FROM order_payments
    GROUP BY order_id
) op ON o.order_id = op.order_id;
