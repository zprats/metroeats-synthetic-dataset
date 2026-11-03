import os
import sqlite3
import tempfile
from pathlib import Path

from metroeats.csvio import read_rows
from metroeats.schema import CUSTOMERS, DELIVERY_EVENTS, ORDER_ITEMS, ORDERS, PAYMENTS, RESTAURANTS


TABLE_DDL = {
    RESTAURANTS.filename: """
        CREATE TABLE restaurants (
            restaurant_id TEXT PRIMARY KEY,
            restaurant_name TEXT NOT NULL,
            city TEXT NOT NULL,
            zone TEXT NOT NULL,
            primary_cuisine TEXT NOT NULL,
            secondary_cuisine TEXT NOT NULL,
            price_band INTEGER NOT NULL,
            avg_item_price_inr REAL NOT NULL,
            avg_prep_minutes INTEGER NOT NULL,
            service_rating REAL NOT NULL,
            rating_count INTEGER NOT NULL,
            onboarded_at TEXT NOT NULL,
            is_chain INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        )
    """,
    CUSTOMERS.filename: """
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            signup_date TEXT NOT NULL,
            city TEXT NOT NULL,
            home_zone TEXT NOT NULL,
            acquisition_channel TEXT NOT NULL,
            loyalty_tier TEXT NOT NULL,
            age_band TEXT NOT NULL,
            preferred_cuisine TEXT NOT NULL,
            marketing_opt_in INTEGER NOT NULL,
            device_type TEXT NOT NULL
        )
    """,
    ORDERS.filename: """
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL REFERENCES customers(customer_id),
            restaurant_id TEXT NOT NULL REFERENCES restaurants(restaurant_id),
            city TEXT NOT NULL,
            placed_at TEXT NOT NULL,
            order_status TEXT NOT NULL,
            fulfillment_mode TEXT NOT NULL,
            subtotal_inr REAL NOT NULL,
            discount_inr REAL NOT NULL,
            delivery_fee_inr REAL NOT NULL,
            tax_inr REAL NOT NULL,
            tip_inr REAL NOT NULL,
            total_inr REAL NOT NULL,
            promo_code TEXT NOT NULL,
            distance_km REAL NOT NULL,
            weather TEXT NOT NULL,
            traffic TEXT NOT NULL,
            promised_minutes INTEGER NOT NULL,
            actual_delivery_minutes INTEGER,
            cancellation_reason TEXT,
            rating INTEGER
        )
    """,
    ORDER_ITEMS.filename: """
        CREATE TABLE order_items (
            order_item_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL REFERENCES orders(order_id),
            item_position INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            item_category TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price_inr REAL NOT NULL,
            line_total_inr REAL NOT NULL,
            is_vegetarian INTEGER NOT NULL,
            customization TEXT NOT NULL
        )
    """,
    PAYMENTS.filename: """
        CREATE TABLE payments (
            payment_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id),
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            amount_inr REAL NOT NULL,
            gateway_fee_inr REAL NOT NULL,
            initiated_at TEXT NOT NULL,
            settled_at TEXT,
            failure_reason TEXT,
            refund_amount_inr REAL NOT NULL
        )
    """,
    DELIVERY_EVENTS.filename: """
        CREATE TABLE delivery_events (
            event_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL REFERENCES orders(order_id),
            courier_id TEXT,
            event_type TEXT NOT NULL,
            event_at TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            distance_remaining_km REAL NOT NULL,
            event_source TEXT NOT NULL
        )
    """,
}

INTEGER_COLUMNS = {
    RESTAURANTS.filename: {"price_band", "avg_prep_minutes", "rating_count", "is_chain"},
    CUSTOMERS.filename: {"marketing_opt_in"},
    ORDERS.filename: {"promised_minutes", "actual_delivery_minutes", "rating"},
    ORDER_ITEMS.filename: {"item_position", "quantity", "is_vegetarian"},
    PAYMENTS.filename: set(),
    DELIVERY_EVENTS.filename: set(),
}

REAL_COLUMNS = {
    RESTAURANTS.filename: {"avg_item_price_inr", "service_rating", "latitude", "longitude"},
    CUSTOMERS.filename: set(),
    ORDERS.filename: {
        "subtotal_inr",
        "discount_inr",
        "delivery_fee_inr",
        "tax_inr",
        "tip_inr",
        "total_inr",
        "distance_km",
    },
    ORDER_ITEMS.filename: {"unit_price_inr", "line_total_inr"},
    PAYMENTS.filename: {"amount_inr", "gateway_fee_inr", "refund_amount_inr"},
    DELIVERY_EVENTS.filename: {"latitude", "longitude", "distance_remaining_km"},
}

BOOLEAN_COLUMNS = {
    RESTAURANTS.filename: {"is_chain"},
    CUSTOMERS.filename: {"marketing_opt_in"},
    ORDER_ITEMS.filename: {"is_vegetarian"},
}

TABLE_ORDER = (RESTAURANTS, CUSTOMERS, ORDERS, ORDER_ITEMS, PAYMENTS, DELIVERY_EVENTS)

INDEX_DDL = (
    "CREATE INDEX idx_orders_customer ON orders(customer_id)",
    "CREATE INDEX idx_orders_restaurant ON orders(restaurant_id)",
    "CREATE INDEX idx_orders_placed_at ON orders(placed_at)",
    "CREATE INDEX idx_orders_city_status ON orders(city, order_status)",
    "CREATE INDEX idx_items_order ON order_items(order_id)",
    "CREATE INDEX idx_payments_order ON payments(order_id)",
    "CREATE INDEX idx_events_order_time ON delivery_events(order_id, event_at)",
)


def build_database(data_directory="data", database_path="var/metroeats.sqlite"):
    source = Path(data_directory)
    target = Path(database_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    Path(temporary_name).unlink()
    try:
        connection = sqlite3.connect(temporary_name)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = OFF")
        connection.execute("PRAGMA synchronous = OFF")
        for table in TABLE_ORDER:
            connection.execute(TABLE_DDL[table.filename])
            placeholders = ", ".join("?" for _ in table.columns)
            statement = f"INSERT INTO {table.filename.removesuffix('.csv')} VALUES ({placeholders})"
            batch = []
            for row in read_rows(source / table.filename, table):
                batch.append(tuple(_convert(table.filename, column, row[column]) for column in table.columns))
                if len(batch) == 5_000:
                    connection.executemany(statement, batch)
                    batch.clear()
            if batch:
                connection.executemany(statement, batch)
            connection.commit()
        for statement in INDEX_DDL:
            connection.execute(statement)
        connection.execute("ANALYZE")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        connection.commit()
        connection.close()
        Path(temporary_name).replace(target)
    except BaseException:
        try:
            connection.close()
        except UnboundLocalError:
            pass
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return target


def _convert(filename, column, value):
    if value == "":
        return None
    if column in BOOLEAN_COLUMNS.get(filename, set()):
        return 1 if value == "true" else 0
    if column in INTEGER_COLUMNS[filename]:
        return int(value)
    if column in REAL_COLUMNS[filename]:
        return float(value)
    return value
