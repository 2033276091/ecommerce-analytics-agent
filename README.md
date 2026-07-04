# 电商智能问数 Agent

## 项目背景

这是一个面向电商经营分析的智能问数 Agent，能理解业务问题、生成 SQL、查询数据、做指标解释、发现异常，并能展示它如何降低运营/数据分析成本。

## 项目结构

- 项目总览：见 `README.md`
- 智能体上线文：见 `AGENT.md \ CALUDE.md`
- 数据模型设计：见 `docs/data_model.md`
- SQLite 表结构：见 `sql/schema.sql`
- 模拟数据生成：见 `scripts/generate_mock_data.py`
- 模拟数据验证：见 `scripts/validate_data.py`
- 知识库：见 `schema.py 表schema定义 metrics.py 指标口径定义 recall.py 召回schema`

## 智能问数流程

1. 意图识别：判断是指标查询、归因分析、异常检测、报表生成。
2. Schema 召回：根据问题找到相关表、字段、指标口径。
3. SQL 生成：基于指标定义和表结构生成 SQL。
4. SQL 校验：检查字段、语法、危险操作。
5. 查询执行：在 数据库 中跑 SQL。
6. 结果解释：把查询结果转成业务语言。
7. 可视化：输出表格、趋势图、TOP 排名图。
8. 追问推荐：给出下一步分析建议。

## 数据范围

第一版模拟 90 天电商经营数据，包含 6 张表：

- `dim_users`：用户维表
- `dim_products`：商品维表
- `fact_orders`：订单事实表
- `fact_order_items`：订单明细事实表
- `fact_traffic_daily`：流量日汇总表
- `fact_refunds`：退款事实表

这些表可以支撑以下常见问题：

- GMV、订单数、客单价
- 品类、品牌、商品销售排行
- 渠道转化率、加购率
- 地区经营表现
- 退款金额、退款率、退款原因
- 复购率和用户分层分析

## 使用方式

生成模拟数据：

```powershell
python scripts\generate_mock_data.py
```

验证数据可查询：

```powershell
python scripts\validate_data.py
```

生成结果：

- `ecommerce_demo.sqlite`：本地演示数据库
- `data/*.csv`：每张表对应的 CSV 数据

问题：
1.近30天的gmv是多少？
2.帮我生成一张报表，这个报表包含用户所在省份、性别、年龄段三个维度，实付金额、退款金额两个度量值，时间范围是近30天
