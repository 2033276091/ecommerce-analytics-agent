import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "ecommerce_demo.sqlite"


def main():
    conn = sqlite3.connect(DB_PATH)
    checks = {
        "paid_order_count_and_gmv": """
            select count(1), round(sum(paid_amount), 2)
            from fact_orders
            where order_status = 'paid'
        """,
        "category_gmv_top5": """
            select p.category, round(sum(i.item_amount), 2) as gmv
            from fact_order_items i
            join fact_orders o on i.order_id = o.order_id
            join dim_products p on i.product_id = p.product_id
            where o.order_status = 'paid'
            group by p.category
            order by gmv desc
            limit 5
        """,
        "channel_conversion_rate": """
            select channel, round(sum(pay_users) * 1.0 / sum(visitors), 4) as pay_rate
            from fact_traffic_daily
            group by channel
            order by pay_rate desc
        """,
        "approved_refund_amount": """
            select count(1), round(sum(refund_amount), 2)
            from fact_refunds
            where refund_status = 'approved'
        """,
    }

    for name, sql in checks.items():
        rows = conn.execute(sql).fetchall()
        print(f"\n{name}")
        for row in rows:
            print(row)

    conn.close()


if __name__ == "__main__":
    main()

