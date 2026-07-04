"""核心指标口径定义。

每个指标包含名称、中文标签、别名、计算公式、SQL 表达式、依赖表字段。
SQL 表达式中的占位符：
  - {time_filter} 会被替换为时间过滤条件
"""

from dataclasses import dataclass, field


@dataclass
class Metric:
    """业务指标定义。"""

    name: str  # 英文标识符
    label: str  # 中文名称
    aliases: list[str] = field(default_factory=list)  # 同义词/别称
    formula: str = ""  # 人类可读的计算公式
    sql_expr: str = ""  # SQL 表达式（可包含 {time_filter} 占位符）
    depends_on: list[str] = field(default_factory=list)  # 依赖的表名
    depends_on_fields: list[str] = field(default_factory=list)  # 依赖的关键字段
    time_sensitive: bool = True  # 是否需要时间过滤
    note: str = ""  # 口径注意事项


# ── 12 个核心指标 ─────────────────────────────────────────────

ALL_METRICS: list[Metric] = [
    Metric(
        name="gmv",
        label="GMV",
        aliases=["销售额", "成交额", "总销售额", "交易额", "流水", "卖了多少", "收入"],
        formula="SUM(fact_orders.paid_amount)，仅统计 order_status = 'paid'",
        sql_expr="SELECT ROUND(SUM(paid_amount), 2) AS gmv FROM fact_orders WHERE order_status = 'paid' AND {time_filter}",
        depends_on=["fact_orders"],
        depends_on_fields=["paid_amount", "order_status", "order_date"],
        note="GMV 严格只算已支付订单的实付金额，不含取消订单。",
    ),
    Metric(
        name="paid_order_count",
        label="支付订单数",
        aliases=["订单数", "订单量", "成交订单数", "成交笔数"],
        formula="COUNT(DISTINCT fact_orders.order_id)，仅统计 order_status = 'paid'",
        sql_expr="SELECT COUNT(DISTINCT order_id) AS paid_order_count FROM fact_orders WHERE order_status = 'paid' AND {time_filter}",
        depends_on=["fact_orders"],
        depends_on_fields=["order_id", "order_status", "order_date"],
    ),
    Metric(
        name="paid_user_count",
        label="支付用户数",
        aliases=["购买人数", "付费用户数", "下单用户数"],
        formula="COUNT(DISTINCT fact_orders.user_id)，仅统计已支付订单",
        sql_expr="SELECT COUNT(DISTINCT user_id) AS paid_user_count FROM fact_orders WHERE order_status = 'paid' AND {time_filter}",
        depends_on=["fact_orders"],
        depends_on_fields=["user_id", "order_status", "order_date"],
    ),
    Metric(
        name="sales_quantity",
        label="销售件数",
        aliases=["销量", "卖出件数", "商品件数"],
        formula="SUM(fact_order_items.quantity)，关联已支付订单",
        sql_expr="SELECT SUM(i.quantity) AS sales_quantity FROM fact_order_items i JOIN fact_orders o ON i.order_id = o.order_id WHERE o.order_status = 'paid' AND {time_filter}",
        depends_on=["fact_orders", "fact_order_items"],
        depends_on_fields=["quantity", "order_status", "order_date"],
    ),
    Metric(
        name="arpu",
        label="客单价",
        aliases=["笔单价", "平均订单金额"],
        formula="GMV / 支付订单数",
        sql_expr="SELECT ROUND(SUM(paid_amount) * 1.0 / COUNT(DISTINCT order_id), 2) AS arpu FROM fact_orders WHERE order_status = 'paid' AND {time_filter}",
        depends_on=["fact_orders"],
        depends_on_fields=["paid_amount", "order_id", "order_status", "order_date"],
        note="客单价是复合指标，SQL 中在一次查询内计算。",
    ),
    Metric(
        name="avg_item_price",
        label="件单价",
        aliases=["单品均价", "平均单价"],
        formula="GMV / 销售件数",
        sql_expr=(
            "SELECT ROUND(SUM(o.paid_amount) * 1.0 / NULLIF(SUM(i.quantity), 0), 2) AS avg_item_price "
            "FROM fact_orders o JOIN fact_order_items i ON o.order_id = i.order_id "
            "WHERE o.order_status = 'paid' AND {time_filter}"
        ),
        depends_on=["fact_orders", "fact_order_items"],
        depends_on_fields=["paid_amount", "quantity", "order_date"],
    ),
    Metric(
        name="conversion_rate",
        label="转化率",
        aliases=["支付转化率", "成交率"],
        formula="支付用户数 / 访客数，通常按日期、渠道或品类聚合",
        sql_expr=(
            "SELECT channel, ROUND(SUM(pay_users) * 1.0 / NULLIF(SUM(visitors), 0), 4) AS conversion_rate "
            "FROM fact_traffic_daily WHERE {time_filter} GROUP BY channel"
        ),
        depends_on=["fact_traffic_daily"],
        depends_on_fields=["pay_users", "visitors", "stat_date", "channel", "category"],
    ),
    Metric(
        name="add_to_cart_rate",
        label="加购率",
        aliases=["加购转化率"],
        formula="加购用户数 / 访客数",
        sql_expr=(
            "SELECT ROUND(SUM(add_to_cart_users) * 1.0 / NULLIF(SUM(visitors), 0), 4) AS add_to_cart_rate "
            "FROM fact_traffic_daily WHERE {time_filter}"
        ),
        depends_on=["fact_traffic_daily"],
        depends_on_fields=["add_to_cart_users", "visitors", "stat_date"],
    ),
    Metric(
        name="refund_amount",
        label="退款金额",
        aliases=["退款总额", "售后退款"],
        formula="SUM(fact_refunds.refund_amount)，仅统计 refund_status = 'approved'",
        sql_expr="SELECT ROUND(SUM(refund_amount), 2) AS refund_amount FROM fact_refunds WHERE refund_status = 'approved' AND {time_filter}",
        depends_on=["fact_refunds"],
        depends_on_fields=["refund_amount", "refund_status", "refund_date"],
    ),
    Metric(
        name="refund_rate_by_amount",
        label="金额退款率",
        aliases=["退款率（金额）", "退款金额占比"],
        formula="退款金额 / GMV",
        sql_expr=(
            "SELECT ROUND("
            "  (SELECT SUM(refund_amount) FROM fact_refunds WHERE refund_status = 'approved' AND {time_filter}) * 1.0 / "
            "  NULLIF((SELECT SUM(paid_amount) FROM fact_orders WHERE order_status = 'paid' AND {time_filter}), 0) * 100, 2"
            ") AS refund_rate_pct"
        ),
        depends_on=["fact_orders", "fact_refunds"],
        depends_on_fields=["refund_amount", "refund_date", "paid_amount", "order_date"],
        note="金额退款率是复合指标，需要在同一时间窗口内计算退款金额 / GMV。",
    ),
    Metric(
        name="refund_rate_by_orders",
        label="订单退款率",
        aliases=["退款率（订单数）"],
        formula="退款订单数 / 支付订单数",
        sql_expr=(
            "SELECT ROUND("
            "  (SELECT COUNT(DISTINCT order_id) FROM fact_refunds WHERE refund_status = 'approved' AND {time_filter}) * 1.0 / "
            "  NULLIF((SELECT COUNT(DISTINCT order_id) FROM fact_orders WHERE order_status = 'paid' AND {time_filter}), 0) * 100, 2"
            ") AS refund_order_rate_pct"
        ),
        depends_on=["fact_orders", "fact_refunds"],
        depends_on_fields=["order_id", "order_date", "refund_date"],
    ),
    Metric(
        name="repurchase_rate",
        label="复购率",
        aliases=["回购率", "回头客比例"],
        formula="周期内购买 ≥2 次的用户数 / 周期内支付用户数",
        sql_expr=(
            "SELECT ROUND("
            "  (SELECT COUNT(*) FROM ("
            "    SELECT user_id FROM fact_orders "
            "    WHERE order_status = 'paid' AND {time_filter} "
            "    GROUP BY user_id HAVING COUNT(DISTINCT order_id) >= 2"
            "  )) * 1.0 / "
            "  NULLIF((SELECT COUNT(DISTINCT user_id) FROM fact_orders WHERE order_status = 'paid' AND {time_filter}), 0) * 100, 2"
            ") AS repurchase_rate_pct"
        ),
        depends_on=["fact_orders"],
        depends_on_fields=["user_id", "order_id", "order_status", "order_date"],
    ),
]


