import csv
import os
import sqlite3
import tempfile
from pathlib import Path

from metroeats.csvio import write_json


REPORT_QUERIES = {
    "monthly_performance.csv": """
        SELECT
            substr(placed_at, 1, 7) AS month,
            COUNT(*) AS orders,
            SUM(order_status = 'delivered') AS delivered_orders,
            ROUND(100.0 * SUM(order_status = 'delivered') / COUNT(*), 2) AS delivery_rate_pct,
            ROUND(SUM(CASE WHEN order_status = 'delivered' THEN total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN total_inr END), 2) AS average_order_value_inr,
            ROUND(AVG(discount_inr), 2) AS average_discount_inr,
            ROUND(100.0 * SUM(order_status = 'delivered' AND actual_delivery_minutes <= promised_minutes)
                / NULLIF(SUM(order_status = 'delivered'), 0), 2) AS on_time_rate_pct
        FROM orders
        GROUP BY substr(placed_at, 1, 7)
        ORDER BY month
    """,
    "city_performance.csv": """
        SELECT
            city,
            COUNT(*) AS orders,
            SUM(order_status = 'delivered') AS delivered_orders,
            ROUND(100.0 * (COUNT(*) - SUM(order_status = 'delivered')) / COUNT(*), 2) AS non_delivery_rate_pct,
            ROUND(SUM(CASE WHEN order_status = 'delivered' THEN total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN total_inr END), 2) AS average_order_value_inr,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN actual_delivery_minutes END), 2) AS average_delivery_minutes,
            ROUND(100.0 * SUM(order_status = 'delivered' AND actual_delivery_minutes <= promised_minutes)
                / NULLIF(SUM(order_status = 'delivered'), 0), 2) AS on_time_rate_pct
        FROM orders
        GROUP BY city
        ORDER BY delivered_gmv_inr DESC
    """,
    "cuisine_performance.csv": """
        SELECT
            r.primary_cuisine AS cuisine,
            COUNT(*) AS orders,
            SUM(o.order_status = 'delivered') AS delivered_orders,
            ROUND(100.0 * (COUNT(*) - SUM(o.order_status = 'delivered')) / COUNT(*), 2) AS non_delivery_rate_pct,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
            ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.total_inr END), 2) AS average_order_value_inr,
            ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.rating END), 2) AS average_rating
        FROM orders o
        JOIN restaurants r ON r.restaurant_id = o.restaurant_id
        GROUP BY r.primary_cuisine
        ORDER BY delivered_gmv_inr DESC
    """,
    "delivery_sla.csv": """
        SELECT
            weather,
            traffic,
            COUNT(*) AS orders,
            SUM(order_status = 'delivered') AS delivered_orders,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN actual_delivery_minutes END), 2) AS average_delivery_minutes,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN actual_delivery_minutes - promised_minutes END), 2) AS average_variance_minutes,
            ROUND(100.0 * SUM(order_status = 'delivered' AND actual_delivery_minutes <= promised_minutes)
                / NULLIF(SUM(order_status = 'delivered'), 0), 2) AS on_time_rate_pct,
            ROUND(100.0 * (COUNT(*) - SUM(order_status = 'delivered')) / COUNT(*), 2) AS non_delivery_rate_pct
        FROM orders
        WHERE fulfillment_mode = 'delivery'
        GROUP BY weather, traffic
        ORDER BY weather, traffic
    """,
    "customer_segments.csv": """
        SELECT
            c.loyalty_tier,
            c.acquisition_channel,
            COUNT(DISTINCT c.customer_id) AS ordering_customers,
            COUNT(o.order_id) AS orders,
            ROUND(1.0 * COUNT(o.order_id) / COUNT(DISTINCT c.customer_id), 2) AS orders_per_customer,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
            ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.total_inr END), 2) AS average_order_value_inr
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        GROUP BY c.loyalty_tier, c.acquisition_channel
        ORDER BY c.loyalty_tier, delivered_gmv_inr DESC
    """,
    "top_items.csv": """
        SELECT
            i.cuisine,
            i.item_name,
            SUM(i.quantity) AS units,
            COUNT(DISTINCT i.order_id) AS orders,
            ROUND(SUM(i.line_total_inr), 2) AS gross_item_value_inr,
            ROUND(AVG(i.unit_price_inr), 2) AS average_unit_price_inr
        FROM order_items i
        JOIN orders o ON o.order_id = i.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY i.cuisine, i.item_name
        ORDER BY gross_item_value_inr DESC
    """,
    "cancellation_reasons.csv": """
        SELECT
            cancellation_reason,
            weather,
            traffic,
            COUNT(*) AS orders,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_of_non_delivered_pct
        FROM orders
        WHERE order_status <> 'delivered'
        GROUP BY cancellation_reason, weather, traffic
        ORDER BY orders DESC
    """,
}


