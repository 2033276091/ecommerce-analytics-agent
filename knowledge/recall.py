"""Schema 召回模块。

给定自然语言问题，从知识库中召回相关的表、字段、指标和时间范围。
LLM 驱动的语义匹配，处理同义词和口语化表达。
"""

from dataclasses import dataclass, field

from knowledge.schema import ALL_TABLES, format_for_prompt as format_schema
from knowledge.metrics import ALL_METRICS, format_for_prompt as format_metrics


@dataclass
class SchemaContext:
    """Schema 召回结果——精简后的查询上下文。"""

    question: str  # 原始问题
    tables: list[str] = field(default_factory=list)  # 相关表名
    fields: list[str] = field(default_factory=list)  # 相关字段（格式: "table.field"）
    metrics: list[str] = field(default_factory=list)  # 匹配到的指标名
    metric_sql: str = ""  # 选中指标的基础 SQL 模板
    time_range: dict = field(default_factory=dict)  # 解析后的时间范围
    filters: list[str] = field(default_factory=list)  # 额外过滤条件
    sql_hints: list[str] = field(default_factory=list)  # 生成 SQL 的额外提示

    def summarize(self) -> str:
        """人类可读的召回摘要。"""
        lines = [f"问题：{self.question}", ""]
        if self.metrics:
            lines.append(f"指标：{', '.join(self.metrics)}")
        if self.tables:
            lines.append(f"表：{', '.join(self.tables)}")
        if self.fields:
            lines.append(f"字段：{', '.join(self.fields)}")
        if self.time_range:
            lines.append(f"时间范围：{self.time_range}")
        if self.filters:
            lines.append(f"过滤条件：{', '.join(self.filters)}")
        if self.sql_hints:
            lines.append(f"提示：{'; '.join(self.sql_hints)}")
        if self.metric_sql:
            lines.append(f"\nSQL 模板：\n{self.metric_sql}")
        return "\n".join(lines)


def build_recall_prompt(question: str) -> str:
    """构建 Schema 召回 prompt。

    将全量 Schema + 指标口径 + 用户问题打包为 LLM prompt。
    """
    return f"""你是一个电商数据分析助手。根据用户的自然语言问题，识别需要查询的数据。

# 数据库 Schema

{format_schema()}

{format_metrics()}

# 用户问题

{question}

# 任务

请分析用户问题，输出一个 JSON 对象，包含以下字段：

- "tables": 需要查询的表名列表（只从上述 Schema 中选）
- "fields": 需要的字段列表，格式为 ["table.field"]（只从上述 Schema 中选）
- "metrics": 匹配到的指标名称列表（从指标口径定义中选）
- "time_range": 时间范围对象，如 {{"type": "last_n_days", "n": 30}} 或 {{"type": "date_range", "start": "2026-06-01", "end": "2026-06-30"}} 或 {{"type": "none"}}
- "filters": 额外的 WHERE 条件列表（如 ["order_status = 'paid'"]，注意指标口径文档中已隐含的过滤条件不需要重复）
- "sql_hints": 生成 SQL 时的额外提示列表

注意：
1. 仔细阅读指标口径文档——GMV/订单数等指标的口径中已隐含了 "order_status = 'paid'" 等过滤条件
2. "近一个月"、"最近7天" 等表述对应的 time_range type 为 "last_n_days"
3. 如果问题涉及时间比较（环比、同比），请标注
4. 只输出 JSON，不要输出其他内容

请严格输出以下格式的 JSON："""


def resolve_time_filter(time_range: dict) -> str:
    """将时间范围 dict 转换为 SQL WHERE 条件中的日期过滤表达式。"""
    if not time_range or time_range.get("type") == "none":
        return "1=1"

    typ = time_range.get("type", "")
    if typ == "last_n_days":
        n = time_range.get("n", 30)
        return f"date(order_date) >= date('now', '-{n} days')"

    if typ == "last_n_weeks":
        n = time_range.get("n", 1)
        return f"date(order_date) >= date('now', '-{n * 7} days')"

    if typ == "date_range":
        start = time_range.get("start", "")
        end = time_range.get("end", "")
        return f"date(order_date) BETWEEN '{start}' AND '{end}'"

    if typ == "yesterday":
        return "date(order_date) = date('now', '-1 days')"

    if typ == "today":
        return "date(order_date) = date('now')"

    return "1=1"


def resolve_time_filter_for_table(time_range: dict, date_field: str) -> str:
    """为特定表的日期字段生成过滤表达式。

    不同表用不同的日期字段（order_date / refund_date / stat_date 等）。
    """
    if not time_range or time_range.get("type") == "none":
        return "1=1"

    typ = time_range.get("type", "")
    if typ == "last_n_days":
        n = time_range.get("n", 30)
        return f"date({date_field}) >= date('now', '-{n} days')"

    if typ == "last_n_weeks":
        n = time_range.get("n", 1)
        return f"date({date_field}) >= date('now', '-{n * 7} days')"

    if typ == "date_range":
        start = time_range.get("start", "")
        end = time_range.get("end", "")
        return f"date({date_field}) BETWEEN '{start}' AND '{end}'"

    if typ == "yesterday":
        return f"date({date_field}) = date('now', '-1 days')"

    if typ == "today":
        return f"date({date_field}) = date('now')"

    return "1=1"
