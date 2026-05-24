# 🚚 Olist 电商平台供应链数据分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 基于巴西最大电商平台 Olist 公开数据集，完成供应商交付时效、品类库存周转、物流满意度归因、销售趋势四大维度的供应链数据分析。
>

## 📊 项目预览

![Streamlit Dashboard](https://img.icons8.com/color/96/dashboard-layout.png)

交互式 Streamlit 看板，覆盖四大分析模块：

| 模块 | 核心分析内容 | 关键指标 |
|------|-------------|---------|
| 📦 **供应商交付时效** | 交付周期分布、按时交付率、延迟分析 | 平均交付周期、延迟率、按时率 |
| 📊 **品类库存周转** | 销售速度、ABC分析、库存周转估算 | 日均销量、品类集中度、周转效率 |
| 🚚 **物流满意度归因** | 时效 vs 评分、区域对比、因素分析 | 评分差异、相关性系数、关键因素 |
| 📈 **销售趋势分析** | 月度趋势、季节性、RFM分层 | 销售额、客单价、客户分层占比 |

## 🗂️ 项目结构

```
olist-supply-chain-analysis/
├── app.py                          # Streamlit 主应用（概览页 + Tab切换）
├── pages/                          # Streamlit 多页面
│   ├── 1_📦_供应商交付时效.py
│   ├── 2_📊_品类库存周转.py
│   ├── 3_🚚_物流满意度归因.py
│   └── 4_📈_销售趋势分析.py
├── modules/                        # 核心分析模块
│   ├── data_loader.py              # 数据加载与预处理
│   ├── delivery_analysis.py        # 交付时效分析
│   ├── inventory_analysis.py       # 库存周转分析
│   ├── logistics_analysis.py       # 物流满意度分析
│   └── sales_analysis.py           # 销售趋势分析
├── utils/
│   └── helpers.py                  # 工具函数
├── data/                           # 数据集目录
├── requirements.txt                # Python 依赖
└── README.md                       # 本文件
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/AllenZorest/olist-supply-chain-analysis.git
cd olist-supply-chain-analysis
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载数据集

**方式一：自动下载（推荐）**

```bash
python -c "import kagglehub; kagglehub.dataset_download('olistbr/brazilian-ecommerce')"
```

**方式二：手动下载**

1. 访问 [Kaggle Olist Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
2. 下载所有 CSV 文件
3. 放入 `data/` 目录

### 4. 启动看板

```bash
streamlit run app.py
```

浏览器访问 `http://localhost:8501` 即可查看交互式看板。

## 📈 分析模块详解

### 📦 供应商交付时效分析

**业务问题**：供应商能否按时交付？哪些环节是瓶颈？

**分析内容**：
- 交付周期分布（直方图 + 箱线图）
- 月度交付时效趋势
- 各州/品类交付时效对比
- 延迟交付深度分析（延迟天数分布、延迟Top品类）
- 交付周期热力图（月度 × 品类）

**关键发现**：
- 确定最佳交付窗口（SLA目标）
- 识别高频延迟品类和区域
- 分析延迟对客户满意度的影响程度

### 📊 品类库存周转分析

**业务问题**：哪些品类周转快？库存结构是否合理？

**分析内容**：
- 品类结构树状图（收入 + 延迟率）
- 品类销售速度排名（日均销量）
- ABC 帕累托分析（品类集中度）
- 卖家-品类关系网络
- Top品类月度收入趋势

**关键发现**：
- 头部3品类收入占比
- 长尾品类识别
- 品类竞争程度评估

### 🚚 物流满意度归因分析

**业务问题**：物流时效如何影响客户满意度？哪些因素最敏感？

**分析内容**：
- 评分分布（1-5分）
- 按时 vs 延迟交付评分对比（箱线图）
- 交付天数 vs 评分散点图 + 回归线
- 各州满意度对比（气泡图）
- 交付天数分段满意度分析
- 相关性热力图（评分 vs 各因素）
- 关键业务洞察与建议

**关键发现**：
- 交付时效与满意度的相关系数
- 最优交付窗口建议
- 区域物流改善优先级

### 📈 销售趋势分析

**业务问题**：销售趋势如何？客户结构是否健康？

**分析内容**：
- 月度收入 & 订单量趋势（双Y轴）
- 季节性分析（周几 + 月份）
- 地理销售分布（各州）
- 品类收入占比趋势（堆积面积图）
- 订单状态漏斗
- RFM 客户分层（饼图 + 消费对比）

**关键发现**：
- 月环比增长率
- 季节性高峰时段
- 高价值客户占比

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| **语言** | Python 3.8+ |
| **看板框架** | Streamlit |
| **数据处理** | Pandas, NumPy |
| **可视化** | Plotly, Matplotlib, Seaborn |
| **统计分析** | SciPy, Scikit-learn |
| **数据获取** | Kagglehub |


## 📝 数据集说明

**Olist Brazilian E-commerce Dataset**

- 数据时间：2016年9月 - 2018年8月
- 约10万条订单记录
- 包含9张数据表：orders, order_items, products, sellers, customers, order_reviews, order_payments, geolocation, category_translation

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**Made with ❤️ by Allen | 数据科学与大数据技术专业**