def get_metric(name: str) -> Metric | None:
    """按名称或别名查找指标。"""
    for m in ALL_METRICS:
        if m.name == name:
            return m
        if name in m.aliases:
            return m
    return None


def search_metrics(keyword: str) -> list[Metric]:
    """模糊搜索指标，匹配名称、标签、别名。"""
    results = []
    kw = keyword.lower()
    for m in ALL_METRICS:
        if (
            kw in m.name.lower()
            or kw in m.label.lower()
            or any(kw in a.lower() for a in m.aliases)
        ):
            results.append(m)
    return results


def format_for_prompt() -> str:
    """将全量指标口径格式化为 LLM prompt 可用的文本。"""
    lines = ["# 指标口径定义", ""]
    for m in ALL_METRICS:
        aliases_str = "、".join(m.aliases) if m.aliases else "无"
        lines.append(f"## {m.label}（{m.name}）")
        lines.append(f"- 别名：{aliases_str}")
        lines.append(f"- 公式：{m.formula}")
        lines.append(f"- 依赖表：{', '.join(m.depends_on)}")
        lines.append(f"- 关键字段：{', '.join(m.depends_on_fields)}")
        if m.note:
            lines.append(f"- 注意：{m.note}")
        lines.append("")
    return "\n".join(lines)
