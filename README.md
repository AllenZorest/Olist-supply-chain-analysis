# Olist 电商平台供应链数据分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 基于巴西 Olist 电商数据集（~100K 订单），构建 **CSV + MySQL 数仓双模式** 供应链分析平台。支持标准数仓分层 (ODS → DWD → DWS → ADS)，覆盖交付时效、库存周转、满意度归因、销售趋势四大维度。
>
> **两种模式随时切换，无 MySQL 也能直接用 CSV 模式运行。**

## 数据源双模式

| 模式 | 数据来源 | 适用场景 |
|------|---------|---------|
| 📁 CSV | `data/` 目录下 8 个 CSV 文件 | 快速启动、无需数据库 |
| 🗄️ MySQL 数仓 | ODS → DWD → DWS 标准分层表 | 展示数仓设计能力、面试加分 |

看板侧边栏一键切换，所有分析页面自动适配。

## 🏗️ 数仓分层架构

```
ADS  ←  Streamlit 看板（双模式：CSV 直读 / DWS 聚合表）
 ↑
DWS  ←  6 张汇总表（日度 · 周度 · 品类 · 州级 + ABC 分类）
 ↑
DWD  ←  1 张订单宽表 + 4 张维度表（客户/商品/卖家/日期）
 ↑
ODS  ←  8 张原始表（CSV 原样入库，含 etl_date 审计字段）
```

| 层 | 表数 | ~行数 | 职责 |
|----|:--:|------|------|
| ODS | 8 | 50万+ | CSV 原样入库，不做任何转换 |
| DWD | 5 | 11万 | 清洗、多表 JOIN、派生交付/RFM 特征 |
| DWS | 6 | 3,000+ | 日/周/品类/州级聚合，含 ABC 分类 |
| ADS | - | - | Streamlit 看板从 DWS 表读取 |

**一键 ETL**：`py dw/run_all.py`（支持 `--layer ods/dwd/dws` 分层运行）

## 📊 页面结构

| 页面 | 内容 | 说明 |
|------|------|------|
| 🏠 数据总览 | 全局 KPI + 各模块关键图表摘要 | 一目了然的仪表盘 |
| 📦 供应商交付时效 | 周期分布、月度趋势、州/品类对比、延迟热力图 | 平均交付天数、延迟率、按时率 |
| 📊 品类库存周转 | 销售速度、ABC 帕累托、品类-卖家关系 | 日均销量、收入集中度、ABC 分类 |
| 🚚 物流满意度归因 | 时效 vs 评分、因素相关性、区域对比 | 评分差异、相关系数、订单漏斗 |
| 📈 销售趋势分析 | 月度趋势、季节性热力、RFM 客户分层 | GMV、客单价、客户分层占比 |
| 💾 SQL 分析对比 | SQL vs Pandas 等价写法、数仓结构概览 | JOIN/GROUP BY/窗口函数/CTE |

> 数据总览页展示各模块 2-4 张核心图表，点击子页面可查看完整分析。

## 🗂️ 项目结构

```
Olist-supply-chain-analysis/
├── datall.py                        # Streamlit 主入口（数据总览 + 导航）
├── pages/                           # 5 个独立分析子页面
│   ├── 1_📦_供应商交付时效.py
│   ├── 2_📊_品类库存周转.py
│   ├── 3_🚚_物流满意度归因.py
│   ├── 4_📈_销售趋势分析.py
│   └── 5_💾_SQL分析对比.py
├── modules/                         # 分析模块（图表函数）
│   ├── data_loader.py               # CSV 模式数据加载
│   ├── delivery_analysis.py
│   ├── inventory_analysis.py
│   ├── logistics_analysis.py
│   └── sales_analysis.py
├── dw/                              # 数仓 ETL 模块 ★
│   ├── config.py                    # MySQL 连接配置
│   ├── run_all.py                   # 一键 ETL 编排（ODS→DWD→DWS）
│   ├── hive_ddl.sql                 # Hive DDL 翻译版（PARQUET 列存）
│   ├── ads/
│   │   ├── queries.py               # ADS 查询函数
│   │   └── dw_loader.py             # MySQL 数仓数据加载器
│   ├── ods/                         # ODS 层 ETL
│   ├── dwd/                         # DWD 层 ETL
│   └── dws/                         # DWS 层 ETL
├── sql/                             # DDL + 业务 SQL
│   ├── ods_setup.sql                # ODS 建表
│   ├── dwd_setup.sql                # DWD 建表
│   ├── dws_setup.sql                # DWS 建表
│   ├── schema.sql                   # 原始 Schema（兼容）
│   ├── analysis_queries.sql         # 21 条业务 SQL
│   ├── sql_analyzer.py              # SQL 执行引擎
│   └── import_to_mysql.py           # CSV → MySQL 导入脚本
├── utils/
│   └── helpers.py
├── data/                            # 数据集（CSV，需自行下载）
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

从 [Kaggle - Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 下载 9 个 CSV 文件，放入 `data/` 目录。

### 4. 启动看板（CSV 模式，无需 MySQL）

```bash
streamlit run datall.py
```

浏览器访问 `http://localhost:8501`，侧边栏选择「📁 CSV」即可。

### 5. 启用 MySQL 数仓模式（可选）

```bash
# 1. 修改 dw/config.py 中的 MySQL 密码
# 2. 运行 ETL
py dw/run_all.py
# 3. 启动看板，侧边栏切换为「🗄️ MySQL 数仓」
streamlit run datall.py
```

