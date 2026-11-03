from dataclasses import dataclass


@dataclass(frozen=True)
class TableSpec:
    filename: str
    columns: tuple[str, ...]
    primary_key: str


RESTAURANTS = TableSpec(
    "restaurants.csv",
    (
        "restaurant_id",
        "restaurant_name",
        "city",
        "zone",
        "primary_cuisine",
        "secondary_cuisine",
        "price_band",
        "avg_item_price_inr",
        "avg_prep_minutes",
        "service_rating",
        "rating_count",
        "onboarded_at",
        "is_chain",
        "latitude",
        "longitude",
    ),
    "restaurant_id",
)

CUSTOMERS = TableSpec(
    "customers.csv",
    (
        "customer_id",
        "signup_date",
        "city",
        "home_zone",
        "acquisition_channel",
        "loyalty_tier",
        "age_band",
        "preferred_cuisine",
        "marketing_opt_in",
        "device_type",
    ),
    "customer_id",
)

ORDERS = TableSpec(
    "orders.csv",
    (
        "order_id",
        "customer_id",
        "restaurant_id",
        "city",
        "placed_at",
        "order_status",
        "fulfillment_mode",
        "subtotal_inr",
        "discount_inr",
        "delivery_fee_inr",
        "tax_inr",
        "tip_inr",
        "total_inr",
        "promo_code",
        "distance_km",
        "weather",
        "traffic",
        "promised_minutes",
        "actual_delivery_minutes",
        "cancellation_reason",
        "rating",
    ),
    "order_id",
)

ORDER_ITEMS = TableSpec(
    "order_items.csv",
    (
        "order_item_id",
        "order_id",
        "item_position",
        "item_name",
        "item_category",
        "cuisine",
        "quantity",
        "unit_price_inr",
        "line_total_inr",
        "is_vegetarian",
        "customization",
    ),
    "order_item_id",
)

PAYMENTS = TableSpec(
    "payments.csv",
    (
        "payment_id",
        "order_id",
        "payment_method",
        "payment_status",
        "amount_inr",
        "gateway_fee_inr",
        "initiated_at",
        "settled_at",
        "failure_reason",
        "refund_amount_inr",
    ),
    "payment_id",
)

DELIVERY_EVENTS = TableSpec(
    "delivery_events.csv",
    (
        "event_id",
        "order_id",
        "courier_id",
        "event_type",
        "event_at",
        "latitude",
        "longitude",
        "distance_remaining_km",
        "event_source",
    ),
    "event_id",
)

TABLES = (RESTAURANTS, CUSTOMERS, ORDERS, ORDER_ITEMS, PAYMENTS, DELIVERY_EVENTS)
TABLE_BY_FILENAME = {table.filename: table for table in TABLES}
