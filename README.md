# 电商智能问数 Agent

面向电商经营分析的智能问数 Agent —— 用户用自然语言提问，系统理解问题、匹配数据表和指标口径、生成安全 SQL、查询本地 SQLite 数据库，并用业务语言解释结果。

## 架构概览

```text
用户自然语言问题
       │
       ▼
┌─────────────────┐
│  1. 意图识别     │  指标查询 / 报表生成 / 归因分析 / 异常查询
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. Schema 召回  │  knowledge/schema.py  → 匹配表 + 字段
│                 │  knowledge/metrics.py → 匹配指标口径
│                 │  knowledge/recall.py  → 生成召回 prompt
└────────┬────────┘
         ▼
┌─────────────────┐
│  3. SQL 生成    │  LLM 基于召回结果 + 指标定义生成只读 SQL
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. SQL 校验    │  scripts/ask.py → 禁止 DROP/DELETE/UPDATE 等危险操作
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. 查询执行    │  本地 SQLite（ecommerce_demo.sqlite）
└────────┬────────┘
         ▼
┌─────────────────┐
│  6. 结果解释    │  业务语言解读查询结果
└────────┬────────┘
         ▼
┌─────────────────┐
│  7. 追问推荐    │  给出下一步分析建议
└────────┬────────┘
         ▼
┌─────────────────┐
│  8. 输出归档    │  output/ 目录下生成 markdown 报告
└─────────────────┘
```

## 项目结构

```text
ai_data/
├── CLAUDE.md                       # Claude Code 智能体上下文（问数 SOP + 输出规范）
├── AGENT.md                        # 项目整体设计文档（MVP 范围、执行计划）
├── README.md                       # 本文件
│
├── docs/
│   └── data_model.md               # 数据模型文档（表结构、表关系、指标口径）
│
├── sql/
│   └── schema.sql                  # SQLite 建表 DDL（6 张表完整定义 + 注释）
│
├── knowledge/                      # 知识库模块（Python）
│   ├── __init__.py                 # 包导出
│   ├── schema.py                   # 表与字段的结构化定义（dataclass，6 张表完整 schema）
│   ├── metrics.py                  # 12 个核心指标口径定义（含公式、SQL 模板、别名、依赖表）
│   └── recall.py                   # Schema 召回模块（构建 LLM prompt、时间范围解析）
│
├── scripts/                        # 命令行工具
│   ├── ask.py                      # 智能问数 CLI（子命令：recall / query / metrics / tables）
│   ├── generate_mock_data.py       # 生成 90 天模拟电商数据 → SQLite + CSV
│   └── validate_data.py            # 数据验证脚本（执行典型查询确认数据可用）
│
├── data/                           # 生成的 CSV 数据（执行 generate_mock_data.py 后产生）
│   ├── dim_users.csv
│   ├── dim_products.csv
│   ├── fact_orders.csv
│   ├── fact_order_items.csv
│   ├── fact_traffic_daily.csv
│   └── fact_refunds.csv
│
├── ecommerce_demo.sqlite           # 本地演示数据库（执行 generate_mock_data.py 后产生）
│
└── output/                         # 智能问数输出报告归档
    └── 001-报表生成-省份性别年龄段实付退款报表.md
```

## 快速开始

### 环境要求

- Python 3.10+
- SQLite3（Python 内置，无需额外安装）
- 无第三方依赖（仅使用 Python 标准库）

### 1. 生成模拟数据

```bash
python scripts/generate_mock_data.py
```

执行后生成：
- `ecommerce_demo.sqlite` — 包含全部 6 张表的 SQLite 数据库
- `data/*.csv` — 每张表对应的 CSV 文件

数据集规模（90 天）：

| 表 | 数据量 |
|---|---|
| dim_users | ~800 条 |
| dim_products | ~75 条（5 品类 × 3 子品类 × 5 品牌） |
| fact_orders | ~5,000+ 条 |
| fact_order_items | ~6,000+ 条 |
| fact_traffic_daily | ~2,250 条（90 天 × 5 渠道 × 5 品类） |
| fact_refunds | ~400+ 条 |

### 2. 验证数据

```bash
python scripts/validate_data.py
```

执行 4 条典型查询确认数据可正常使用：支付订单与 GMV、品类 GMV TOP5、渠道转化率、退款金额。

### 3. 使用 CLI 工具

```bash
# 列出所有表及字段
python scripts/ask.py tables

# 列出所有可用指标
python scripts/ask.py metrics

# 按关键词搜索指标
python scripts/ask.py metrics gmv
python scripts/ask.py metrics 退款

# 构建 Schema 召回 prompt（供 LLM 使用）
python scripts/ask.py recall "近30天GMV是多少？"

# 直接执行 SQL（带安全校验）
python scripts/ask.py query "SELECT ROUND(SUM(paid_amount), 2) AS gmv FROM fact_orders WHERE order_status = 'paid' AND date(order_date) >= date('now', '-30 days')"
```

## 数据模型

