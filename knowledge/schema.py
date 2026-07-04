"""表与字段的结构化定义。

从 docs/data_model.md 和 sql/schema.sql 提取，供 Schema 召回和 SQL 生成使用。
"""

from dataclasses import dataclass, field


@dataclass
class Field:
    """数据库字段定义。"""

    name: str
    type: str  # SQL 类型
    description: str  # 中文业务含义
    is_dimension: bool = False  # 维度字段（分组/筛选用）
    is_measure: bool = False  # 度量字段（聚合用）


@dataclass
class Table:
    """数据库表定义。"""

    name: str
    label: str  # 中文名称
    description: str  # 业务说明
    fields: list[Field] = field(default_factory=list)

    def get_field(self, name: str) -> Field | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


# ── 6 张表的完整定义 ──────────────────────────────────────────

ALL_TABLES: list[Table] = [
    Table(
        name="dim_users",
        label="用户维表",
        description="存储用户基本信息，用于分析地区、会员等级、年龄对消费行为的影响",
        fields=[
            Field("user_id", "TEXT", "用户ID", is_dimension=True),
            Field("register_date", "DATE", "注册日期", is_dimension=True),
            Field("province", "TEXT", "省份", is_dimension=True),
            Field("city_tier", "TEXT", "城市等级（一线/新一线/二线/三线）", is_dimension=True),
            Field("gender", "TEXT", "性别（男/女/未知）", is_dimension=True),
            Field("age_group", "TEXT", "年龄段（18-24/25-34/35-44/45+）", is_dimension=True),
            Field("member_level", "TEXT", "会员等级（普通/白银/黄金/铂金）", is_dimension=True),
        ],
    ),
    Table(
        name="dim_products",
        label="商品维表",
        description="存储商品信息，用于分析品类、品牌、价格带对销售的影响，以及计算毛利",
        fields=[
            Field("product_id", "TEXT", "商品ID", is_dimension=True),
            Field("product_name", "TEXT", "商品名称", is_dimension=True),
            Field("category", "TEXT", "一级品类（女装/美妆/食品/数码/家清）", is_dimension=True),
            Field("sub_category", "TEXT", "二级品类", is_dimension=True),
            Field("brand", "TEXT", "品牌（Aster/Bison/Clover/Dawn/Echo）", is_dimension=True),
            Field("cost_price", "REAL", "成本价", is_measure=True),
            Field("list_price", "REAL", "标价（原价）", is_measure=True),
            Field("launch_date", "DATE", "上架日期", is_dimension=True),
        ],
    ),
    Table(
        name="fact_orders",
        label="订单事实表",
        description="每行一笔订单。存储订单级交易数据，用于计算 GMV、订单数、客单价，支持渠道和地区分析",
        fields=[
            Field("order_id", "TEXT", "订单ID", is_dimension=True),
            Field("user_id", "TEXT", "用户ID，关联 dim_users", is_dimension=True),
            Field("order_date", "DATE", "下单日期", is_dimension=True),
            Field("pay_time", "DATETIME", "支付时间，未支付则为空", is_dimension=True),
            Field("province", "TEXT", "收货省份", is_dimension=True),
            Field("channel", "TEXT", "下单渠道（自然流量/搜索/推荐/直播/广告）", is_dimension=True),
            Field("order_status", "TEXT", "订单状态：paid 已支付 / cancelled 已取消", is_dimension=True),
            Field("gross_amount", "REAL", "商品原始金额（优惠前）", is_measure=True),
            Field("discount_amount", "REAL", "优惠金额", is_measure=True),
            Field("paid_amount", "REAL", "实付金额", is_measure=True),
        ],
    ),
    Table(
        name="fact_order_items",
        label="订单明细事实表",
        description="每行一笔订单中的一个商品。存储订单-商品粒度数据，用于计算销量、件单价、品类/品牌销售排行",
        fields=[
            Field("item_id", "TEXT", "明细ID", is_dimension=True),
            Field("order_id", "TEXT", "订单ID，关联 fact_orders", is_dimension=True),
            Field("product_id", "TEXT", "商品ID，关联 dim_products", is_dimension=True),
            Field("quantity", "INTEGER", "购买件数", is_measure=True),
            Field("unit_price", "REAL", "商品成交单价", is_measure=True),
            Field("item_amount", "REAL", "明细成交金额（quantity × unit_price）", is_measure=True),
        ],
    ),
    Table(
        name="fact_traffic_daily",
        label="流量日汇总表",
        description="每行是某天+某渠道+某品类的流量聚合数据。用于计算转化率、加购率，分析渠道和品类表现",
        fields=[
            Field("stat_date", "DATE", "统计日期", is_dimension=True),
            Field("channel", "TEXT", "流量渠道（同订单渠道）", is_dimension=True),
            Field("category", "TEXT", "品类，关联 dim_products.category", is_dimension=True),
            Field("page_views", "INTEGER", "浏览量", is_measure=True),
            Field("visitors", "INTEGER", "访客数", is_measure=True),
            Field("add_to_cart_users", "INTEGER", "加购用户数", is_measure=True),
            Field("order_users", "INTEGER", "下单用户数", is_measure=True),
            Field("pay_users", "INTEGER", "支付用户数", is_measure=True),
        ],
    ),
    Table(
        name="fact_refunds",
        label="退款事实表",
        description="每行一笔退款申请。用于计算退款金额、退款率，分析退款原因和品类分布",
        fields=[
            Field("refund_id", "TEXT", "退款ID", is_dimension=True),
            Field("order_id", "TEXT", "订单ID，关联 fact_orders", is_dimension=True),
            Field("user_id", "TEXT", "用户ID，关联 dim_users", is_dimension=True),
            Field("refund_date", "DATE", "退款日期", is_dimension=True),
            Field("refund_amount", "REAL", "退款金额", is_measure=True),
            Field("refund_reason", "TEXT", "退款原因（不喜欢/尺码不合适/质量问题/发货慢/价格变动）", is_dimension=True),
            Field("refund_status", "TEXT", "退款状态：approved 已通过 / rejected 已拒绝", is_dimension=True),
        ],
    ),
]


def get_table(name: str) -> Table | None:
    """按表名获取 Table 对象。"""
    for t in ALL_TABLES:
        if t.name == name:
            return t
    return None


def format_for_prompt() -> str:
    """将全量 Schema 格式化为 LLM prompt 可用的文本。"""
    lines = []
    for t in ALL_TABLES:
        lines.append(f"## {t.name}（{t.label}）")
        lines.append(f"{t.description}")
        lines.append("| 字段 | 类型 | 说明 | 用途 |")
        lines.append("|------|------|------|------|")
        for f in t.fields:
            role = ""
            if f.is_dimension and f.is_measure:
                role = "维度/度量"
            elif f.is_dimension:
                role = "维度（分组/筛选）"
            elif f.is_measure:
                role = "度量（聚合）"
            lines.append(f"| {f.name} | {f.type} | {f.description} | {role} |")
        lines.append("")
    return "\n".join(lines)
