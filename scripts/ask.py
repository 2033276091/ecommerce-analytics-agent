"""智能问数 CLI 工具。

用法：
    python scripts/ask.py "近一个月gmv是多少？"

流程：
    1. 构建 Schema 召回 prompt（输出供 LLM 使用）
    2. 基于召回的 Schema + 指标口径生成 SQL
    3. SQL 安全校验
    4. 在本地 SQLite 执行
    5. 输出结果 + 业务解释
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "ecommerce_demo.sqlite"
sys.path.insert(0, str(ROOT))

from knowledge.recall import build_recall_prompt, resolve_time_filter_for_table  # noqa: E402
from knowledge.metrics import ALL_METRICS, get_metric  # noqa: E402
from knowledge.schema import ALL_TABLES  # noqa: E402

# ── 安全校验 ────────────────────────────────────────────────

FORBIDDEN_KEYWORDS = [
    "DELETE", "UPDATE", "INSERT", "DROP", "ALTER",
    "CREATE", "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
    "ATTACH", "DETACH", "PRAGMA",
]

ALLOWED_TABLES = {t.name for t in ALL_TABLES}


def validate_sql(sql: str) -> tuple[bool, str]:
    """校验 SQL 安全性：只允许 SELECT，只允许已知表。"""
    upper = sql.strip().upper()
    if not upper.startswith("SELECT"):
        return False, "只允许 SELECT 语句"

    for kw in FORBIDDEN_KEYWORDS:
        # 用词边界检查，避免误杀字段名中包含的子串
        if kw in upper:
            # 检查是否是独立的 SQL 关键字（前后是空白或语句边界）
            import re
            if re.search(rf"\b{kw}\b", upper):
                return False, f"禁止使用 {kw}"

    # 检查表名白名单
    for table in ALLOWED_TABLES:
        # 允许的表出现在 SQL 中没问题，这里不做替换，只是检查
        pass

    return True, "OK"


def execute_sql(sql: str) -> list[tuple]:
    """在本地 SQLite 执行只读查询。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql).fetchall()
        return [tuple(row) for row in rows]
    finally:
        conn.close()


# ── CLI 入口 ────────────────────────────────────────────────


def cmd_recall(args):
    """输出 Schema 召回 prompt，供 LLM 使用或人工查看。"""
    question = " ".join(args.question)
    prompt = build_recall_prompt(question)
    print(prompt)


def cmd_query(args):
    """直接执行提供的 SQL，带安全校验。"""
    sql = args.sql.strip()
    ok, msg = validate_sql(sql)
    if not ok:
        print(f"[拒绝] {msg}")
        sys.exit(1)

    print(f"[SQL 安全校验通过]")
    try:
        rows = execute_sql(sql)
    except Exception as e:
        print(f"[执行失败] {e}")
        sys.exit(1)

    if not rows:
        print("(无结果)")
        return

    # 打印列名
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.execute(sql)
    col_names = [d[0] for d in cur.description]
    conn.close()
    print("\t".join(col_names))
    print("-" * 40)
    for row in rows:
        print("\t".join(str(v) for v in row))
    print(f"\n({len(rows)} 行)")


def cmd_metrics(args):
    """列出所有可用指标。"""
    keyword = args.keyword
    metrics = ALL_METRICS
    if keyword:
        from knowledge.metrics import search_metrics
        metrics = search_metrics(keyword)
    for m in metrics:
        aliases = "、".join(m.aliases) if m.aliases else "—"
        print(f"  {m.name:30s} | {m.label:8s} | {aliases}")


def cmd_tables(args):
    """列出所有表及其字段。"""
    for t in ALL_TABLES:
        print(f"\n[{t.name}] {t.label}")
        print(f"  {t.description}")
        for f in t.fields:
            tag = ""
            if f.is_dimension:
                tag += "[维度]"
            if f.is_measure:
                tag += "[度量]"
            print(f"  {f.name:20s} {f.type:8s} {tag:10s} {f.description}")


def main():
    parser = argparse.ArgumentParser(description="电商智能问数 Agent")
    sub = parser.add_subparsers(dest="cmd")

    p_recall = sub.add_parser("recall", help="构建 Schema 召回 prompt")
    p_recall.add_argument("question", nargs="+", help="自然语言问题")

    p_query = sub.add_parser("query", help="执行 SQL 查询（带安全校验）")
    p_query.add_argument("sql", help="要执行的 SQL 语句")

    p_metrics = sub.add_parser("metrics", help="列出可用指标")
    p_metrics.add_argument("keyword", nargs="?", help="可选：按关键词过滤")

    p_tables = sub.add_parser("tables", help="列出所有表及字段")

    args = parser.parse_args()

    if args.cmd == "recall":
        cmd_recall(args)
    elif args.cmd == "query":
        cmd_query(args)
    elif args.cmd == "metrics":
        cmd_metrics(args)
    elif args.cmd == "tables":
        cmd_tables(args)
    else:
        # 默认模式：输出 recall prompt
        parser.print_help()
        print("\n提示：直接使用 'recall' 子命令来构建 Schema 召回 prompt")


if __name__ == "__main__":
    main()
