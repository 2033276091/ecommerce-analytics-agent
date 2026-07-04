# 电商模拟数据与表结构设计

## 背景

第一版只保留电商问数最常用的 6 张表：`dim_users`、`dim_products`、`fact_orders`、`fact_order_items`、`fact_traffic_daily`、`fact_refunds`。这套模型足够支撑 GMV、订单、客单价、转化率、退款率、复购、品类排行、区域渠道分析等高频问题。

## 业务场景

这个数据集模拟一个多品类电商平台的日常经营分析。业务人员关心：

- 今天或昨天销售额怎么样。
- 哪些品类、品牌、商品卖得好。
- 不同地区、渠道的转化效果如何。
- 退款是否异常，集中在哪些品类和原因。
- 用户是否复购，会员等级是否影响消费。
- GMV 变化到底来自流量、转化率还是客单价。

## 表关系

```text
dim_users.user_id          -> fact_orders.user_id
fact_orders.order_id       -> fact_order_items.order_id
dim_products.product_id    -> fact_order_items.product_id
fact_orders.order_id       -> fact_refunds.order_id
dim_products.category      -> fact_traffic_daily.category
```

## 表结构

### dim_users

用户维表，用于分析地区、会员等级、注册时间对交易表现的影响。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| user_id | TEXT | 用户 ID |
| register_date | DATE | 注册日期 |
| province | TEXT | 省份 |
| city_tier | TEXT | 城市等级 |
| gender | TEXT | 性别 |
| age_group | TEXT | 年龄段 |
| member_level | TEXT | 会员等级 |

### dim_products

商品维表，用于分析品类、品牌、价格带、毛利空间。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| product_id | TEXT | 商品 ID |
| product_name | TEXT | 商品名称 |
| category | TEXT | 一级品类 |
| sub_category | TEXT | 二级品类 |
| brand | TEXT | 品牌 |
| cost_price | REAL | 成本价 |
| list_price | REAL | 标价 |
| launch_date | DATE | 上架日期 |

### fact_orders

订单事实表，粒度为一笔订单。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| order_id | TEXT | 订单 ID |
| user_id | TEXT | 用户 ID |
| order_date | DATE | 下单日期 |
| pay_time | DATETIME | 支付时间 |
| province | TEXT | 收货省份 |
| channel | TEXT | 下单来源渠道 |
| order_status | TEXT | 订单状态：paid/cancelled |
| gross_amount | REAL | 订单商品原始金额 |
| discount_amount | REAL | 优惠金额 |
| paid_amount | REAL | 实付金额 |

### fact_order_items

订单明细事实表，粒度为订单中的一个商品。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| item_id | TEXT | 明细 ID |
| order_id | TEXT | 订单 ID |
| product_id | TEXT | 商品 ID |
| quantity | INTEGER | 购买件数 |
| unit_price | REAL | 商品成交单价 |
| item_amount | REAL | 明细成交金额 |

### fact_traffic_daily

流量日汇总表，粒度为日期 + 渠道 + 品类。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stat_date | DATE | 统计日期 |
| channel | TEXT | 流量渠道 |
| category | TEXT | 品类 |
| page_views | INTEGER | 浏览量 |
| visitors | INTEGER | 访客数 |
| add_to_cart_users | INTEGER | 加购用户数 |
| order_users | INTEGER | 下单用户数 |
| pay_users | INTEGER | 支付用户数 |

### fact_refunds

退款事实表，粒度为一笔退款申请。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| refund_id | TEXT | 退款 ID |
| order_id | TEXT | 订单 ID |
| user_id | TEXT | 用户 ID |
| refund_date | DATE | 退款日期 |
| refund_amount | REAL | 退款金额 |
| refund_reason | TEXT | 退款原因 |
| refund_status | TEXT | 退款状态：approved/rejected |

## 核心指标口径

| 指标 | 口径 |
| --- | --- |
| GMV | `sum(fact_orders.paid_amount)`，仅统计 `order_status = 'paid'` |
| 支付订单数 | `count(distinct order_id)`，仅统计已支付订单 |
| 支付用户数 | `count(distinct user_id)`，仅统计已支付订单 |
| 销售件数 | `sum(quantity)`，关联已支付订单明细 |
| 客单价 | `GMV / 支付订单数` |
| 件单价 | `GMV / 销售件数` |
| 转化率 | `支付用户数 / 访客数`，通常按日期、渠道、品类聚合 |
| 加购率 | `加购用户数 / 访客数` |
| 退款金额 | `sum(refund_amount)`，仅统计 `refund_status = 'approved'` |
| 金额退款率 | `退款金额 / GMV` |
| 订单退款率 | `退款订单数 / 支付订单数` |
| 复购率 | 周期内购买 2 次及以上用户数 / 周期内支付用户数 |

## 第一批示例问题

- 昨天 GMV、支付订单数、客单价分别是多少？
- 最近 7 天 GMV 趋势如何？
- 最近 7 天 GMV 最高的品类 TOP5 是哪些？
- 各渠道最近 7 天转化率分别是多少？
- 华东地区女装类目的退款率是否偏高？
- 最近 30 天复购率是多少？
- 本周 GMV 较上周下降时，是流量下降、转化率下降还是客单价下降？

