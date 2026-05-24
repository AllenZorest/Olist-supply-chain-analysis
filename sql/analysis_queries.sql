-- ============================================================
-- Olist 供应链数据分析 SQL 查询集
-- 场景模拟：假设你是数据分析师，每天用这些SQL从数据库取数
--
-- 使用方式：
--   mysql -u root -p olist_supply_chain < analysis_queries.sql
-- 或者逐条复制到 MySQL Workbench 中执行
-- ============================================================

USE olist_supply_chain;

-- ============================================================
-- 📦 模块一：供应商交付时效分析
-- 业务场景：运营经理想知道"哪些供应商发货慢？延迟率趋势如何？"
-- ============================================================

-- Q1: 整体交付时效概览（KPI卡片数据）
-- 含义：已交付订单的总数、平均/中位交付天数、延迟率
SELECT
    '整体' AS scope,
    COUNT(DISTINCT order_id)                                    AS total_delivered,
    ROUND(AVG(delivery_days), 1)                                AS avg_delivery_days,
    ROUND(AVG(delivery_days), 0)                                AS median_delivery_days,  -- 近似
    ROUND(AVG(is_delayed) * 100, 1)                             AS delay_rate_pct,
    ROUND(AVG(CASE WHEN is_delayed = 1 THEN delay_days END), 1) AS avg_delay_when_late
FROM v_order_full
WHERE order_status = 'delivered';

-- Q2: 月度交付时效趋势（折线图数据）
-- 含义：每个月平均多少天到货、延迟率是多少
-- 实际工作场景：每周一早上跑这个SQL给领导看趋势
SELECT
    purchase_year_month,
    ROUND(AVG(delivery_days), 1)      AS avg_delivery_days,
    ROUND(AVG(is_delayed) * 100, 1)   AS delay_rate_pct,
    COUNT(DISTINCT order_id)          AS order_count
FROM v_order_full
WHERE order_status = 'delivered'
GROUP BY purchase_year_month
ORDER BY purchase_year_month;

-- Q3: 各州交付时效对比（横向柱状图）
-- 含义：哪个州的客户收货最慢？
SELECT
    customer_state,
    ROUND(AVG(delivery_days), 1)    AS avg_delivery_days,
    ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
    COUNT(DISTINCT order_id)        AS order_count
FROM v_order_full
WHERE order_status = 'delivered'
  AND customer_state IS NOT NULL
GROUP BY customer_state
HAVING order_count >= 50  -- 样本量太小的州忽略
ORDER BY avg_delivery_days DESC;

-- Q4: 品类交付时效排名（Top延迟品类）
-- 含义：哪些品类最拖后腿？
SELECT
    category_name,
    ROUND(AVG(delivery_days), 1)    AS avg_delivery_days,
    ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
    COUNT(DISTINCT order_id)        AS order_count
FROM v_order_full
WHERE order_status = 'delivered'
  AND category_name IS NOT NULL
GROUP BY category_name
ORDER BY delay_rate_pct DESC
LIMIT 15;

-- Q5: 延迟天数分布（哪些延迟天数最多）
-- 含义：延迟了1天、2天...还是10天？用于设定SLA目标
SELECT
    delay_days,
    COUNT(DISTINCT order_id) AS delay_count
FROM v_order_full
WHERE order_status = 'delivered'
  AND is_delayed = 1
  AND delay_days <= 30
GROUP BY delay_days
ORDER BY delay_days;

-- Q6: 供应商交付排行榜（Top10最慢/最快）
-- 实际工作中：采购部门需要这个数据去考核供应商
SELECT
    seller_id,
    ROUND(AVG(delivery_days), 1)    AS avg_delivery_days,
    ROUND(AVG(is_delayed) * 100, 1) AS delay_rate_pct,
    COUNT(DISTINCT order_id)        AS total_orders,
    SUM(price)                      AS total_revenue
FROM v_order_full
WHERE order_status = 'delivered'
  AND seller_id IS NOT NULL
GROUP BY seller_id
ORDER BY delay_rate_pct DESC
LIMIT 10;


-- ============================================================
-- 📊 模块二：品类库存周转分析
-- 业务场景：商品运营经理想知道"哪些品类好卖？库存结构合理吗？"
-- 注：Olist无库存数据，用销售速度和集中度作为代理指标
-- ============================================================