def run_analysis(database_path="var/metroeats.sqlite", output_directory="reports"):
    database = Path(database_path)
    if not database.is_file():
        raise FileNotFoundError(f"database does not exist: {database}")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    summary = _executive_summary(connection)
    write_json(output / "executive_summary.json", summary)
    report_rows = {}
    for filename, query in REPORT_QUERIES.items():
        cursor = connection.execute(query)
        rows = cursor.fetchall()
        headers = tuple(column[0] for column in cursor.description)
        _write_csv(output / filename, headers, rows)
        report_rows[filename] = len(rows)
    connection.close()
    manifest = {
        "source_database": str(database),
        "reports": {
            "executive_summary.json": 1,
            **dict(sorted(report_rows.items())),
        },
    }
    write_json(output / "report_manifest.json", manifest)
    return summary, report_rows


def _executive_summary(connection):
    order_metrics = connection.execute(
        """
        SELECT
            COUNT(*) AS orders,
            SUM(order_status = 'delivered') AS delivered_orders,
            COUNT(DISTINCT customer_id) AS ordering_customers,
            COUNT(DISTINCT restaurant_id) AS active_restaurants,
            ROUND(SUM(CASE WHEN order_status = 'delivered' THEN total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN total_inr END), 2) AS average_order_value_inr,
            ROUND(AVG(CASE WHEN order_status = 'delivered' THEN actual_delivery_minutes END), 2) AS average_delivery_minutes,
            ROUND(100.0 * SUM(order_status = 'delivered') / COUNT(*), 2) AS delivery_rate_pct,
            ROUND(100.0 * SUM(order_status = 'delivered' AND actual_delivery_minutes <= promised_minutes)
                / NULLIF(SUM(order_status = 'delivered'), 0), 2) AS on_time_rate_pct,
            ROUND(SUM(CASE WHEN order_status = 'delivered' THEN discount_inr ELSE 0 END), 2) AS delivered_discount_inr
        FROM orders
        """
    ).fetchone()
    payment_metrics = connection.execute(
        """
        SELECT
            ROUND(SUM(refund_amount_inr), 2) AS refunds_inr,
            ROUND(SUM(gateway_fee_inr), 2) AS gateway_fees_inr,
            ROUND(100.0 * SUM(payment_status = 'failed') / COUNT(*), 2) AS payment_failure_rate_pct
        FROM payments
        """
    ).fetchone()
    item_metrics = connection.execute(
        """
        SELECT
            COUNT(*) AS order_lines,
            SUM(quantity) AS units,
            ROUND(1.0 * SUM(quantity) / COUNT(DISTINCT order_id), 2) AS units_per_order
        FROM order_items
        """
    ).fetchone()
    top_city = connection.execute(
        """
        SELECT city, ROUND(SUM(total_inr), 2) AS delivered_gmv_inr
        FROM orders
        WHERE order_status = 'delivered'
        GROUP BY city
        ORDER BY delivered_gmv_inr DESC
        LIMIT 1
        """
    ).fetchone()
    return {
        "marketplace": dict(order_metrics),
        "payments": dict(payment_metrics),
        "basket": dict(item_metrics),
        "top_city_by_delivered_gmv": dict(top_city),
    }


def _write_csv(path, headers, rows):
    target = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
        text=True,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(tuple(row) for row in rows)
        stream.flush()
        os.fsync(stream.fileno())
    Path(temporary_name).replace(target)