## 🛠️ 技术栈

| 领域 | 技术 |
|------|------|
| 看板框架 | Streamlit（`st.navigation()` 统一路由） |
| 数据库 | MySQL 8.0（数仓）/ CSV 本地文件 |
| 数据处理 | Pandas、NumPy |
| 可视化 | Plotly（30+ 交互图表） |
| ETL | Python + pymysql |

## 🎯 岗位匹配

| 岗位要求 | 项目体现 |
|---------|---------|
| 供应链分析 | 四大模块覆盖交付/库存/物流/销售 |
| SQL/MySQL | 数仓分层 + 21 条业务查询 + DDL/ETL |
| Python | 全 Python 实现，模块化架构 |
| 数据可视化 | Streamlit + Plotly 交互看板 |
| 业务需求分析 | Dashboard → Drill-down 分层设计 |
| 大数据 | Hive DDL 翻译版（PARQUET 列存） |


## 📜 项目更新历程

### v3.0 — 2026-05-28：一体化集成版（当前版本）

**文件重命名**：`run_datall.py` → `datall.py`（启动命令更简洁）

**Bug 修复**：
- 数仓模式下销售趋势「订单漏斗」报 KeyError `raw`：`dw_loader.py` 缺少 `data_dict['raw']` 键，从 delivered DataFrame 提取 `order_id` + `order_status` 补全
- 数仓模式下品类库存周转报 KeyError `unique_products`：DWS 表无此字段，改为从 delivered 实时 groupby 计算后 merge
- `delay_rate` 格式不一致：DWS 存小数（0.085），CSV 存百分比（8.5），`dw_loader.py` 加载时统一 `* 100` 转换

### v2.0 — 2026-05-28：Dashboard → Drill-down 架构重构

**页面架构**（A 方案）：
- `app.py` 重构为数据总览页，采用 `st.navigation()` + `st.Page()` 统一路由
- 主页精简：每个 tab 只放 KPI + 2-4 张核心图表，不再堆砌全部内容
- 子页面保留完整分析，主页底部有导航提示引导用户深入查看
- 侧边栏显示「🏠 数据总览」而非文件名

**Bug 修复**：
- 子页面数据源选择失效：Streamlit session_state 跨页面共享依赖 widget key，`st.navigation()` 架构下改用统一的 `st.radio(key="data_source_radio")` 集中管理
- 主页面数据源切换时 session_state 里 key 在 widget 创建前不存在导致默认 CSV：配合 `st.navigation()` 生命周期修复

### v1.3 — 2026-05-28：数仓模式兼容性

**双模式数据源**：
- 侧边栏添加 `st.radio` 切换「📁 CSV」/「🗄️ MySQL 数仓」
- Streamlit 看板（含所有子页面）均支持两种模式自动切换
- 无 MySQL 时自动回退 CSV 模式，零配置可用

**Bug 修复**：
- `is_delayed` 布尔索引报错：MySQL TINYINT → pandas int64，旧模块 `df[df['is_delayed']]` 失败 → `astype(bool)` 转换
- `delivery_time_days` KeyError：DWS 列名为 `delivery_days`，`dw_loader.py` 加载时 rename
- `purchase_date` KeyError：CSV 版本无此列，`data_loader.py` 从 `order_purchase_timestamp` 派生
- `dim_products` 缺 `product_length_cm` / `product_height_cm` / `product_width_cm` 列：`dwd_setup.sql` DDL 和 `run_all.py` INSERT 同步补全

### v1.2 — 2026-05-27：DWS 层调试 & Hive 扩展

**DWS 层**：
- `year_week` VARCHAR(7) → VARCHAR(8)：`2018-W01` 是 8 字符
- pymysql 不支持多语句执行：ABC 分类 `SET @total` / `SET @cum` / `UPDATE` 拆为三次 `execute()`
- `week_start_date` / `week_end_date` 别名缺失：SELECT 中补上 `AS` 别名
- DWS 7 个步骤全部跑通（6/6 张表）

**Hive 扩展**：新增 `dw/hive_ddl.sql`（473 行），将全部 MySQL 数仓表翻译为 Hive DDL（STRING/TIMESTAMP/PARTITIONED BY/STORED AS PARQUET），附录含 ODS→DWD Hive ETL INSERT 示例

### v1.1 — 2026-05-25：数仓分层架构 & Git 分支分离

**数仓升级**：
- 新增 `dw/` 目录，实现 ODS → DWD → DWS → ADS 标准四层架构
- `dw/run_all.py` 一键 ETL 编排，支持 `--layer` 参数分层运行
- 6 张 DWS 聚合表：日度指标、品类日度、州级日度、周度指标、品类全局、州级全局（含 ABC 分类）
- `dw/ads/dw_loader.py` 数仓数据加载器

**Bug 修复**：热力图 `Period` 类型 JSON 序列化报错 → `purchase_year_month.astype(str)` 转换

**分支管理**：`master` 保留原始 Pandas MVP，`dw-upgrade` 为数仓升级版

### v1.0 — 2026-05-24：初始版本

- 四大分析模块：交付时效、库存周转、满意度归因、销售趋势
- Streamlit 多页面看板（主页面 Tab + 5 个子页面）
- 30+ Plotly 交互图表
- SQL 数据库模块：MySQL 建表、21 条业务查询、SQL vs Pandas 对比页面
- CSV 本地加载模式，Kaggle 数据集自动下载

## 📜 License

MIT
