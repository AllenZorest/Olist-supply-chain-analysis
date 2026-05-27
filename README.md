# 🚚 Olist 电商平台供应链数据分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 基于巴西 Olist 电商数据集，构建**标准数仓分层架构 (ODS → DWD → DWS → ADS)**，完成交付时效、库存周转、满意度归因、销售趋势四大维度分析。Streamlit 看板从 DWS 聚合表读取，不再直读 CSV。

## 🏗️ 数仓分层架构

```
ADS  ←  Streamlit 看板（读 DWS 聚合表，非 CSV）
 ↑     5 个页面: 概览 / 交付 / 库存 / 满意度 / 销售趋势
DWS  ←  6 张汇总表
 ↑     日度指标 · 品类日度 · 州级日度 · 周度 · 品类全局 · 州级全局
DWD  ←  1 张订单宽表 + 4 张维度表
 ↑     客户维度 · 商品维度 · 卖家维度 · 日期维度 · dwd_order_detail
ODS  ←  8 张原始表 (CSV 原样入库)
       customers · sellers · products · orders · items · payments · reviews
```

| 层 | 表数 | ~行数 | 职责 |
|----|:--:|------|------|
| ODS | 8 | 50万+ | CSV 原样入库，不做任何转换 |
| DWD | 5 | 11万 | 清洗、JOIN 多表、派生交付/RFM 特征 |
| DWS | 6 | 3000+ | 日/周/品类/州级聚合，含 ABC 分类 |
| ADS | - | - | Streamlit 看板直接读 DWS 表 |

**一键 ETL**: `py dw/run_all.py`

## 📊 分析模块

| 模块 | 核心内容 | 关键指标 |
|------|---------|---------|
| 📦 供应商交付时效 | 周期分布、月度趋势、各州/品类对比、延迟热力图 | 平均交付天数、延迟率、按时率 |
| 📊 品类库存周转 | 销售速度、ABC 帕累托、品类-卖家关系 | 日均销量、收入集中度、ABC 分类 |
| 🚚 物流满意度归因 | 时效 vs 评分、因素相关性、区域对比 | 评分差异、相关系数、关键因素 |
| 📈 销售趋势分析 | 月度趋势、季节性热力、RFM 客户分层 | GMV、客单价、客户分层占比 |
| 💾 SQL 对比 | SQL vs Pandas 等价写法、数仓结构概览 | JOIN/GROUP BY/窗口函数/CTE |

## 🗂️ 项目结构

```
Olist-supply-chain-analysis/
├── app.py                           # Streamlit 主看板
├── pages/                           # 5 个独立分析页面
│   ├── 1_📦_供应商交付时效.py
│   ├── 2_📊_品类库存周转.py
│   ├── 3_🚚_物流满意度归因.py
│   ├── 4_📈_销售趋势分析.py
│   └── 5_💾_SQL分析对比.py
├── modules/                         # 分析模块（可视化函数）
│   ├── data_loader.py               # CSV 数据加载（旧版/回退）
│   ├── delivery_analysis.py
│   ├── inventory_analysis.py
│   ├── logistics_analysis.py
│   └── sales_analysis.py
├── dw/                              # 数仓 ETL 模块 ★
│   ├── config.py                    # MySQL 连接配置
│   ├── run_all.py                   # 一键 ETL 编排 (ODS→DWD→DWS)
│   ├── ads/
│   │   ├── queries.py               # ADS 查询函数
│   │   └── dw_loader.py             # 数仓版数据加载器
│   ├── ods/                         # ODS 层
│   ├── dwd/                         # DWD 层
│   └── dws/                         # DWS 层
├── sql/                             # DDL 定义
│   ├── ods_setup.sql                # ODS 建表语句
│   ├── dwd_setup.sql                # DWD 建表语句
│   ├── dws_setup.sql                # DWS 建表语句
│   ├── schema.sql                   # 原始 Schema（兼容）
│   ├── analysis_queries.sql         # 21条业务 SQL
│   ├── sql_analyzer.py              # SQL 执行器
│   └── import_to_mysql.py           # CSV 导入脚本
├── utils/
│   └── helpers.py
├── data/                            # 数据集（CSV）
├── requirements.txt
└── README.md
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/AllenZorest/Olist-supply-chain-analysis.git
cd Olist-supply-chain-analysis
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载数据集

将 9 个 CSV 文件放入 `data/` 目录。

从 [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 下载。

### 4. 运行数仓 ETL（推荐）

```bash
# 修改 dw/config.py 中的 MySQL 密码，然后:
py dw/run_all.py
```

### 5. 启动看板

```bash
streamlit run app.py
```

浏览器访问 `http://localhost:8501`。

> **无 MySQL 也能用**: 项目会自动回退到 CSV 本地加载模式。

## 🛠️ 技术栈

| 领域 | 技术 |
|------|------|
| 看板框架 | Streamlit |
| 数据库 | MySQL 8.0 (数仓) / SQLite (回退) |
| 数据处理 | Pandas, NumPy |
| 可视化 | Plotly, Matplotlib, Seaborn |
| ETL | Python + pymysql |

## 🎯 岗位匹配

| 岗位要求 | 项目体现 |
|---------|---------|
| 供应链分析 | 四大模块覆盖交付/库存/物流/销售 |
| SQL/MySQL | 数仓分层 + 21条业务查询 + DDL/ETL |
| Python | 全 Python 实现，模块化架构 |
| 数据可视化 | Streamlit + Plotly 交互看板 |
| 业务需求分析 | 每个分析从业务问题出发 |

## 📝 面试话术

> "这个项目我构建了标准的数据仓库分层架构。底层 ODS 存原始 CSV，DWD 通过多表 JOIN 构建订单宽表，DWS 做日/周聚合，最后 ADS 用 Streamlit 展示。整个流程 ODS→DWD→DWS 一键 ETL，看板从 DWS 直接读聚合表。核心分析逻辑既用 Pandas 实现，也用 SQL 重写了一遍，JOIN、GROUP BY、窗口函数、CTE 都覆盖到了。"

## 📜 License

MIT