-- Q7: 品类销售速度排行（日均销量 Top20）
-- 含义：每个品类平均每天卖多少单
SELECT
    category_name,
    COUNT(DISTINCT order_id) AS total_sales,
    ROUND(SUM(price), 0)     AS total_revenue,
    ROUND(COUNT(DISTINCT order_id) /
          (SELECT DATEDIFF(MAX(order_purchase_timestamp),
                           MIN(order_purchase_timestamp))
           FROM v_order_full WHERE order_status = 'delivered'), 2) AS daily_sales,
    COUNT(DISTINCT product_id) AS unique_products,
    COUNT(DISTINCT seller_id)  AS unique_sellers
FROM v_order_full
WHERE order_status = 'delivered'
  AND category_name IS NOT NULL
GROUP BY category_name
ORDER BY daily_sales DESC
LIMIT 20;

-- Q8: ABC 品类分层分析（帕累托分析）
-- 含义：头部多少品类贡献了70%收入？
-- 这是面试高频考点：用窗口函数做累计占比
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
),
ranked AS (
    SELECT
        cr.*,
        cr.revenue / t.total_rev * 100 AS revenue_pct,
        SUM(cr.revenue) OVER (ORDER BY cr.revenue DESC) / t.total_rev * 100 AS cum_pct,
        ROW_NUMBER() OVER (ORDER BY cr.revenue DESC) AS rn
    FROM category_revenue cr, total t
)
SELECT
    category_name,
    ROUND(revenue, 0)    AS revenue,
    ROUND(revenue_pct, 1) AS revenue_pct,
    ROUND(cum_pct, 1)    AS cum_pct,
    CASE
        WHEN cum_pct <= 70 THEN 'A类(核心)'
        WHEN cum_pct <= 90 THEN 'B类(重要)'
        ELSE 'C类(长尾)'
    END AS abc_class
FROM ranked
ORDER BY revenue DESC;

-- Q9: 品类月度趋势（Top 5 品类收入占比变化）
-- 含义：核心品类的市场份额在涨还是跌？
SELECT
    purchase_year_month,
    category_name,
    SUM(price) AS monthly_revenue,
    SUM(SUM(price)) OVER (PARTITION BY purchase_year_month) AS total_monthly_revenue,
    ROUND(SUM(price) / SUM(SUM(price)) OVER (PARTITION BY purchase_year_month) * 100, 1) AS revenue_share_pct
FROM v_order_full
WHERE order_status = 'delivered'
  AND category_name IN (
      SELECT category_name FROM (
          SELECT category_name, SUM(price) AS rev
          FROM v_order_full WHERE order_status = 'delivered'
          GROUP BY category_name ORDER BY rev DESC LIMIT 5
      ) top
  )
GROUP BY purchase_year_month, category_name
ORDER BY purchase_year_month, category_name;

-- Q10: 卖家品类覆盖度分析
-- 含义：大部分卖家只卖一个品类，还是跨品类经营？
SELECT
    CASE
        WHEN category_count = 1 THEN '单品类'
        WHEN category_count <= 3 THEN '2-3品类'
        WHEN category_count <= 5 THEN '4-5品类'
        ELSE '5+品类'
    END AS seller_type,
    COUNT(*) AS seller_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) AS pct
FROM (
    SELECT seller_id, COUNT(DISTINCT category_name) AS category_count
    FROM v_order_full
    WHERE order_status = 'delivered' AND seller_id IS NOT NULL
    GROUP BY seller_id
) seller_cats
GROUP BY
    CASE
        WHEN category_count = 1 THEN '单品类'
        WHEN category_count <= 3 THEN '2-3品类'
        WHEN category_count <= 5 THEN '4-5品类'
        ELSE '5+品类'
    END
ORDER BY seller_count DESC;


-- ============================================================
-- 🚚 模块三：物流满意度归因分析
-- 业务场景：客服经理想知道"物流慢了客户真的会差评吗？数据支撑是什么？"
-- ============================================================

-- Q11: 按时 vs 延迟 评分对比（核心归因查询）
-- 含义：同一批订单，按时到的平均分 vs 延迟到的平均分
SELECT
    CASE WHEN is_delayed = 1 THEN '延迟交付' ELSE '按时交付' END AS delivery_type,
    COUNT(DISTINCT v.order_id)                                   AS order_count,
    ROUND(AVG(r.review_score), 2)                                AS avg_score,
    ROUND(SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END) /
          COUNT(DISTINCT v.order_id) * 100, 1)                   AS score_5_rate_pct,
    ROUND(SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) /
          COUNT(DISTINCT v.order_id) * 100, 1)                   AS negative_rate_pct
