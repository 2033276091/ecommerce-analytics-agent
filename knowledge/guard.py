"""安全护栏：在 SQL 生成前检查召回结果是否完备。

防止智能体在遇到未定义指标时自行编造计算口径。
"""

from knowledge.recall import SchemaContext
from knowledge.metrics import suggest_metric


def check_recall_completeness(context: SchemaContext) -> tuple[bool, str]:
    """检查召回结果是否覆盖了用户问题的所有指标需求。

    这是 SQL 生成前的必经检查点。如果有任何指标或术语无法匹配，
    必须阻断流程，向用户确认口径后再继续。

    Args:
        context: Schema 召回结果

    Returns:
        (True, "OK") — 全部覆盖，可以继续生成 SQL
        (False, message) — 有未覆盖项，必须阻断并询问用户
    """
    if not context.has_unmatched():
        return True, "OK"

    lines = [
        "═══════════════════════════════════════════",
        "🛑 召回不完备 —— 禁止生成 SQL！",
        "═══════════════════════════════════════════",
        "",
        f"原始问题：{context.question}",
        "",
    ]

    if context.metrics:
        lines.append(f"✅ 已匹配的指标：{', '.join(context.metrics)}")
    else:
        lines.append("⚠️ 未匹配到任何已定义指标")

    lines.append("")

    if context.unmatched_metrics:
        lines.append("─── 以下指标在知识库中未定义 ───")
        for um in context.unmatched_metrics:
            lines.append(f"  ❌ 「{um}」—— 知识库中无此指标定义")
            # 给出最接近的候选建议
            suggestions = suggest_metric(um)
            if suggestions:
                lines.append(f"     💡 你可能想要的已定义指标：")
                for s in suggestions:
                    aliases_str = f"（别名：{'、'.join(s.aliases)}）" if s.aliases else ""
                    lines.append(f"        · {s.label}（{s.name}）{aliases_str}")
                    lines.append(f"          口径：{s.formula}")
            lines.append("")

    if context.unmatched_terms:
        lines.append("─── 以下术语无法识别 ───")
        for ut in context.unmatched_terms:
            lines.append(f"  ❓ 「{ut}」")
        lines.append("")

    lines.append("─── 你必须执行的操作 ───")
    lines.append("1. 将上述信息如实告知用户")
    lines.append("2. 请用户对每个未定义指标给出明确的口径定义")
    lines.append("3. 在用户确认口径之前，**禁止**生成任何 SQL")
    lines.append("4. 如果用户确认了某个未定义指标的口径，将其记录到报告中")
    lines.append("═══════════════════════════════════════════")

    return False, "\n".join(lines)


def format_guard_for_prompt() -> str:
    """将护栏使用说明格式化为 LLM prompt 可用的文本。"""
    return """# 召回完备性护栏

在 Schema 召回完成后、SQL 生成之前，**必须**调用以下检查：

```python
from knowledge.guard import check_recall_completeness
ok, msg = check_recall_completeness(schema_context)
```

如果 `ok == False`：
- **立即停止**，不要继续生成 SQL
- 将 `msg` 的内容原样展示给用户
- 等待用户对未定义指标给出明确口径后再继续

如果 `ok == True`：
- 所有指标均已匹配，可以安全地进入 SQL 生成阶段"""
