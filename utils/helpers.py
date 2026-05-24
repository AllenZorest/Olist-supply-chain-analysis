"""
通用工具函数
"""
import pandas as pd
import numpy as np
from datetime import datetime

# 巴西各州代码映射
STATE_MAP = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
    'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
    'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul',
    'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná',
    'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
    'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina',
    'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'
}

# 巴西各大区
REGION_MAP = {
    'Norte': ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
    'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
    'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
    'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
    'Sul': ['PR', 'RS', 'SC']
}


def get_state_name(abbr: str) -> str:
    """获取州全名"""
    return STATE_MAP.get(abbr, abbr)


def get_region(state_abbr: str) -> str:
    """获取州所属大区"""
    for region, states in REGION_MAP.items():
        if state_abbr in states:
            return region
    return 'Unknown'


def format_currency(value: float) -> str:
    """格式化巴西雷亚尔"""
    return f"R$ {value:,.2f}"


def format_percent(value: float) -> str:
    """格式化百分比"""
    return f"{value:.1f}%"


def days_between(start, end) -> int:
    """计算两个日期之间的天数"""
    if pd.isna(start) or pd.isna(end):
        return np.nan
    return (end - start).days


def style_negative_red(val):
    """为负值标红"""
    color = 'red' if isinstance(val, (int, float)) and val < 0 else 'black'
    return f'color: {color}'


def card_metric(title, value, delta=None, delta_color="normal"):
    """生成 Streamlit metric 卡片数据"""
    return {"title": title, "value": value, "delta": delta, "delta_color": delta_color}