FROM v_order_full v
INNER JOIN order_reviews r ON v.order_id = r.order_id
WHERE v.order_status = 'delivered'
GROUP BY CASE WHEN is_delayed = 1 THEN '延迟交付' ELSE '按时交付' END;

-- Q12: 交付天数 vs 评分（分段分析）
-- 含义：交付时间越长，评分怎么变？
SELECT
    CASE
        WHEN delivery_days <= 5  THEN '0-5天'
        WHEN delivery_days <= 10 THEN '6-10天'
        WHEN delivery_days <= 15 THEN '11-15天'
        WHEN delivery_days <= 20 THEN '16-20天'
        WHEN delivery_days <= 30 THEN '21-30天'
        ELSE '30天以上'
    END AS delivery_range,
    COUNT(DISTINCT v.order_id)    AS order_count,
    ROUND(AVG(r.review_score), 2) AS avg_score,
    ROUND(SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END) /
          COUNT(DISTINCT v.order_id) * 100, 1) AS score_5_rate_pct
FROM v_order_full v
INNER JOIN order_reviews r ON v.order_id = r.order_id
WHERE v.order_status = 'delivered'
GROUP BY
    CASE
        WHEN delivery_days <= 5  THEN '0-5天'
        WHEN delivery_days <= 10 THEN '6-10天'
        WHEN delivery_days <= 15 THEN '11-15天'
        WHEN delivery_days <= 20 THEN '16-20天'
        WHEN delivery_days <= 30 THEN '21-30天'
        ELSE '30天以上'
    END
ORDER BY MIN(delivery_days);

-- Q13: 各州满意度对比（含延迟率）
-- 含义：哪些州满意度低，是物流问题导致的吗？
SELECT
    v.customer_state,
    ROUND(AVG(v.delivery_days), 1)    AS avg_delivery_days,
    ROUND(AVG(v.is_delayed) * 100, 1) AS delay_rate_pct,
    ROUND(AVG(r.review_score), 2)     AS avg_score,
    COUNT(DISTINCT v.order_id)        AS order_count
FROM v_order_full v
INNER JOIN order_reviews r ON v.order_id = r.order_id
WHERE v.order_status = 'delivered'
  AND v.customer_state IS NOT NULL
GROUP BY v.customer_state
HAVING order_count >= 50
ORDER BY avg_score ASC;

-- Q14: 满意度相关因素（多维度）
-- 含义：除了交付时效，运费、商品重量也影响评分吗？
SELECT
    ROUND(AVG(r.review_score), 2)                 AS avg_score,
    ROUND(AVG(v.delivery_days), 1)                 AS avg_delivery_days,
    ROUND(AVG(v.is_delayed) * 100, 1)              AS delay_rate_pct,
    ROUND(AVG(v.freight_value), 2)                 AS avg_freight,
    ROUND(AVG(v.product_weight_g), 0)              AS avg_weight_g,
    ROUND(AVG(v.price), 2)                         AS avg_price
FROM v_order_full v
INNER JOIN order_reviews r ON v.order_id = r.order_id
WHERE v.order_status = 'delivered';

-- Q15: 差评订单特征分析（review_score <= 2）
-- 含义：给差评的订单有什么共同特征？交付慢？运费贵？商品重？
SELECT
    '差评订单(≤2分)' AS group_type,
    COUNT(DISTINCT v.order_id)    AS order_count,
    ROUND(AVG(v.delivery_days), 1) AS avg_delivery_days,
    ROUND(AVG(v.delay_days), 1)    AS avg_delay_days,
    ROUND(AVG(v.freight_value), 2) AS avg_freight,
    ROUND(AVG(v.product_weight_g), 0) AS avg_weight_g
FROM v_order_full v
INNER JOIN order_reviews r ON v.order_id = r.order_id
WHERE v.order_status = 'delivered'
  AND r.review_score <= 2

UNION ALL

SELECT
    '好评订单(5分)' AS group_type,
    COUNT(DISTINCT v.order_id)    AS order_count,
    ROUND(AVG(v.delivery_days), 1) AS avg_delivery_days,
    ROUND(AVG(v.delay_days), 1)    AS avg_delay_days,
    ROUND(AVG(v.freight_value), 2) AS avg_freight,
    ROUND(AVG(v.product_weight_g), 0) AS avg_weight_g
FROM v_order_full v
INNER JOIN order_reviews r ON v.order_id = r.order_id
WHERE v.order_status = 'delivered'
  AND r.review_score = 5;


-- ============================================================
-- 📈 模块四：销售趋势分析
-- 业务场景：市场经理想知道"销售额在涨还是跌？几月份是旺季？"
-- ============================================================

