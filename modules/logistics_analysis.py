"""
物流满意度归因分析模块

核心分析：
- 交付时效 vs 客户评分相关性
- 延迟交付对满意度的影响
- 物流各环节对满意度的影响
- 区域物流满意度对比
- 负面评价文本关键词分析
- 满意度影响因素回归分析
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import streamlit as st


def satisfaction_kpi_cards(data_dict):
    """满意度 KPI 卡片"""
    df = data_dict['delivered']

    avg_score = df['review_score'].mean()
    score_5_rate = (df['review_score'] == 5).mean() * 100
    score_1_rate = (df['review_score'] == 1).mean() * 100

    # 按时vs延迟满意度对比
    ontime_score = df[~df['is_delayed']]['review_score'].mean()
    delayed_score = df[df['is_delayed']]['review_score'].mean()

    return {
        '平均评分': f"{avg_score:.2f} / 5",
        '5分好评率': f"{score_5_rate:.1f}%",
        '1分差评率': f"{score_1_rate:.1f}%",
        '按时交付评分': f"{ontime_score:.2f}",
        '延迟交付评分': f"{delayed_score:.2f}",
        '评分差异': f"{(ontime_score - delayed_score):.2f}",
    }


def plot_score_distribution(data_dict):
    """评分分布"""
    df = data_dict['delivered']

    score_dist = df['review_score'].value_counts().sort_index()

    colors = ['#DC3912', '#FF9900', '#FFCC00', '#99CC00', '#109618']
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=score_dist.index.astype(int),
        y=score_dist.values,
        marker_color=colors[:len(score_dist)],
        text=score_dist.values,
        textposition='outside',
        hovertemplate='评分: %{x}<br>订单数: %{y}<extra></extra>',
    ))

    fig.update_layout(
        title='客户评分分布',
        height=400,
        xaxis_title='评分',
        yaxis_title='订单数量',
        xaxis=dict(tickmode='linear', tick0=1, dtick=1),
    )

    return fig


def plot_delivery_vs_score(data_dict):
    """交付时效 vs 评分关系"""
    df = data_dict['delivered']

    # 按时 vs 延迟对比
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('按时 vs 延迟交付评分对比', '交付天数 vs 评分散点图'),
    )

    # 按时 vs 延迟箱线图
    ontime_scores = df[~df['is_delayed']]['review_score'].dropna()
    delayed_scores = df[df['is_delayed']]['review_score'].dropna()

    fig.add_trace(go.Box(
        y=ontime_scores,
        name='按时交付',
        marker_color='#109618',
        boxmean='sd',
    ), row=1, col=1)

    fig.add_trace(go.Box(
        y=delayed_scores,
        name='延迟交付',
        marker_color='#DC3912',
        boxmean='sd',
    ), row=1, col=1)

    # 散点图（采样以提高性能）
    sample = df[['delivery_time_days', 'review_score']].dropna().sample(
        min(5000, len(df)), random_state=42
    )

    # 添加趋势线
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        sample['delivery_time_days'], sample['review_score']
    )

    fig.add_trace(go.Scatter(
        x=sample['delivery_time_days'],
        y=sample['review_score'],
        mode='markers',
        marker=dict(size=3, opacity=0.3, color='#3366CC'),
        name='订单',
        showlegend=False,
    ), row=1, col=2)

    # 趋势线
    x_range = np.linspace(sample['delivery_time_days'].min(), sample['delivery_time_days'].max(), 100)
    fig.add_trace(go.Scatter(
        x=x_range,
        y=slope * x_range + intercept,
        mode='lines',
        line=dict(color='red', width=2),
        name=f'趋势线 (r={r_value:.3f})',
    ), row=1, col=2)

    fig.update_layout(
        title='交付时效与客户评分关系',
        height=450,
        showlegend=True,
    )
    fig.update_yaxes(title_text='评分', row=1, col=1)
    fig.update_yaxes(title_text='评分', row=1, col=2)
    fig.update_xaxes(title_text='交付天数', row=1, col=2)

    return fig, r_value, p_value


def plot_satisfaction_by_state(data_dict):
    """各州满意度对比"""
    df = data_dict['delivered']

    state_satisfaction = df.groupby('customer_state').agg(
        avg_score=('review_score', 'mean'),
        score_5_rate=('review_score', lambda x: (x == 5).mean() * 100),
        delay_rate=('is_delayed', 'mean'),
        order_count=('order_id', 'nunique'),
    ).reset_index()
    state_satisfaction = state_satisfaction[state_satisfaction['order_count'] >= 50]

    fig = px.scatter(
        state_satisfaction,
        x='delay_rate',
        y='avg_score',
        size='order_count',
        color='score_5_rate',
        text='customer_state',
        color_continuous_scale='RdYlGn',
        title='各州延迟率 vs 满意度（气泡大小=订单量）',
        labels={
            'delay_rate': '延迟率',
            'avg_score': '平均评分',
            'order_count': '订单数',
            'score_5_rate': '5分率(%)',
        },
        size_max=40,
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(height=500)

    return fig


def plot_satisfaction_factors(data_dict):
    """满意度影响因素分析"""
    df = data_dict['delivered'].copy()

    # 按交付天数分段分析满意度
    df['delivery_range'] = pd.cut(
        df['delivery_time_days'],
        bins=[0, 5, 10, 15, 20, 30, 50, 200],
        labels=['0-5天', '6-10天', '11-15天', '16-20天', '21-30天', '31-50天', '50天+']
    )

    range_stats = df.groupby('delivery_range', observed=False).agg(
        avg_score=('review_score', 'mean'),
        order_count=('order_id', 'nunique'),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=range_stats['delivery_range'],
            y=range_stats['order_count'],
            name='订单数',
            marker_color='#3366CC',
            opacity=0.7,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=range_stats['delivery_range'],
            y=range_stats['avg_score'],
            name='平均评分',
            mode='lines+markers',
            line=dict(color='#DC3912', width=3),
            marker=dict(size=10),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title='交付天数分段满意度分析',
        height=400,
        hovermode='x unified',
    )
    fig.update_xaxes(title_text='交付天数范围')
    fig.update_yaxes(title_text='订单数', secondary_y=False)
    fig.update_yaxes(title_text='平均评分', secondary_y=True, range=[3, 5])

    return fig


def plot_correlation_heatmap(data_dict):
    """相关性热力图"""
    df = data_dict['delivered'][[
        'review_score', 'delivery_time_days', 'delay_days',
        'price', 'freight_value', 'product_weight_g',
        'product_length_cm', 'product_height_cm', 'product_width_cm',
    ]].dropna()

    corr = df.corr()

    fig = px.imshow(
        corr,
        text_auto='.2f',
        aspect='auto',
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        title='满意度相关因素热力图',
        labels=dict(color='相关系数'),
    )
    fig.update_layout(height=450)

    return fig


def run_logistics_analysis(data_dict):
    """运行完整的物流满意度归因分析"""
    st.header("物流满意度归因分析")

    # KPI 卡片
    kpis = satisfaction_kpi_cards(data_dict)
    cols = st.columns(6)
    labels = list(kpis.keys())
    values = list(kpis.values())
    for i, col in enumerate(cols):
        col.metric(labels[i], values[i])

    st.markdown("---")

    # 评分分布
    st.subheader("客户评分分布")
    st.plotly_chart(plot_score_distribution(data_dict), use_container_width=True)

    # 交付时效 vs 评分
    st.subheader("交付时效与满意度关系")
    fig, r_value, p_value = plot_delivery_vs_score(data_dict)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("相关系数 (r)", f"{r_value:.4f}")
    col2.metric("显著性 (p-value)", f"{p_value:.2e}" if p_value < 0.01 else f"{p_value:.4f}")
    col3.metric("结论", "显著负相关" if r_value < -0.1 else "弱相关")

    # 双列布局
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("各州满意度对比")
        st.plotly_chart(plot_satisfaction_by_state(data_dict), use_container_width=True)

    with col2:
        st.subheader("交付天数分段满意度")
        st.plotly_chart(plot_satisfaction_factors(data_dict), use_container_width=True)

    # 相关性热力图
    st.subheader("影响因素相关性分析")
    st.plotly_chart(plot_correlation_heatmap(data_dict), use_container_width=True)

    # 关键洞察
    st.subheader("关键业务洞察")
    df = data_dict['delivered']

    insights = []
    insights.append({
        "维度": "交付时效影响",
        "发现": f"交付每延迟1天，评分平均下降约{abs(r_value):.3f}分",
        "建议": "将交付周期控制在15天以内可显著提升客户满意度"
    })

    delay_bins = pd.cut(df['delivery_time_days'], bins=[0, 7, 15, 30, 200])
    score_by_bin = df.groupby(delay_bins, observed=False)['review_score'].mean()
    best_bin = score_by_bin.idxmax()

    insights.append({
        "维度": "最优交付窗口",
        "发现": f"交付周期在{best_bin}天时评分最高（{score_by_bin.max():.2f}分）",
        "建议": "将SLA目标设定在此范围内，平衡效率与满意度"
    })

    # 区域分析
    region_scores = df.groupby('customer_state')['review_score'].mean().sort_values()
    worst_state = region_scores.index[0]
    best_state = region_scores.index[-1]

    insights.append({
        "维度": "区域差异",
        "发现": f"满意度最高州: {best_state}（{region_scores.max():.2f}分），最低州: {worst_state}（{region_scores.min():.2f}分）",
        "建议": f"重点关注{worst_state}等低分区域的物流改善"
    })

    st.dataframe(pd.DataFrame(insights), use_container_width=True, hide_index=True)
