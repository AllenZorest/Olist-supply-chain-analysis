"""
品类库存周转分析模块

虽然 Olist 数据集无直接库存数据，但我们可以通过以下代理指标分析：
- 品类销售速度（日均销量）
- 卖家-品类集中度
- 品类销售稳定性
- 周转效率评估（基于订单频率）
- 长尾品类 vs 头部品类

这些指标可以帮助评估各品类的"库存消化能力"
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def inventory_kpi_cards(data_dict):
    """库存周转 KPI 卡片"""
    df = data_dict['delivered']
    cat = data_dict['category_summary']

    top3_share = cat.nlargest(3, 'total_revenue')['total_revenue'].sum() / cat['total_revenue'].sum() * 100
    total_categories = len(cat)

    # 日均销量
    date_range = (df['order_purchase_timestamp'].max() - df['order_purchase_timestamp'].min()).days
    daily_orders = len(df) / max(date_range, 1)

    # 卖家平均经营品类数
    seller_cats = df.groupby('seller_id')['category_name'].nunique()
    avg_cats_per_seller = seller_cats.mean()

    # 品类平均卖家数
    cat_sellers = cat['unique_sellers'].mean()

    return {
        '品类总数': str(total_categories),
        '头部3品类收入占比': f"{top3_share:.1f}%",
        '日均订单量': f"{daily_orders:.0f} 单",
        '卖家平均品类数': f"{avg_cats_per_seller:.1f} 个",
        '品类平均卖家数': f"{cat_sellers:.0f} 个",
        '总商品数': df['product_id'].nunique(),
    }


def plot_category_treemap(data_dict):
    """品类结构树状图"""
    cat = data_dict['category_summary']

    fig = px.treemap(
        cat.nlargest(30, 'total_revenue'),
        path=['category_name'],
        values='total_revenue',
        color='delay_rate',
        color_continuous_scale='RdYlGn_r',
        title='品类收入结构 & 延迟率概览',
        hover_data={
            'total_orders': True,
            'avg_price': ':.2f',
            'delay_rate': ':.1f',
            'avg_delivery_days': ':.1f',
        }
    )
    fig.update_traces(
        textinfo='label+value',
        texttemplate='%{label}<br>R$%{value:,.0f}',
    )
    fig.update_layout(height=550)

    return fig


def plot_sales_velocity(data_dict):
    """品类销售速度分析（日均销量）"""
    df = data_dict['delivered']

    date_range = (df['order_purchase_timestamp'].max() - df['order_purchase_timestamp'].min()).days

    velocity = df.groupby('category_name').agg(
        total_sales=('order_id', 'nunique'),
        total_revenue=('price', 'sum'),
    ).reset_index()

    velocity['daily_sales'] = velocity['total_sales'] / max(date_range, 1)
    velocity['daily_revenue'] = velocity['total_revenue'] / max(date_range, 1)

    velocity = velocity.nlargest(20, 'daily_sales').sort_values('daily_sales', ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=velocity['category_name'],
        x=velocity['daily_sales'],
        name='日均销量（单）',
        orientation='h',
        marker_color='#3366CC',
        text=velocity['daily_sales'].round(1),
        textposition='outside',
    ))

    fig.update_layout(
        title='Top 20 品类日均销量',
        height=500,
        xaxis_title='日均销量（单/天）',
        yaxis=dict(autorange="reversed"),
    )

    return fig


def plot_category_concentration(data_dict):
    """品类集中度分析（ABC分析）"""
    cat = data_dict['category_summary'].copy()
    cat = cat.sort_values('total_revenue', ascending=False)
    cat['cum_pct'] = cat['total_revenue'].cumsum() / cat['total_revenue'].sum() * 100
    cat['rank'] = range(1, len(cat) + 1)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=cat['category_name'],
            y=cat['total_revenue'],
            name='收入',
            marker_color='#3366CC',
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=cat['category_name'],
            y=cat['cum_pct'],
            name='累计占比',
            mode='lines+markers',
            line=dict(color='#DC3912', width=2),
            marker=dict(size=4),
        ),
        secondary_y=True,
    )

    # ABC 分界线
    fig.add_hline(y=70, line_dash="dash", line_color="green",
                  annotation_text="A类 70%", secondary_y=True)
    fig.add_hline(y=90, line_dash="dash", line_color="orange",
                  annotation_text="B类 90%", secondary_y=True)

    fig.update_layout(
        title='品类收入 ABC 分析（帕累托图）',
        height=450,
        hovermode='x unified',
    )
    fig.update_xaxes(tickangle=45, showticklabels=False)
    fig.update_yaxes(title_text='收入 (R$)', secondary_y=False)
    fig.update_yaxes(title_text='累计占比 (%)', secondary_y=True)

    # 标注ABC类别数量
    a_count = (cat['cum_pct'] <= 70).sum()
    b_count = ((cat['cum_pct'] > 70) & (cat['cum_pct'] <= 90)).sum()
    c_count = (cat['cum_pct'] > 90).sum()

    fig.add_annotation(
        text=f"A类: {a_count}个 | B类: {b_count}个 | C类: {c_count}个",
        xref="paper", yref="paper",
        x=0.5, y=1.08, showarrow=False,
        font=dict(size=12),
    )

    return fig


def plot_seller_category_network(data_dict):
    """卖家-品类关系分析"""
    df = data_dict['delivered']

    # 卖家经营品类数分布
    seller_cats = df.groupby('seller_id')['category_name'].nunique().reset_index()
    seller_cats.columns = ['seller_id', 'num_categories']

    dist = seller_cats['num_categories'].value_counts().sort_index()

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('卖家经营品类数分布', '品类卖家竞争度Top15'),
    )

    fig.add_trace(
        go.Bar(
            x=dist.index[:15],
            y=dist.values[:15],
            marker_color='#3366CC',
            name='卖家数',
        ),
        row=1, col=1
    )

    # 品类卖家竞争度
    cat_competition = data_dict['category_summary'].nlargest(15, 'unique_sellers')
    fig.add_trace(
        go.Bar(
            y=cat_competition['category_name'],
            x=cat_competition['unique_sellers'],
            orientation='h',
            marker_color='#FF9900',
            name='卖家数',
            text=cat_competition['unique_sellers'],
            textposition='outside',
        ),
        row=1, col=2
    )

    fig.update_layout(
        title='卖家-品类关系分析',
        height=450,
        showlegend=False,
    )
    fig.update_xaxes(title_text='经营品类数', row=1, col=1)
    fig.update_yaxes(title_text='卖家数量', row=1, col=1)
    fig.update_xaxes(title_text='卖家数量', row=1, col=2)
    fig.update_yaxes(autorange="reversed", row=1, col=2)

    return fig


def plot_monthly_category_dynamics(data_dict):
    """品类月度销售动态"""
    df = data_dict['delivered']

    # 取Top品类月度趋势
    top_cats = data_dict['category_summary'].nlargest(8, 'total_revenue')['category_name'].tolist()

    monthly_cat = df[df['category_name'].isin(top_cats)].groupby(
        ['purchase_year_month', 'category_name']
    ).agg(
        revenue=('price', 'sum'),
        orders=('order_id', 'nunique'),
    ).reset_index()
    monthly_cat['purchase_year_month'] = monthly_cat['purchase_year_month'].astype(str)

    fig = px.line(
        monthly_cat,
        x='purchase_year_month',
        y='revenue',
        color='category_name',
        title='Top 8 品类月度收入趋势',
        labels={
            'purchase_year_month': '月份',
            'revenue': '收入 (R$)',
            'category_name': '品类',
        },
        markers=True,
    )
    fig.update_layout(height=450, hovermode='x unified')

    return fig


def run_inventory_analysis(data_dict):
    """运行完整的库存周转分析"""
    st.header("品类库存周转分析")

    # KPI 卡片
    kpis = inventory_kpi_cards(data_dict)
    cols = st.columns(6)
    labels = list(kpis.keys())
    values = list(kpis.values())
    for i, col in enumerate(cols):
        col.metric(labels[i], values[i])

    st.markdown("---")

    # 品类结构树状图
    st.subheader("品类结构全景")
    st.plotly_chart(plot_category_treemap(data_dict), use_container_width=True)

    # 双列布局
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("品类销售速度")
        st.plotly_chart(plot_sales_velocity(data_dict), use_container_width=True)

    with col2:
        st.subheader("ABC 品类分析")
        st.plotly_chart(plot_category_concentration(data_dict), use_container_width=True)

    # 卖家-品类关系
    st.subheader("卖家-品类关系")
    st.plotly_chart(plot_seller_category_network(data_dict), use_container_width=True)

    # 月度动态
    st.subheader("品类月度销售动态")
    st.plotly_chart(plot_monthly_category_dynamics(data_dict), use_container_width=True)

    # 详细数据表
    st.subheader("品类详细数据")
    detail_cols = ['category_name', 'total_orders', 'total_revenue', 'avg_price',
                   'avg_delivery_days', 'delay_rate', 'unique_products', 'unique_sellers']
    cat_detail = data_dict['category_summary'][detail_cols].copy()
    cat_detail = cat_detail.sort_values('total_revenue', ascending=False)
    cat_detail.columns = ['品类', '订单数', '总收入', '均价', '平均交付天数', '延迟率(%)', '商品数', '卖家数']
    cat_detail['总收入'] = cat_detail['总收入'].round(0)
    cat_detail['均价'] = cat_detail['均价'].round(2)
    cat_detail['平均交付天数'] = cat_detail['平均交付天数'].round(1)

    st.dataframe(cat_detail, use_container_width=True, hide_index=True)
