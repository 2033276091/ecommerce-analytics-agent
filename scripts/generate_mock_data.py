import csv
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "ecommerce_demo.sqlite"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

random.seed(42)

PROVINCES = ["上海", "江苏", "浙江", "广东", "北京", "四川", "湖北", "山东"]
CITY_TIERS = ["一线", "新一线", "二线", "三线"]
GENDERS = ["男", "女", "未知"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45+"]
MEMBER_LEVELS = ["普通", "白银", "黄金", "铂金"]
CHANNELS = ["自然流量", "搜索", "推荐", "直播", "广告"]
REFUND_REASONS = ["不喜欢", "尺码不合适", "质量问题", "发货慢", "价格变动"]
CATEGORY_CONFIG = {
    "女装": ["连衣裙", "衬衫", "外套"],
    "美妆": ["护肤", "彩妆", "香水"],
    "食品": ["零食", "饮料", "粮油"],
    "数码": ["手机配件", "耳机", "智能设备"],
    "家清": ["纸品", "清洁剂", "洗衣用品"],
}


def write_csv(name, rows):
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{name}.csv"
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generate_users(n=800):
    rows = []
    start = date.today() - timedelta(days=365)
    for i in range(1, n + 1):
        rows.append(
            {
                "user_id": f"U{i:05d}",
                "register_date": start + timedelta(days=random.randint(0, 330)),
                "province": random.choice(PROVINCES),
                "city_tier": random.choice(CITY_TIERS),
                "gender": random.choices(GENDERS, weights=[45, 50, 5])[0],
                "age_group": random.choices(AGE_GROUPS, weights=[22, 45, 24, 9])[0],
                "member_level": random.choices(MEMBER_LEVELS, weights=[55, 25, 15, 5])[0],
            }
        )
    return rows


def generate_products():
    rows = []
    idx = 1
    brands = ["Aster", "Bison", "Clover", "Dawn", "Echo"]
    for category, subs in CATEGORY_CONFIG.items():
        for sub in subs:
            for brand in brands:
                base_price = random.randint(39, 699)
                rows.append(
                    {
                        "product_id": f"P{idx:04d}",
                        "product_name": f"{brand}{sub}{idx}",
                        "category": category,
                        "sub_category": sub,
                        "brand": brand,
                        "cost_price": round(base_price * random.uniform(0.35, 0.65), 2),
                        "list_price": round(base_price, 2),
                        "launch_date": date.today() - timedelta(days=random.randint(30, 420)),
                    }
                )
                idx += 1
    return rows


def generate_orders(users, products, days=90):
    orders = []
    items = []
    refunds = []
    order_seq = 1
    item_seq = 1
    refund_seq = 1
    start = date.today() - timedelta(days=days - 1)

    for offset in range(days):
        order_date = start + timedelta(days=offset)
        weekday_boost = 1.2 if order_date.weekday() in (4, 5, 6) else 1.0
        daily_orders = int(random.randint(35, 85) * weekday_boost)
        for _ in range(daily_orders):
            user = random.choice(users)
            channel = random.choices(CHANNELS, weights=[28, 25, 22, 15, 10])[0]
            status = random.choices(["paid", "cancelled"], weights=[92, 8])[0]
            order_id = f"O{order_seq:06d}"
            line_count = random.choices([1, 2, 3], weights=[70, 23, 7])[0]
            selected_products = random.sample(products, line_count)
            gross_amount = 0.0

            for product in selected_products:
                quantity = random.choices([1, 2, 3], weights=[78, 17, 5])[0]
                unit_price = round(float(product["list_price"]) * random.uniform(0.82, 1.0), 2)
                item_amount = round(quantity * unit_price, 2)
                gross_amount += item_amount
                items.append(
                    {
                        "item_id": f"I{item_seq:07d}",
                        "order_id": order_id,
                        "product_id": product["product_id"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "item_amount": item_amount,
                    }
                )
                item_seq += 1

            discount_amount = round(gross_amount * random.uniform(0.02, 0.18), 2)
            paid_amount = round(gross_amount - discount_amount, 2) if status == "paid" else 0.0
            pay_time = datetime.combine(order_date, datetime.min.time()) + timedelta(
                hours=random.randint(8, 23), minutes=random.randint(0, 59)
            )
            orders.append(
                {
                    "order_id": order_id,
                    "user_id": user["user_id"],
                    "order_date": order_date,
                    "pay_time": pay_time if status == "paid" else None,
                    "province": user["province"],
                    "channel": channel,
                    "order_status": status,
                    "gross_amount": round(gross_amount, 2),
                    "discount_amount": discount_amount,
                    "paid_amount": paid_amount,
                }
            )

            if status == "paid" and random.random() < 0.085:
                refund_amount = round(paid_amount * random.uniform(0.35, 1.0), 2)
                refund_date = order_date + timedelta(days=random.randint(1, 15))
                refunds.append(
                    {
                        "refund_id": f"R{refund_seq:06d}",
                        "order_id": order_id,
                        "user_id": user["user_id"],
                        "refund_date": refund_date,
                        "refund_amount": refund_amount,
                        "refund_reason": random.choice(REFUND_REASONS),
                        "refund_status": random.choices(["approved", "rejected"], weights=[82, 18])[0],
                    }
                )
                refund_seq += 1

            order_seq += 1

    return orders, items, refunds


def generate_traffic(days=90):
    rows = []
    start = date.today() - timedelta(days=days - 1)
    for offset in range(days):
        stat_date = start + timedelta(days=offset)
        for channel in CHANNELS:
            channel_factor = {"自然流量": 1.25, "搜索": 1.1, "推荐": 1.0, "直播": 0.75, "广告": 0.65}[channel]
            for category in CATEGORY_CONFIG:
                category_factor = {"女装": 1.25, "美妆": 1.1, "食品": 1.0, "数码": 0.82, "家清": 0.78}[category]
                visitors = int(random.randint(500, 2400) * channel_factor * category_factor)
                page_views = int(visitors * random.uniform(2.2, 4.8))
                add_to_cart_users = int(visitors * random.uniform(0.08, 0.22))
                order_users = int(add_to_cart_users * random.uniform(0.30, 0.62))
                pay_users = int(order_users * random.uniform(0.70, 0.93))
                rows.append(
                    {
                        "stat_date": stat_date,
                        "channel": channel,
                        "category": category,
                        "page_views": page_views,
                        "visitors": visitors,
                        "add_to_cart_users": add_to_cart_users,
                        "order_users": order_users,
                        "pay_users": pay_users,
                    }
                )
    return rows


def insert_rows(conn, table, rows):
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn.executemany(sql, [[str(row[col]) if row[col] is not None else None for col in columns] for row in rows])


def build_sqlite(users, products, orders, items, traffic, refunds):
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    insert_rows(conn, "dim_users", users)
    insert_rows(conn, "dim_products", products)
    insert_rows(conn, "fact_orders", orders)
    insert_rows(conn, "fact_order_items", items)
    insert_rows(conn, "fact_traffic_daily", traffic)
    insert_rows(conn, "fact_refunds", refunds)
    conn.commit()
    conn.close()


def main():
    users = generate_users()
    products = generate_products()
    orders, items, refunds = generate_orders(users, products)
    traffic = generate_traffic()

    for name, rows in {
        "dim_users": users,
        "dim_products": products,
        "fact_orders": orders,
        "fact_order_items": items,
        "fact_traffic_daily": traffic,
        "fact_refunds": refunds,
    }.items():
        write_csv(name, rows)

    build_sqlite(users, products, orders, items, traffic, refunds)
    print(f"generated sqlite database: {DB_PATH}")
    print(f"users={len(users)}, products={len(products)}, orders={len(orders)}, items={len(items)}")
    print(f"traffic_rows={len(traffic)}, refunds={len(refunds)}")


if __name__ == "__main__":
    main()

