"""
SQL 分析对比页面 — 展示 SQL 查询在实际工作中的应用

这个页面模拟真实数据分析师的工作流：
数据库 → 写 SQL → 取数 → 分析

同时展示等价 Pandas 写法，向面试官证明你两种方式都会
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from modules.data_loader import load_and_preprocess
from dw.ads.dw_loader import load_from_warehouse

# 页面标题/icon 由 datall.py 的 st.set_page_config 统一设置

st.title("💾 SQL 数据分析 & 数仓架构")
st.caption("SQL vs Pandas 对比 + 数据仓库分层架构概览")

# ---- 侧边栏 ----
with st.sidebar:
    st.markdown("### 数据源")
    data_source = st.radio(
        "选择数据源",
        ["数仓 DWS 层 (MySQL)", "CSV 本地文件"],
        index=0,
        help="数仓版：数据经 ODS→DWD→DWS ETL 处理后从 MySQL 读取"
    )

    st.markdown("---")
    st.markdown("### 数仓分层架构")
    st.markdown("""
    ```
    ADS  ← 看板（读 DWS 聚合表）
     ↑
    DWS  ← 日/周聚合（6张表）
     ↑
    DWD  ← 订单宽表 + 维度表（5张）
     ↑
    ODS  ← CSV 原样入库（8张表）
    ```
    """)

    st.markdown("---")
    st.markdown("### 面试要点")
    st.markdown("""
    这个页面向面试官展示：
    - ✅ 理解数仓分层架构 (ODS/DWD/DWS/ADS)
    - ✅ 会写 SQL（JOIN、GROUP BY、窗口函数）
    - ✅ 会用 Python 分析
    """)

# ---- 数据库连接 ----
@st.cache_resource
def get_sql_analyzer(_use_mysql, **kw):
    from sql.sql_analyzer import SQLAnalyzer
    analyzer = SQLAnalyzer(use_mysql=_use_mysql)
    if _use_mysql:
        analyzer.mysql_config.update({
            'host': kw.get('host', 'localhost'),
            'port': kw.get('port', 3306),
            'user': kw.get('user', 'root'),
            'password': kw.get('password', ''),
        })
    analyzer.connect()
    return analyzer

# 根据选择加载数据
@st.cache_data
def get_data(use_warehouse=True):
    if use_warehouse:
        return load_from_warehouse()
    return load_and_preprocess()


# ============================================================
# 主页面
# ============================================================

pandas_data = None
use_warehouse = (data_source == "数仓 DWS 层 (MySQL)")

st.info(f"""
当前数据源: **{data_source}**
""")

# ---- Tabs ----
tab1, tab2, tab3, tab4 = st.tabs([
    "📦 交付时效",
    "📊 库存周转",
    "🚚 满意度归因",
    "📈 销售趋势"
])

# ============================================================
# Tab 1: 交付时效
# ============================================================
with tab1:
    st.subheader("Q: 每月交付时效趋势（按月汇总平均交付天数）")

    sql_code = """-- 这个 SQL 回答了"每个月平均多少天到货？延迟率怎么变？"
SELECT
    purchase_year_month,                       -- 年-月
    ROUND(AVG(delivery_days), 1) AS avg_days, -- 平均交付天数
    ROUND(AVG(is_delayed)*100, 1) AS delay_pct,-- 延迟率(%)
    COUNT(DISTINCT order_id) AS order_count    -- 订单量
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE order_status = 'delivered'
GROUP BY purchase_year_month
ORDER BY purchase_year_month;"""

    st.code(sql_code, language='sql')

    # 用 Pandas 数据画图（避免依赖数据库连接）
    try:
        pandas_data = get_data(use_warehouse)
        monthly = pandas_data['monthly_summary']

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly['purchase_year_month'],
            y=monthly['avg_delivery_days'],
            name='平均交付天数',
            marker_color='#3366CC',
        ))
        fig.add_trace(go.Scatter(
            x=monthly['purchase_year_month'],
            y=monthly['delay_rate'],
            name='延迟率(%)',
            yaxis='y2',
            line=dict(color='#DC3912', width=2),
        ))
        fig.update_layout(
            title='月度交付时效趋势',
            yaxis=dict(title='平均天数'),
            yaxis2=dict(title='延迟率(%)', overlaying='y', side='right'),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("请先下载数据集")

    st.markdown("---")
    st.caption("等价的 Pandas 写法:")
    pandas_code = """# Pandas 等价写法（对比理解）
df = data_dict['delivered']
monthly = df.groupby('purchase_year_month').agg(
    avg_days=('delivery_time_days', 'mean'),
    delay_pct=('is_delayed', lambda x: x.mean() * 100),
    orders=('order_id', 'nunique')
).reset_index()"""
    st.code(pandas_code, language='python')


# ============================================================
# Tab 2: 库存周转
# ============================================================
with tab2:
    st.subheader("Q: ABC 品类分层（头部多少品类贡献了70%收入？）")

    sql_code = """-- 用 窗口函数 做累计占比，这是面试高频考点
