-- ============================================================================
-- 电商经营分析 · 智能问数 Agent · 数据模型
-- ============================================================================
-- 表关系（外键）:
--   dim_users.user_id          -> fact_orders.user_id
--   fact_orders.order_id       -> fact_order_items.order_id
--   dim_products.product_id    -> fact_order_items.product_id
--   fact_orders.order_id       -> fact_refunds.order_id
--   dim_products.category      -> fact_traffic_daily.category
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 用户维表 (dim_users)
-- 用途: 按地区、会员等级、注册时间等维度分析用户对交易表现的贡献
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_users (
    user_id       TEXT PRIMARY KEY,  -- 用户 ID（主键）
    register_date DATE NOT NULL,     -- 注册日期
    province      TEXT NOT NULL,     -- 所在省份
    city_tier     TEXT NOT NULL,     -- 城市等级（如：一线/新一线/二线/三线/四线）
    gender        TEXT NOT NULL,     -- 性别
    age_group     TEXT NOT NULL,     -- 年龄段（如：18-24/25-34/35-44/45+）
    member_level  TEXT NOT NULL      -- 会员等级（如：普通/银卡/金卡/钻石）
);

-- ----------------------------------------------------------------------------
-- 2. 商品维表 (dim_products)
-- 用途: 按品类、品牌、价格带、毛利空间分析商品销售表现
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_products (
    product_id   TEXT PRIMARY KEY,   -- 商品 ID（主键）
    product_name TEXT NOT NULL,      -- 商品名称
    category     TEXT NOT NULL,      -- 一级品类（如：女装/男装/数码/美妆/家居）
    sub_category TEXT NOT NULL,      -- 二级品类（如：连衣裙/牛仔裤/T恤）
    brand        TEXT NOT NULL,      -- 品牌
    cost_price   REAL NOT NULL,      -- 成本价（单件进货/生产成本）
    list_price   REAL NOT NULL,      -- 标价/吊牌价（展示给用户的原价）
    launch_date  DATE NOT NULL       -- 上架日期
);

-- ----------------------------------------------------------------------------
-- 3. 订单事实表 (fact_orders)
-- 用途: 记录每笔订单的金额、状态、渠道等核心交易信息
--       粒度 = 一笔订单
--       关键口径: GMV = sum(paid_amount) WHERE order_status = 'paid'
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id       TEXT PRIMARY KEY,    -- 订单 ID（主键）
    user_id        TEXT NOT NULL,       -- 下单用户 ID → dim_users.user_id
    order_date     DATE NOT NULL,       -- 下单日期
    pay_time       DATETIME,            -- 支付时间（未支付则为 NULL）
    province       TEXT NOT NULL,       -- 收货省份
    channel        TEXT NOT NULL,       -- 下单来源渠道（自然流量/搜索/推荐/直播/广告）
    order_status   TEXT NOT NULL,       -- 订单状态: paid（已支付）/ cancelled（已取消）
    gross_amount   REAL NOT NULL,       -- 商品原始金额（优惠前）
    discount_amount REAL NOT NULL,      -- 优惠总金额（满减+优惠券+其他折扣）
    paid_amount    REAL NOT NULL,       -- 实付金额（gross_amount - discount_amount）
    FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
);

-- ----------------------------------------------------------------------------
-- 4. 订单明细事实表 (fact_order_items)
-- 用途: 记录每笔订单中每个商品的购买数量、单价、金额
--       粒度 = 订单中的一件商品（一个订单可能有多条明细）
--       关键口径: 销售件数 = sum(quantity)，需关联已支付订单
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_order_items (
    item_id    TEXT PRIMARY KEY,        -- 明细 ID（主键，每条记录唯一）
    order_id   TEXT NOT NULL,           -- 所属订单 ID → fact_orders.order_id
    product_id TEXT NOT NULL,           -- 商品 ID → dim_products.product_id
    quantity   INTEGER NOT NULL,        -- 该商品购买件数
    unit_price REAL NOT NULL,           -- 商品成交单价（已折算优惠后的实际单价）
    item_amount REAL NOT NULL,          -- 明细成交金额（unit_price × quantity）
    FOREIGN KEY (order_id)   REFERENCES fact_orders(order_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
);

-- ----------------------------------------------------------------------------
-- 5. 流量日汇总表 (fact_traffic_daily)
-- 用途: 统计每天各渠道各品类的流量漏斗指标（浏览→访客→加购→下单→支付）
--       粒度 = 日期 + 渠道 + 品类
--       关键口径: 转化率 = 支付用户数 / 访客数
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_traffic_daily (
    stat_date         DATE NOT NULL,    -- 统计日期
    channel           TEXT NOT NULL,    -- 流量渠道（自然流量/搜索/推荐/直播/广告）
    category          TEXT NOT NULL,    -- 品类（与 dim_products.category 对应）
    page_views        INTEGER NOT NULL, -- 页面浏览量（PV）
    visitors          INTEGER NOT NULL, -- 独立访客数（UV）
    add_to_cart_users INTEGER NOT NULL, -- 加购用户数（将商品加入购物车的访客数）
    order_users       INTEGER NOT NULL, -- 下单用户数（提交订单的访客数）
    pay_users         INTEGER NOT NULL, -- 支付用户数（完成支付的访客数）
    PRIMARY KEY (stat_date, channel, category)
);

-- ----------------------------------------------------------------------------
-- 6. 退款事实表 (fact_refunds)
-- 用途: 记录每笔退款申请，用于分析退款率、退款原因分布等
--       粒度 = 一笔退款申请
--       关键口径: 退款率相关指标仅统计 refund_status = 'approved'
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_refunds (
    refund_id     TEXT PRIMARY KEY,     -- 退款 ID（主键）
    order_id      TEXT NOT NULL,        -- 关联原订单 ID → fact_orders.order_id
    user_id       TEXT NOT NULL,        -- 退款用户 ID → dim_users.user_id
    refund_date   DATE NOT NULL,        -- 退款申请日期
    refund_amount REAL NOT NULL,        -- 退款金额
    refund_reason TEXT NOT NULL,        -- 退款原因（质量问题/尺寸不合适/不想要了/物流慢/其他）
    refund_status TEXT NOT NULL,        -- 退款状态: approved（已通过）/ rejected（已拒绝）
    FOREIGN KEY (order_id) REFERENCES fact_orders(order_id),
    FOREIGN KEY (user_id)  REFERENCES dim_users(user_id)
);
