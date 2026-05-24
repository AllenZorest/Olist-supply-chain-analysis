"""
销售趋势分析模块

核心分析：
- 整体销售趋势（月度/周度）
- 季节性分析（节假日效应）
- 品类销售趋势
- 地理销售分布
- 客单价趋势
- RFM客户分层
- 订单状态漏斗
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import streamlit as st


def sales_kpi_cards(data_dict):
    """销售 KPI 卡片"""
    df = data_dict['delivered']
    monthly = data_dict['monthly_summary']

    total_revenue = df['price'].sum()
    total_orders = df['order_id'].nunique()
    avg_order_value = df.groupby('order_id')['price'].sum().mean()
    unique_customers = df['customer_unique_id'].nunique()

    # 月环比增长率
    if len(monthly) >= 2:
        last_month_rev = monthly.iloc[-1]['total_revenue']
        prev_month_rev = monthly.iloc[-2]['total_revenue']
        mom_growth = ((last_month_rev - prev_month_rev) / prev_month_rev * 100) if prev_month_rev > 0 else 0
    else:
        mom_growth = 0

    return {
        '总销售额': f"R$ {total_revenue:,.0f}",
        '总订单数': f"{total_orders:,}",
        '平均客单价': f"R$ {avg_order_value:,.0f}",
        '客户数': f"{unique_customers:,}",
        '月环比增长': f"{mom_growth:+.1f}%",
        '单价中位数': f"R$ {df['price'].median():.0f}",
    }


def plot_revenue_trend(data_dict):
    """月度收入与订单量趋势"""
    monthly = data_dict['monthly_summary']

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=monthly['purchase_year_month'],
            y=monthly['total_revenue'],
            name='收入',
            marker_color='#3366CC',
            opacity=0.8,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=monthly['purchase_year_month'],
            y=monthly['total_orders'],
            name='订单数',
            mode='lines+markers',
            line=dict(color='#DC3912', width=2),
            marker=dict(size=6),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title='月度销售趋势（收入 & 订单量）',
        height=450,
        hovermode='x unified',
    )
    fig.update_xaxes(title_text='月份')
    fig.update_yaxes(title_text='收入 (R$)', secondary_y=False)
    fig.update_yaxes(title_text='订单数', secondary_y=True)

    return fig


def plot_seasonality_analysis(data_dict):
    """销售季节性分析"""
    df = data_dict['delivered']

    # 按周几
    dow_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    dow_stats = df.groupby('purchase_dayofweek').agg(
        orders=('order_id', 'nunique'),
        revenue=('price', 'sum'),
    ).reset_index()
    dow_stats['day_name'] = dow_stats['purchase_dayofweek'].map(lambda x: dow_names[int(x)])

    # 按月
    month_stats = df.groupby('purchase_month').agg(
        orders=('order_id', 'nunique'),
        revenue=('price', 'sum'),
    ).reset_index()
    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    month_stats['month_name'] = month_stats['purchase_month'].map(lambda x: month_names[int(x) - 1])

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('按星期几', '按月份'),
    )

    fig.add_trace(
        go.Bar(
            x=dow_stats['day_name'],
            y=dow_stats['orders'],
            marker_color='#3366CC',
            text=dow_stats['orders'],
            textposition='outside',
            name='按周几',
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            x=month_stats['month_name'],
            y=month_stats['orders'],
            marker_color='#FF9900',
            text=month_stats['orders'],
            textposition='outside',
            name='按月份',
        ),
        row=1, col=2
    )

    fig.update_layout(
        title='销售季节性模式',
        height=400,
        showlegend=False,
    )
    fig.update_yaxes(title_text='订单数', row=1, col=1)
    fig.update_yaxes(title_text='订单数', row=1, col=2)

    return fig


def plot_geo_sales(data_dict):
    """地理销售分布"""
    df = data_dict['delivered']

    # 按客户州汇总
    geo = df.groupby('customer_state').agg(
        orders=('order_id', 'nunique'),
        revenue=('price', 'sum'),
        avg_score=('review_score', 'mean'),
    ).reset_index()

    # 加载巴西各州
    from utils.helpers import STATE_MAP, REGION_MAP
    geo['state_name'] = geo['customer_state'].map(STATE_MAP)
    geo['region'] = geo['customer_state'].map(
        lambda x: next((r for r, s in REGION_MAP.items() if x in s), 'Unknown')
    )

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('各州订单量', '各州收入'),
        specs=[[{'type': 'bar'}, {'type': 'bar'}]],
    )

    geo_sorted_orders = geo.sort_values('orders', ascending=True)

    fig.add_trace(
        go.Bar(
            y=geo_sorted_orders['customer_state'],
            x=geo_sorted_orders['orders'],
            orientation='h',
            marker_color='#3366CC',
            text=geo_sorted_orders['orders'],
            textposition='outside',
            name='订单量',
        ),
        row=1, col=1
    )

    geo_sorted_rev = geo.sort_values('revenue', ascending=True)

    fig.add_trace(
        go.Bar(
            y=geo_sorted_rev['customer_state'],
            x=geo_sorted_rev['revenue'],
            orientation='h',
            marker_color='#FF9900',
            text=geo_sorted_rev['revenue'].apply(lambda x: f'R${x/1000:.0f}K'),
            textposition='outside',
            name='收入',
        ),
        row=1, col=2
    )

    fig.update_layout(
        title='销售地理分布（按客户所在州）',
        height=max(400, len(geo) * 18),
        showlegend=False,
    )

    return fig


def plot_category_trend(data_dict):
    """品类销售趋势"""
    df = data_dict['delivered']
    monthly = data_dict['monthly_summary']
    cat = data_dict['category_summary']

    # Top5品类月度占比变化
    top5_cats = cat.nlargest(5, 'total_revenue')['category_name'].tolist()

    monthly_cat = df[df['category_name'].isin(top5_cats)].groupby(
        ['purchase_year_month', 'category_name']
    )['price'].sum().reset_index()

    monthly_total = df.groupby('purchase_year_month')['price'].sum().reset_index()
    monthly_total.columns = ['purchase_year_month', 'total_revenue']

    monthly_cat = monthly_cat.merge(monthly_total, on='purchase_year_month')
    monthly_cat['share'] = monthly_cat['price'] / monthly_cat['total_revenue'] * 100
    monthly_cat['purchase_year_month'] = monthly_cat['purchase_year_month'].astype(str)

    fig = px.area(
        monthly_cat,
        x='purchase_year_month',
        y='share',
        color='category_name',
        title='Top 5 品类收入占比趋势',
        labels={
            'purchase_year_month': '月份',
            'share': '收入占比 (%)',
            'category_name': '品类',
        },
        groupnorm=None,
    )
    fig.update_layout(height=450, hovermode='x unified')

    return fig


def plot_order_status_funnel(data_dict):
    """订单状态漏斗"""
    orders = data_dict['raw']['orders']

    status_counts = orders['order_status'].value_counts()

    fig = go.Figure(go.Funnel(
        y=status_counts.index.tolist(),
        x=status_counts.values.tolist(),
        textinfo="value+percent previous",
        textposition="inside",
        marker=dict(color=['#3366CC', '#109618', '#FF9900', '#DC3912', '#990099', '#0099C6',
                           '#DD4477', '#66AA00']),
    ))

    fig.update_layout(
        title='订单状态流转漏斗',
        height=400,
    )

    return fig


def plot_rfm_analysis(data_dict):
    """RFM 客户分层"""
    df = data_dict['delivered']

    # 计算参考日期
    reference_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

    rfm = df.groupby('customer_unique_id').agg(
        recency=('order_purchase_timestamp', lambda x: (reference_date - x.max()).days),
        frequency=('order_id', 'nunique'),
        monetary=('price', 'sum'),
    ).reset_index()

    # 客户分层
    rfm['R_score'] = pd.qcut(rfm['recency'], 4, labels=[4, 3, 2, 1])
    rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4])
    rfm['M_score'] = pd.qcut(rfm['monetary'].rank(method='first'), 4, labels=[1, 2, 3, 4])

    rfm['RFM_score'] = rfm['R_score'].astype(int) + rfm['F_score'].astype(int) + rfm['M_score'].astype(int)

    def segment(score):
        if score >= 10:
            return '高价值客户'
        elif score >= 7:
            return '潜力客户'
        elif score >= 5:
            return '一般客户'
        else:
            return '流失风险客户'

    rfm['segment'] = rfm['RFM_score'].apply(segment)

    seg_stats = rfm.groupby('segment').agg(
        count=('customer_unique_id', 'count'),
        avg_monetary=('monetary', 'mean'),
    ).reset_index()
    seg_stats['pct'] = seg_stats['count'] / seg_stats['count'].sum() * 100

    # 饼图
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('客户分层占比', '各层平均消费'),
        specs=[[{'type': 'pie'}, {'type': 'bar'}]],
    )

    colors_map = {
        '高价值客户': '#109618',
        '潜力客户': '#3366CC',
        '一般客户': '#FF9900',
        '流失风险客户': '#DC3912',
    }

    fig.add_trace(
        go.Pie(
            labels=seg_stats['segment'],
            values=seg_stats['count'],
            marker=dict(colors=[colors_map.get(s, '#999') for s in seg_stats['segment']]),
            textinfo='label+percent',
            hole=0.3,
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            x=seg_stats['segment'],
            y=seg_stats['avg_monetary'],
            marker_color=[colors_map.get(s, '#999') for s in seg_stats['segment']],
            text=seg_stats['avg_monetary'].apply(lambda x: f'R${x:.0f}'),
            textposition='outside',
        ),
        row=1, col=2
    )

    fig.update_layout(
        title='RFM 客户分层分析',
        height=450,
        showlegend=False,
    )
    fig.update_yaxes(title_text='平均消费金额', row=1, col=2)

    return fig


def run_sales_analysis(data_dict):
    """运行完整的销售趋势分析"""
    st.header("销售趋势分析")

    # KPI 卡片
    kpis = sales_kpi_cards(data_dict)
    cols = st.columns(6)
    labels = list(kpis.keys())
    values = list(kpis.values())
    for i, col in enumerate(cols):
        col.metric(labels[i], values[i])

    st.markdown("---")

    # 收入趋势
    st.subheader("月度销售趋势")
    st.plotly_chart(plot_revenue_trend(data_dict), use_container_width=True)

    # 季节性 + 地理
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("销售季节性")
        st.plotly_chart(plot_seasonality_analysis(data_dict), use_container_width=True)

    with col2:
        st.subheader("品类收入占比趋势")
        st.plotly_chart(plot_category_trend(data_dict), use_container_width=True)

    # 地理分布
    st.subheader("地理销售分布")
    st.plotly_chart(plot_geo_sales(data_dict), use_container_width=True)

    # 订单漏斗 + RFM
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("订单状态漏斗")
        st.plotly_chart(plot_order_status_funnel(data_dict), use_container_width=True)

    with col2:
        st.subheader("客户分层 (RFM)")
        st.plotly_chart(plot_rfm_analysis(data_dict), use_container_width=True)