-- Q16: 月度销售趋势（收入 + 订单数 双轴）
-- 含义：每个月的销售额和订单数变化
SELECT
    purchase_year_month,
    COUNT(DISTINCT order_id)      AS monthly_orders,
    ROUND(SUM(price), 0)          AS monthly_revenue,
    COUNT(DISTINCT customer_unique_id) AS unique_customers,
    ROUND(SUM(price) / COUNT(DISTINCT order_id), 0) AS avg_order_value
FROM v_order_full
WHERE order_status = 'delivered'
GROUP BY purchase_year_month
ORDER BY purchase_year_month;

-- Q17: 周几下单最多？（季节性分析）
-- 含义：工作日 vs 周末购买习惯
SELECT
    CASE DAYOFWEEK(order_purchase_timestamp)
        WHEN 1 THEN '周日' WHEN 2 THEN '周一' WHEN 3 THEN '周二'
        WHEN 4 THEN '周三' WHEN 5 THEN '周四' WHEN 6 THEN '周五'
        WHEN 7 THEN '周六'
    END AS day_of_week,
    COUNT(DISTINCT order_id)     AS order_count,
    ROUND(SUM(price), 0)         AS total_revenue
FROM v_order_full
WHERE order_status = 'delivered'
GROUP BY DAYOFWEEK(order_purchase_timestamp)
ORDER BY DAYOFWEEK(order_purchase_timestamp);

-- Q18: 各月份订单量（季节性分析）
SELECT
    purchase_month,
    COUNT(DISTINCT order_id)     AS order_count,
    ROUND(SUM(price), 0)         AS total_revenue
FROM v_order_full
WHERE order_status = 'delivered'
GROUP BY purchase_month
ORDER BY purchase_month;

-- Q19: 各州销售排行榜
-- 含义：哪个州贡献最多收入？
SELECT
    customer_state,
    COUNT(DISTINCT order_id)      AS total_orders,
    ROUND(SUM(price), 0)          AS total_revenue,
    COUNT(DISTINCT customer_unique_id) AS customer_count,
    ROUND(SUM(price) / COUNT(DISTINCT order_id), 0) AS avg_order_value
FROM v_order_full
WHERE order_status = 'delivered'
  AND customer_state IS NOT NULL
GROUP BY customer_state
ORDER BY total_revenue DESC;

-- Q20: 订单状态漏斗（从下单到完成的转化）
-- 含义：多少订单走完了完整流程？
SELECT
    order_status,
    COUNT(DISTINCT order_id) AS count,
    ROUND(COUNT(DISTINCT order_id) /
          (SELECT COUNT(DISTINCT order_id) FROM orders) * 100, 1) AS pct
FROM orders
GROUP BY order_status
ORDER BY count DESC;

-- Q21: RFM 客户分层
-- 含义：哪些是 VIP 客户？哪些快流失了？
-- 这是数据分析师必会的经典模型
WITH rfm_base AS (
    SELECT
        customer_unique_id,
        DATEDIFF(
            (SELECT MAX(order_purchase_timestamp) FROM v_order_full WHERE order_status = 'delivered'),
            MAX(order_purchase_timestamp)
        ) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(price) AS monetary
    FROM v_order_full
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
),
rfm_scored AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,   -- 越小=越近=越好
        NTILE(4) OVER (ORDER BY frequency ASC)    AS f_score,    -- 越大=越频繁=越好
        NTILE(4) OVER (ORDER BY monetary ASC)     AS m_score     -- 越大=消费越多=越好
    FROM rfm_base
),
rfm_segmented AS (
    SELECT
        *,
        r_score + f_score + m_score AS rfm_total,
        CASE
            WHEN r_score + f_score + m_score >= 10 THEN '高价值客户'
            WHEN r_score + f_score + m_score >= 7  THEN '潜力客户'
            WHEN r_score + f_score + m_score >= 5  THEN '一般客户'
            ELSE '流失风险客户'
        END AS segment
    FROM rfm_scored
)
SELECT
    segment,
    COUNT(*) AS customer_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) AS pct,
    ROUND(AVG(monetary), 0) AS avg_lifetime_value,
    ROUND(AVG(frequency), 1) AS avg_orders
FROM rfm_segmented
GROUP BY segment
ORDER BY
    CASE segment
        WHEN '高价值客户' THEN 1
        WHEN '潜力客户' THEN 2
        WHEN '一般客户' THEN 3
        WHEN '流失风险客户' THEN 4
    END;