WITH cat_rev AS (
    SELECT category_name, SUM(price) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE order_status = 'delivered'
    GROUP BY category_name
)
SELECT
    category_name,
    ROUND(revenue * 100.0 / SUM(revenue) OVER(), 1) AS revenue_pct,
    ROUND(SUM(revenue) OVER(ORDER BY revenue DESC)
          * 100.0 / SUM(revenue) OVER(), 1) AS cum_pct,
    CASE
        WHEN SUM(revenue) OVER(ORDER BY revenue DESC)
             * 100.0 / SUM(revenue) OVER() <= 70 THEN 'A类(核心)'
        WHEN SUM(revenue) OVER(ORDER BY revenue DESC)
             * 100.0 / SUM(revenue) OVER() <= 90 THEN 'B类(重要)'
        ELSE 'C类(长尾)'
    END AS abc_class
FROM cat_rev
ORDER BY revenue DESC;"""

    st.code(sql_code, language='sql')

    st.markdown("**关键 SQL 概念解析：**")
    st.markdown("""
    - `SUM(revenue) OVER()` — 窗口函数，计算全局总和
    - `SUM(revenue) OVER(ORDER BY revenue DESC)` — 按收入降序的累计求和
    - `CASE WHEN` — 条件分类，给每个品类打标签
    """)

    try:
        if pandas_data is None:
            pandas_data = get_data(use_warehouse)
        cat = pandas_data['category_summary'].sort_values('total_revenue', ascending=False)
        cat['cum_pct'] = cat['total_revenue'].cumsum() / cat['total_revenue'].sum() * 100

        abc_counts = {
            'A类(核心)': (cat['cum_pct'] <= 70).sum(),
            'B类(重要)': ((cat['cum_pct'] > 70) & (cat['cum_pct'] <= 90)).sum(),
            'C类(长尾)': (cat['cum_pct'] > 90).sum(),
        }

        cols = st.columns(3)
        cols[0].metric("A类 核心品类", abc_counts['A类(核心)'], "贡献70%收入")
        cols[1].metric("B类 重要品类", abc_counts['B类(重要)'], "贡献20%收入")
        cols[2].metric("C类 长尾品类", abc_counts['C类(长尾)'], "贡献10%收入")
    except:
        pass

    st.caption("等价的 Pandas 写法:")
    pandas_code = """# Pandas 版本 — 更直观但面试官也想看到 SQL
cat = df.groupby('category_name')['price'].sum().reset_index()
cat = cat.sort_values('price', ascending=False)
cat['cum_pct'] = cat['price'].cumsum() / cat['price'].sum() * 100
cat['abc'] = np.where(cat['cum_pct'] <= 70, 'A',
             np.where(cat['cum_pct'] <= 90, 'B', 'C'))"""
    st.code(pandas_code, language='python')


# ============================================================
# Tab 3: 满意度归因
# ============================================================
with tab3:
    st.subheader("Q: 按时交付 vs 延迟交付，评分差多少？")

    sql_code = """-- 核心归因查询：物流慢了，客户真的会差评吗？
SELECT
    CASE WHEN o.delivered_date > o.estimated_date
         THEN '延迟交付' ELSE '按时交付' END AS type,
    COUNT(DISTINCT o.order_id) AS orders,
    ROUND(AVG(r.review_score), 2) AS avg_score,
    ROUND(SUM(CASE WHEN r.review_score=5 THEN 1 ELSE 0 END)
          * 100.0 / COUNT(DISTINCT o.order_id), 1) AS five_star_rate
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY
    CASE WHEN o.delivered_date > o.estimated_date
         THEN '延迟交付' ELSE '按时交付' END;"""

    st.code(sql_code, language='sql')

    st.markdown("**面试可以说的点：**")
    st.markdown("""
    这个 SQL 用了 `CASE WHEN` 做条件聚合 + `JOIN` 关联两个表 + `GROUP BY` 分组对比
    → 这就是数据分析师 90% 的日常工作
    """)

    try:
        if pandas_data is None:
            pandas_data = get_data(use_warehouse)
        df = pandas_data['delivered'].merge(
            pandas_data['raw']['order_reviews'].groupby('order_id')['review_score'].mean().reset_index(),
            on='order_id', how='inner'
        )
        ontime = df[~df['is_delayed']]['review_score'].mean()
        delayed = df[df['is_delayed']]['review_score'].mean()

        cols = st.columns(3)
        cols[0].metric("按时交付 平均评分", f"{ontime:.2f}", "基准线")
        cols[1].metric("延迟交付 平均评分", f"{delayed:.2f}", f"{(delayed-ontime):.2f}")
        cols[2].metric("结论", f"延迟评分低{abs(delayed-ontime):.2f}分",
                       delta=f"物流是关键因素" if abs(delayed-ontime) > 0.5 else "影响有限",
                       delta_color="inverse")
    except:
        pass

    st.caption("等价的 Pandas 写法:")
    pandas_code = """df.groupby('is_delayed')['review_score'].mean()
