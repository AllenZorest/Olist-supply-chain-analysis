"""
供应商交付时效分析模块

核心指标：
- 平均交付周期 & 分布
- 按时交付率（SLA达成率）
- 延迟交付分析（延迟天数分布、延迟原因）
- 区域/州维度交付对比
- 品类维度交付对比
- 月度交付趋势
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def delivery_kpi_cards(data_dict):
    """生成交付时效 KPI 卡片数据"""
    df = data_dict['delivered']

    total_delivered = len(df)
    avg_delivery = df['delivery_time_days'].mean()
    median_delivery = df['delivery_time_days'].median()
    delay_rate = df['is_delayed'].mean() * 100
    avg_delay = df.loc[df['is_delayed'], 'delay_days'].mean()
    p95_delivery = df['delivery_time_days'].quantile(0.95)

    return {
        '已交付订单': f"{total_delivered:,}",
        '平均交付周期': f"{avg_delivery:.1f} 天",
        '中位交付周期': f"{median_delivery:.0f} 天",
        '延迟交付率': f"{delay_rate:.1f}%",
        '平均延迟天数': f"{avg_delay:.1f} 天",
        'P95交付周期': f"{p95_delivery:.0f} 天",
    }


def plot_delivery_distribution(data_dict):
    """交付周期分布图"""
    df = data_dict['delivered']

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('交付周期分布（直方图）', '交付周期箱线图'),
        specs=[[{'type': 'histogram'}, {'type': 'box'}]]
    )

    # 直方图
    delivery_times = df['delivery_time_days'].dropna()
    delivery_times = delivery_times[delivery_times.between(0, 60)]

    fig.add_trace(
        go.Histogram(
            x=delivery_times,
            nbinsx=40,
            marker_color='#3366CC',
            opacity=0.75,
            name='订单数',
            hovertemplate='交付天数: %{x}<br>订单数: %{y}<extra></extra>'
        ),
        row=1, col=1
    )

    # 添加均值线
    mean_val = delivery_times.mean()
    fig.add_vline(x=mean_val, line_dash="dash", line_color="red",
                  annotation_text=f"均值: {mean_val:.1f}天", row=1, col=1)

    # 箱线图
    fig.add_trace(
        go.Box(
            x=delivery_times,
            marker_color='#3366CC',
            name='',
            hovertemplate='交付天数: %{x}<extra></extra>'
        ),
        row=1, col=2
    )

    fig.update_layout(
        title='订单交付周期分布分析',
        height=450,
        showlegend=False,
        bargap=0.05,
    )
    fig.update_xaxes(title_text='交付天数', row=1, col=1)
    fig.update_xaxes(title_text='交付天数', row=1, col=2)
    fig.update_yaxes(title_text='订单数量', row=1, col=1)

    return fig


def plot_monthly_delivery_trend(data_dict):
    """月度交付时效趋势"""
    monthly = data_dict['monthly_summary']

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('平均交付周期趋势', '延迟交付率趋势'),
        shared_xaxes=True,
        vertical_spacing=0.12,
    )

    fig.add_trace(
        go.Scatter(
            x=monthly['purchase_year_month'],
            y=monthly['avg_delivery_days'],
            mode='lines+markers',
            name='平均交付天数',
            line=dict(color='#3366CC', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(51,102,204,0.1)',
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=monthly['purchase_year_month'],
            y=monthly['delay_rate'],
            mode='lines+markers',
            name='延迟率(%)',
            line=dict(color='#DC3912', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(220,57,18,0.1)',
        ),
        row=2, col=1
    )

    fig.update_layout(
        title='月度交付时效趋势',
        height=550,
        hovermode='x unified',
    )
    fig.update_yaxes(title_text='天数', row=1, col=1)
    fig.update_yaxes(title_text='延迟率 (%)', row=2, col=1)

    return fig


def plot_delivery_by_state(data_dict):
    """各州交付时效对比"""
    df = data_dict['delivered']

    # 按客户州汇总
    state_stats = df.groupby('customer_state').agg(
        avg_delivery=('delivery_time_days', 'mean'),
        delay_rate=('is_delayed', 'mean'),
        order_count=('order_id', 'nunique'),
    ).reset_index()
    state_stats['delay_rate'] = (state_stats['delay_rate'] * 100).round(1)
    state_stats = state_stats[state_stats['order_count'] >= 50]
    state_stats = state_stats.sort_values('avg_delivery', ascending=True)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('各州平均交付周期', '各州延迟交付率'),
        horizontal_spacing=0.15,
    )

    fig.add_trace(
        go.Bar(
            y=state_stats['customer_state'],
            x=state_stats['avg_delivery'],
            orientation='h',
            marker_color='#3366CC',
            text=state_stats['avg_delivery'].round(1),
            textposition='outside',
            name='平均交付天数',
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            y=state_stats['customer_state'],
            x=state_stats['delay_rate'],
            orientation='h',
            marker_color='#DC3912',
            text=state_stats['delay_rate'].round(1).astype(str) + '%',
            textposition='outside',
            name='延迟率',
        ),
        row=1, col=2
    )

    fig.update_layout(
        title='各州交付时效对比（按客户所在州）',
        height=max(400, len(state_stats) * 20),
        showlegend=False,
    )
    fig.update_xaxes(title_text='平均交付天数', row=1, col=1)
    fig.update_xaxes(title_text='延迟率 (%)', row=1, col=2)

    return fig


def plot_delivery_by_category(data_dict):
    """品类交付时效对比"""
    cat = data_dict['category_summary']
    top_cats = cat.nlargest(15, 'total_orders')

    fig = px.scatter(
        top_cats,
        x='avg_delivery_days',
        y='delay_rate',
        size='total_orders',
        color='avg_delivery_days',
        text='category_name',
        color_continuous_scale='RdYlGn_r',
        title='各品类交付时效气泡图（气泡大小=订单量）',
        labels={
            'avg_delivery_days': '平均交付天数',
            'delay_rate': '延迟率 (%)',
            'total_orders': '订单数',
            'category_name': '品类'
        },
        size_max=50,
    )

    fig.update_traces(
        textposition='top center',
        textfont=dict(size=10),
    )
    fig.update_layout(height=550)
    fig.add_hline(
        y=data_dict['delivered']['is_delayed'].mean() * 100,
        line_dash="dash", line_color="gray",
        annotation_text=f"整体延迟率: {data_dict['delivered']['is_delayed'].mean() * 100:.1f}%"
    )

    return fig


def plot_delivery_heatmap(data_dict):
    """交付时效热力图（月度 × 品类）"""
    df = data_dict['delivered']

    pivot = df.pivot_table(
        values='delivery_time_days',
        index='category_name',
        columns='purchase_year_month',
        aggfunc='mean'
    )

    # 选取前12品类
    top_cats = data_dict['category_summary'].nlargest(12, 'total_orders')['category_name']
    pivot = pivot.loc[pivot.index.isin(top_cats)]
    pivot = pivot.sort_index(axis=1)

    fig = px.imshow(
        pivot,
        aspect='auto',
        color_continuous_scale='RdYlGn_r',
        title='月度 × 品类 交付周期热力图',
        labels=dict(x='月份', y='品类', color='平均交付天数'),
    )
    fig.update_layout(height=500)
    fig.update_xaxes(tickangle=45)

    return fig


def run_delivery_analysis(data_dict):
    """运行完整的交付时效分析"""
    st.header("供应商交付时效分析")

    # KPI 卡片
    kpis = delivery_kpi_cards(data_dict)
    cols = st.columns(6)
    labels = list(kpis.keys())
    values = list(kpis.values())
    for i, col in enumerate(cols):
        col.metric(labels[i], values[i])

    st.markdown("---")

    # 交付周期分布
    st.subheader("交付周期分布")
    st.plotly_chart(plot_delivery_distribution(data_dict), use_container_width=True)

    # 月度趋势
    st.subheader("月度交付时效趋势")
    st.plotly_chart(plot_monthly_delivery_trend(data_dict), use_container_width=True)

    # 双列布局
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("各州交付时效对比")
        st.plotly_chart(plot_delivery_by_state(data_dict), use_container_width=True)

    with col2:
        st.subheader("品类交付时效气泡图")
        st.plotly_chart(plot_delivery_by_category(data_dict), use_container_width=True)

    # 热力图
    st.subheader("交付周期热力图")
    st.plotly_chart(plot_delivery_heatmap(data_dict), use_container_width=True)

    # 延迟深度分析
    st.subheader("延迟交付深度分析")
    df = data_dict['delivered']
    delayed = df[df['is_delayed']]

    col1, col2 = st.columns(2)
    with col1:
        # 延迟天数分布
        delay_dist = delayed['delay_days'].value_counts().sort_index()
        delay_dist = delay_dist[delay_dist.index <= 30]  # 只看0-30天
        fig = px.bar(
            x=delay_dist.index, y=delay_dist.values,
            labels={'x': '延迟天数', 'y': '订单数'},
            title='延迟天数分布',
            color_discrete_sequence=['#DC3912'],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 延迟交付Top品类
        delay_by_cat = delayed.groupby('category_name').agg(
            delay_count=('order_id', 'nunique'),
            avg_delay=('delay_days', 'mean'),
        ).reset_index()
        delay_by_cat = delay_by_cat.nlargest(10, 'delay_count')

        fig = px.bar(
            delay_by_cat,
            x='delay_count', y='category_name',
            orientation='h',
            title='延迟交付最多的品类',
            color='avg_delay',
            color_continuous_scale='Reds',
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