6 张表覆盖电商经营分析的 5 个核心数据域：

| 表名 | 中文名 | 粒度 | 数据域 |
|---|---|---|---|
| `dim_users` | 用户维表 | 一个用户 | 用户域 |
| `dim_products` | 商品维表 | 一个商品 | 商品域 |
| `fact_orders` | 订单事实表 | 一笔订单 | 交易域 |
| `fact_order_items` | 订单明细事实表 | 订单中的一个商品 | 交易域 |
| `fact_traffic_daily` | 流量日汇总表 | 日期 + 渠道 + 品类 | 流量域 |
| `fact_refunds` | 退款事实表 | 一笔退款申请 | 售后域 |

### 表关系

```text
dim_users.user_id       ──→ fact_orders.user_id
fact_orders.order_id    ──→ fact_order_items.order_id
dim_products.product_id ──→ fact_order_items.product_id
fact_orders.order_id    ──→ fact_refunds.order_id
dim_products.category   ──→ fact_traffic_daily.category
```

详细字段说明见 `docs/data_model.md` 和 `sql/schema.sql`。

## 核心指标口径

知识库定义了 12 个核心指标，每个指标包含名称、别名、计算公式、SQL 模板和依赖关系：

| 指标 | 英文名 | 口径 |
|---|---|---|
| GMV | `gmv` | `SUM(paid_amount)`，仅 `order_status = 'paid'` |
| 支付订单数 | `paid_order_count` | `COUNT(DISTINCT order_id)`，仅已支付 |
| 支付用户数 | `paid_user_count` | `COUNT(DISTINCT user_id)`，仅已支付 |
| 销售件数 | `sales_quantity` | `SUM(quantity)`，关联已支付订单 |
| 客单价 | `arpu` | GMV / 支付订单数 |
| 件单价 | `avg_item_price` | GMV / 销售件数 |
| 转化率 | `conversion_rate` | 支付用户数 / 访客数 |
| 加购率 | `add_to_cart_rate` | 加购用户数 / 访客数 |
| 退款金额 | `refund_amount` | `SUM(refund_amount)`，仅 `refund_status = 'approved'` |
| 金额退款率 | `refund_rate_by_amount` | 退款金额 / GMV |
| 订单退款率 | `refund_rate_by_orders` | 退款订单数 / 支付订单数 |
| 复购率 | `repurchase_rate` | 购买 ≥2 次用户数 / 支付用户数 |

每个指标还包含丰富的同义别名（如 GMV 别名包括"销售额"、"成交额"、"流水"等），确保口语化问题能精准匹配到正确口径。

## 智能问数 SOP

当用户通过 Claude Code 提问时，Agent 按以下流程执行：

1. **意图识别** — 判断问题类型：指标查询、报表生成、归因分析、异常查询
2. **Schema 召回** — 调用 `knowledge/recall.py` 匹配相关表、字段、指标口径；未匹配到的需说明，禁止硬算
3. **SQL 生成** — 基于召回的指标定义和表结构生成只读 SQL
4. **SQL 校验** — 调用 `scripts/ask.py query` 进行安全校验（禁止 DROP/DELETE/UPDATE 等危险操作）
5. **查询执行** — 在本地 SQLite 数据库执行 SQL
6. **结果返回** — 根据意图类型返回对应的业务解读
7. **追问推荐** — 给出下一步分析方向建议
8. **输出归档** — 完整分析过程保存为 `output/` 目录下的 markdown 文件

### 输出文件命名规范

```text
output/{序号}-{意图类型}-{问题概要}.md
```

示例：`output/001-报表生成-省份性别年龄段实付退款报表.md`

## 典型问题示例

```text
指标查询：近 30 天 GMV 是多少？
报表生成：帮我生成近 7 天各品类 GMV 排名报表
归因分析：本周 GMV 下降主要是流量、转化率还是客单价导致？
异常查询：近 7 天退款率是否高于近 30 天平均？
```

## 回答准确率保障

```text
准确率 = 高质量知识库 × 精准的召回策略 × 完善的提示词工程 × 多层校验机制 × 持续反馈迭代

  ① 结构化 Schema：dataclass 定义表/字段，LLM 直接理解数据模型
  ② 指标口径库：12 个核心指标含公式 + SQL 模板 + 别名，规避口径歧义
  ③ Schema 召回：LLM 驱动的语义匹配，处理同义词和口语化表达
  ④ SQL 安全校验：关键词黑名单 + 表名白名单 + 只允许 SELECT
  ⑤ 输出规范：8 步 SOP + 模板化输出，确保每次回答完整可追溯
```

## 相关文档

| 文档 | 用途 |
|---|---|
| `CLAUDE.md` | Claude Code 智能体系统指令（SOP + 输出规范） |
| `AGENT.md` | 项目整体设计文档（背景、MVP 范围、实施计划） |
| `docs/data_model.md` | 数据模型详细说明（表结构、字段、表关系、指标口径） |
| `sql/schema.sql` | SQLite 建表 DDL（含注释） |
