"""
数仓分层模块 (Data Warehouse Layers)

分层架构:
    ODS (Operational Data Store)  →  原始 CSV 原样入库
    DWD (Data Warehouse Detail)   →  订单明细宽表 + 维度表
    DWS (Data Warehouse Summary)  →  日聚合 / 周聚合
    ADS (Application Data Service)→  Streamlit 看板
"""
