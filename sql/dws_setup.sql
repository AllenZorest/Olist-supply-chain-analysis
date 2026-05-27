-- ============================================================
-- DWS 层 (Data Warehouse Summary)
-- 从 DWD 层聚合，按日/周/月汇总核心业务指标
-- 表命名: dws_{粒度}_{主题}
-- ============================================================

USE olist_supply_chain;

-- ============================================================
-- 1. dws_daily_metrics — 日度核心指标汇总
-- 粒度: 每天一行
-- ============================================================
DROP TABLE IF EXISTS dws_daily_metrics;
CREATE TABLE dws_daily_metrics (
    purchase_date       DATE          NOT NULL COMMENT '下单日期',
    total_orders        INT           COMMENT '订单总量',
    total_items          INT           COMMENT '商品总件数',
    total_gmv           DECIMAL(16,2) COMMENT 'GMV(订单总金额)',
    total_revenue        DECIMAL(16,2) COMMENT '商品收入(不含运费)',
    total_freight        DECIMAL(16,2) COMMENT '运费总额',
    avg_order_value      DECIMAL(10,2) COMMENT '客单价',
    delivered_orders     INT           COMMENT '已签收订单数',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_delay_days       DECIMAL(6,2)  COMMENT '平均延迟天数',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    unique_customers     INT           COMMENT '下单用户数',
    unique_sellers       INT           COMMENT '活跃卖家数',
    etl_date             DATE          COMMENT 'ETL日期',
    PRIMARY KEY (purchase_date),
    INDEX idx_dws_daily_gmv (total_gmv)
) COMMENT 'DWS层-日度核心指标汇总';

-- ============================================================
-- 2. dws_daily_category — 日度品类汇总
-- 粒度: 每一天 × 每一品类
-- ============================================================
DROP TABLE IF EXISTS dws_daily_category;
CREATE TABLE dws_daily_category (
    purchase_date        DATE          NOT NULL COMMENT '下单日期',
    category_name        VARCHAR(100)  NOT NULL COMMENT '品类名(英文)',
    total_orders          INT           COMMENT '订单数',
    total_gmv            DECIMAL(14,2) COMMENT 'GMV',
    total_revenue         DECIMAL(14,2) COMMENT '商品收入',
    avg_price            DECIMAL(10,2) COMMENT '均价',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    etl_date              DATE          COMMENT 'ETL日期',
    PRIMARY KEY (purchase_date, category_name),
    INDEX idx_dws_dc_cat (category_name),
    INDEX idx_dws_dc_date (purchase_date)
) COMMENT 'DWS层-日度品类汇总';

-- ============================================================
-- 3. dws_daily_state — 日度州级汇总
-- 粒度: 每一天 × 每一客户州
-- ============================================================
DROP TABLE IF EXISTS dws_daily_state;
CREATE TABLE dws_daily_state (
    purchase_date        DATE         NOT NULL COMMENT '下单日期',
    state                VARCHAR(2)   NOT NULL COMMENT '客户州缩写',
    total_orders          INT          COMMENT '订单数',
    total_gmv            DECIMAL(14,2) COMMENT 'GMV',
    avg_delivery_days    DECIMAL(6,2) COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4) COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2) COMMENT '平均评分',
    etl_date              DATE         COMMENT 'ETL日期',
    PRIMARY KEY (purchase_date, state),
    INDEX idx_dws_ds_state (state)
) COMMENT 'DWS层-日度州级汇总';

-- ============================================================
-- 4. dws_weekly_metrics — 周度核心指标汇总
-- 粒度: 每周一行，从 dim_dates 获取周
-- ============================================================
DROP TABLE IF EXISTS dws_weekly_metrics;
CREATE TABLE dws_weekly_metrics (
    year_week           VARCHAR(7)    NOT NULL COMMENT '年-周(YYYY-WW)',
    week_start_date     DATE          COMMENT '周起始日(周一)',
    week_end_date       DATE          COMMENT '周结束日(周日)',
    total_orders         INT           COMMENT '周订单总量',
    total_gmv            DECIMAL(16,2) COMMENT '周GMV',
    avg_daily_orders     DECIMAL(8,1)  COMMENT '日均订单数',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    etl_date              DATE          COMMENT 'ETL日期',
    PRIMARY KEY (year_week)
) COMMENT 'DWS层-周度核心指标汇总';

-- ============================================================
-- 5. dws_category_summary — 品类全局汇总（全时段）
-- 粒度: 每一品类一行，全局统计
-- ============================================================
DROP TABLE IF EXISTS dws_category_summary;
CREATE TABLE dws_category_summary (
    category_name        VARCHAR(100)  NOT NULL COMMENT '品类名',
    total_orders          INT           COMMENT '累计订单数',
    total_gmv            DECIMAL(14,2) COMMENT '累计GMV',
    total_revenue         DECIMAL(14,2) COMMENT '累计收入(不含运费)',
    avg_price            DECIMAL(10,2) COMMENT '均价',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    revenue_pct          DECIMAL(6,4)  COMMENT '收入占比',
    cumulative_pct       DECIMAL(6,4)  COMMENT '累计收入占比(ABC分析)',
    abc_class            CHAR(1)       COMMENT 'ABC分类(A/B/C)',
    unique_sellers       INT           COMMENT '卖家数',
    daily_avg_items      DECIMAL(8,1)  COMMENT '日均销量',
    etl_date              DATE          COMMENT 'ETL日期',
    PRIMARY KEY (category_name)
) COMMENT 'DWS层-品类全局汇总（含ABC分类）';

-- ============================================================
-- 6. dws_state_summary — 州级全局汇总（全时段）
-- ============================================================
DROP TABLE IF EXISTS dws_state_summary;
CREATE TABLE dws_state_summary (
    state                VARCHAR(2)    NOT NULL COMMENT '州缩写',
    total_orders          INT           COMMENT '累计订单数',
    total_gmv            DECIMAL(14,2) COMMENT '累计GMV',
    avg_delivery_days    DECIMAL(6,2)  COMMENT '平均交付天数',
    delay_rate           DECIMAL(6,4)  COMMENT '延迟率',
    avg_review_score     DECIMAL(4,2)  COMMENT '平均评分',
    unique_customers     INT           COMMENT '下单用户数',
    etl_date              DATE          COMMENT 'ETL日期',
    PRIMARY KEY (state)
) COMMENT 'DWS层-州级全局汇总';
