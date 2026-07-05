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
    unmatched_metrics: list[str] = field(default_factory=list)  # 用户提到但知识库未定义的指标
    unmatched_terms: list[str] = field(default_factory=list)  # 其他无法识别的术语/概念

    def has_unmatched(self) -> bool:
        """是否有知识库无法覆盖的指标或术语。"""
        return bool(self.unmatched_metrics or self.unmatched_terms)

    def summarize(self) -> str:
        """人类可读的召回摘要。"""
        lines = [f"问题：{self.question}", ""]

        # 未匹配项 —— 放在最前面，最醒目
        if self.has_unmatched():
            lines.append("⚠️ ═══════════════════════════════════════════")
            lines.append("⚠️ 警告：以下内容在知识库中未找到对应定义！")
            if self.unmatched_metrics:
                for um in self.unmatched_metrics:
                    lines.append(f"  ❌ 未定义指标：「{um}」")
            if self.unmatched_terms:
                for ut in self.unmatched_terms:
                    lines.append(f"  ❓ 未识别术语：「{ut}」")
            lines.append("⚠️ 请向用户确认上述指标/术语的口径后再继续！")
            lines.append("⚠️ ═══════════════════════════════════════════")
            lines.append("")

        if self.metrics:
            lines.append(f"✅ 已匹配指标：{', '.join(self.metrics)}")
        if self.tables:
            lines.append(f"✅ 已匹配表：{', '.join(self.tables)}")
        if self.fields:
            lines.append(f"✅ 已匹配字段：{', '.join(self.fields)}")
        if self.time_range:
            lines.append(f"✅ 时间范围：{self.time_range}")
        if self.filters:
            lines.append(f"✅ 过滤条件：{', '.join(self.filters)}")
        if self.sql_hints:
            lines.append(f"✅ 提示：{'; '.join(self.sql_hints)}")
        if self.metric_sql:
            lines.append(f"\nSQL 模板：\n{self.metric_sql}")
        return "\n".join(lines)


def build_recall_prompt(question: str) -> str:
    """构建 Schema 召回 prompt。

    将全量 Schema + 指标口径 + 用户问题打包为 LLM prompt。
    """
    return f"""你是一个严格、保守的电商数据分析助手。你的核心原则是：**口径不明不硬算**。

# 数据库 Schema

{format_schema()}

{format_metrics()}

# 用户问题

{question}

# 任务

请分析用户问题，输出一个 JSON 对象，包含以下字段：

- "tables": 需要查询的表名列表（只从上述 Schema 中选，找不到就留空数组）
- "fields": 需要的字段列表，格式为 ["table.field"]（只从上述 Schema 中选）
- "metrics": 匹配到的指标名称列表（只从上述指标口径定义中选，找不到就留空数组）
- "time_range": 时间范围对象，如 {{"type": "last_n_days", "n": 30}} 或 {{"type": "none"}}
- "filters": 额外的 WHERE 条件列表（指标口径中已隐含的过滤条件不需要重复）
- "sql_hints": 生成 SQL 时的额外提示列表
- "unmatched_metrics": 【重要】用户问题中提到的、但在上述指标口径定义中 **找不到** 的指标/业务概念列表。例如用户问"下单GMV"但知识库只有"GMV"（成交GMV），则"下单GMV"应列入此数组
- "unmatched_terms": 【重要】用户问题中无法识别的其他术语/概念列表

## 严格遵守的规则

1. **只使用已定义的内容**：上述 Schema 中列出了所有可用表，指标口径定义中列出了所有可用指标。你只能使用这些已定义的内容。
2. **诚实标记未知项**：用户问题中提到的任何指标，如果在指标口径定义中找不到精确或高度近似的匹配，**必须**将其放入 "unmatched_metrics" 数组。
3. **禁止自行推断**：绝对不要根据自己的训练数据或常识来定义指标口径。例如：
   - 知识库只有 "GMV"（定义为 SUM(paid_amount) WHERE order_status='paid'，即成交口径）
   - 用户问"下单GMV"——这不是同一个概念，"下单GMV"应放入 unmatched_metrics
   - 不要自行决定用 gross_amount、不过滤状态等口径
4. **宁可多报不少报**：如果不确定某个术语是否匹配，就放入 unmatched 数组中，让用户确认。
5. **"近一个月"、"最近7天"** 等表述对应的 time_range type 为 "last_n_days"

请严格输出以下格式的 JSON，不要输出其他内容："""


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
