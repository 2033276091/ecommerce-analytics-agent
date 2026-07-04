"""电商智能问数 Agent — 知识库模块。

提供 Schema（表/字段）与 Metric（指标口径）的结构化定义，以及 Schema 召回能力。
"""

from knowledge.schema import Table, Field, ALL_TABLES, get_table
from knowledge.metrics import Metric, ALL_METRICS, get_metric
from knowledge.recall import SchemaContext, build_recall_prompt, resolve_time_filter, resolve_time_filter_for_table

__all__ = [
    "Table",
    "Field",
    "ALL_TABLES",
    "get_table",
    "Metric",
    "ALL_METRICS",
    "get_metric",
    "SchemaContext",
    "build_recall_prompt",
    "resolve_time_filter",
    "resolve_time_filter_for_table",
]