# 等价于 SQL 的: GROUP BY is_delayed + AVG(review_score)"""
    st.code(pandas_code, language='python')


# ============================================================
# Tab 4: 销售趋势
# ============================================================
with tab4:
    st.subheader("Q: RFM 客户分层（谁是我们的高价值客户？）")

    sql_code = """-- 客户价值分层，用窗口函数 NTILE 分档
WITH rfm AS (
    SELECT
        customer_unique_id,
        DATEDIFF('2018-09-01', MAX(purchase_date)) AS recency,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(price) AS monetary
    FROM orders o
    JOIN order_items oi USING(order_id)
    JOIN customers c USING(customer_id)
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
),
scored AS (
    SELECT *,
        NTILE(4) OVER(ORDER BY recency DESC) AS r_score,
        NTILE(4) OVER(ORDER BY frequency)    AS f_score,
        NTILE(4) OVER(ORDER BY monetary)     AS m_score
    FROM rfm
)
SELECT
    CASE
        WHEN r_score+f_score+m_score >= 10 THEN '高价值客户'
        WHEN r_score+f_score+m_score >= 7  THEN '潜力客户'
        WHEN r_score+f_score+m_score >= 5  THEN '一般客户'
        ELSE '流失风险客户'
    END AS segment,
    COUNT(*) AS count,
    ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) AS pct
FROM scored
GROUP BY segment
ORDER BY AVG(r_score+f_score+m_score) DESC;"""

    st.code(sql_code, language='sql')

    st.markdown("**SQL 进阶点（面试加分项）：**")
    st.markdown("""
    - `NTILE(4)` — 把客户按消费额等分为4档（窗口函数）
    - `CTE (WITH ... AS)` — 子查询模块化，可读性强
    - RFM 模型 — 电商/零售分析的经典模型
    """)

    try:
        if pandas_data is None:
            pandas_data = get_data(use_warehouse)
        df = pandas_data['delivered']
        ref_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

        rfm = df.groupby('customer_unique_id').agg(
            recency=('order_purchase_timestamp', lambda x: (ref_date - x.max()).days),
            frequency=('order_id', 'nunique'),
            monetary=('price', 'sum'),
        ).reset_index()

        rfm['R'] = pd.qcut(rfm['recency'], 4, labels=[4, 3, 2, 1])
        rfm['F'] = pd.qcut(rfm['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4])
        rfm['M'] = pd.qcut(rfm['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4])
        rfm['total'] = rfm['R'].astype(int) + rfm['F'].astype(int) + rfm['M'].astype(int)

        def segment(s):
            if s >= 10: return '高价值客户'
            if s >= 7: return '潜力客户'
            if s >= 5: return '一般客户'
            return '流失风险客户'

        rfm['segment'] = rfm['total'].apply(segment)
        seg = rfm['segment'].value_counts()

        fig = px.pie(
            values=seg.values, names=seg.index,
            title='客户分层占比',
            color=seg.index,
            color_discrete_map={
                '高价值客户': '#109618',
                '潜力客户': '#3366CC',
                '一般客户': '#FF9900',
                '流失风险客户': '#DC3912',
            }
        )
        fig.update_traces(textinfo='label+percent', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

    except:
        pass

    st.caption("等价的 Pandas 写法:")
    pandas_code = """# Pandas 版本 — pd.qcut 等价于 SQL 的 NTILE
rfm['R'] = pd.qcut(rfm['recency'], 4, labels=[4,3,2,1])
rfm['F'] = pd.qcut(rfm['frequency'].rank(method='first'), 4, labels=[1,2,3,4])
rfm['M'] = pd.qcut(rfm['monetary'].rank(method='first'), 4, labels=[1,2,3,4])"""
    st.code(pandas_code, language='python')


# ============================================================
# 底部总结
# ============================================================
st.markdown("---")
st.success("""
### 面试时这样说

> "这个项目我用了两种技术路线：**Pandas 做探索性分析 + Plotly 可视化**包装成 Streamlit 看板，
> 同时把核心分析逻辑翻译成了 **SQL**（JOIN + GROUP BY + 窗口函数），
> 证明我既能在 Python 环境做分析，也能直接从数据库取数，两种方式都熟练掌握。"
""")
