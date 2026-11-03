import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from metroeats.catalog import CITY_BY_NAME, CUISINES
from metroeats.csvio import read_rows, sha256_file
from metroeats.schema import CUSTOMERS, DELIVERY_EVENTS, ORDER_ITEMS, ORDERS, PAYMENTS, RESTAURANTS, TABLES


@dataclass(frozen=True)
class ValidationIssue:
    table: str
    row_number: int
    message: str


@dataclass
class ValidationReport:
    row_counts: dict[str, int] = field(default_factory=dict)
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)

    @property
    def valid(self):
        return not self.errors

    def add_error(self, table, row_number, message):
        if len(self.errors) < 200:
            self.errors.append(ValidationIssue(table, row_number, message))

    def add_warning(self, table, row_number, message):
        if len(self.warnings) < 200:
            self.warnings.append(ValidationIssue(table, row_number, message))

    def to_dict(self):
        return {
            "valid": self.valid,
            "row_counts": dict(sorted(self.row_counts.items())),
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "metrics": self.metrics,
        }


class DatasetValidator:
    def __init__(self, directory, verify_checksums=True):
        self.directory = Path(directory)
        self.verify_checksums = verify_checksums
        self.report = ValidationReport()
        self.restaurant_ids = set()
        self.restaurant_cities = {}
        self.customer_ids = set()
        self.customer_cities = {}
        self.order_ids = set()
        self.order_totals = {}
        self.order_subtotals = {}
        self.order_statuses = {}
        self.item_subtotals = defaultdict(lambda: Decimal("0.00"))
        self.payment_orders = set()
        self.event_types = defaultdict(set)

    def validate(self):
        self._check_files()
        if self.report.errors:
            return self.report
        self._validate_restaurants()
        self._validate_customers()
        self._validate_orders()
        self._validate_items()
        self._validate_payments()
        self._validate_events()
        self._validate_cross_table_rules()
        self._validate_manifest()
        self.report.metrics = self._metrics()
        return self.report

    def _check_files(self):
        if not self.directory.is_dir():
            self.report.add_error("dataset", 0, f"directory does not exist: {self.directory}")
            return
        for table in TABLES:
            path = self.directory / table.filename
            if not path.is_file():
                self.report.add_error(table.filename, 0, "file is missing")
                continue
            try:
                iterator = read_rows(path, table)
                next(iterator, None)
            except ValueError as error:
                self.report.add_error(table.filename, 1, str(error))

    def _validate_restaurants(self):
        count = 0
        for row_number, row in enumerate(read_rows(self.directory / RESTAURANTS.filename, RESTAURANTS), start=2):
            count += 1
            identifier = row["restaurant_id"]
            self._unique(RESTAURANTS.filename, row_number, identifier, self.restaurant_ids)
            if row["city"] not in CITY_BY_NAME:
                self.report.add_error(RESTAURANTS.filename, row_number, "unknown city")
            if row["primary_cuisine"] not in CUISINES or row["secondary_cuisine"] not in CUISINES:
                self.report.add_error(RESTAURANTS.filename, row_number, "unknown cuisine")
            self._bounded_number(RESTAURANTS.filename, row_number, row["price_band"], 1, 4, "price_band")
            self._bounded_number(RESTAURANTS.filename, row_number, row["service_rating"], 1, 5, "service_rating")
            self._boolean(RESTAURANTS.filename, row_number, row["is_chain"], "is_chain")
            self.restaurant_cities[identifier] = row["city"]
        self.report.row_counts[RESTAURANTS.filename] = count

    def _validate_customers(self):
        count = 0
        for row_number, row in enumerate(read_rows(self.directory / CUSTOMERS.filename, CUSTOMERS), start=2):
            count += 1
            identifier = row["customer_id"]
            self._unique(CUSTOMERS.filename, row_number, identifier, self.customer_ids)
            if row["city"] not in CITY_BY_NAME:
                self.report.add_error(CUSTOMERS.filename, row_number, "unknown city")
            if row["preferred_cuisine"] not in CUISINES:
                self.report.add_error(CUSTOMERS.filename, row_number, "unknown preferred cuisine")
            self._boolean(CUSTOMERS.filename, row_number, row["marketing_opt_in"], "marketing_opt_in")
            self.customer_cities[identifier] = row["city"]
        self.report.row_counts[CUSTOMERS.filename] = count

    def _validate_orders(self):
        count = 0
        for row_number, row in enumerate(read_rows(self.directory / ORDERS.filename, ORDERS), start=2):
            count += 1
            identifier = row["order_id"]
            self._unique(ORDERS.filename, row_number, identifier, self.order_ids)
            customer_id = row["customer_id"]
            restaurant_id = row["restaurant_id"]
            if customer_id not in self.customer_ids:
                self.report.add_error(ORDERS.filename, row_number, "customer_id does not exist")
            if restaurant_id not in self.restaurant_ids:
                self.report.add_error(ORDERS.filename, row_number, "restaurant_id does not exist")
            if self.customer_cities.get(customer_id) != row["city"]:
                self.report.add_error(ORDERS.filename, row_number, "order city differs from customer city")
            if self.restaurant_cities.get(restaurant_id) != row["city"]:
                self.report.add_error(ORDERS.filename, row_number, "order city differs from restaurant city")
            subtotal = self._decimal(ORDERS.filename, row_number, row["subtotal_inr"], "subtotal_inr")
            discount = self._decimal(ORDERS.filename, row_number, row["discount_inr"], "discount_inr")
            delivery_fee = self._decimal(ORDERS.filename, row_number, row["delivery_fee_inr"], "delivery_fee_inr")
            tax = self._decimal(ORDERS.filename, row_number, row["tax_inr"], "tax_inr")
            tip = self._decimal(ORDERS.filename, row_number, row["tip_inr"], "tip_inr")
            total = self._decimal(ORDERS.filename, row_number, row["total_inr"], "total_inr")
            if None not in {subtotal, discount, delivery_fee, tax, tip, total}:
                expected = subtotal - discount + delivery_fee + tax + tip
                if abs(expected - total) > Decimal("0.01"):
                    self.report.add_error(ORDERS.filename, row_number, "total_inr does not reconcile")
                self.order_totals[identifier] = total
                self.order_subtotals[identifier] = subtotal
            status = row["order_status"]
            if status == "delivered":
                if not row["actual_delivery_minutes"] or not row["rating"]:
                    self.report.add_error(ORDERS.filename, row_number, "delivered order lacks delivery metrics")
                if row["cancellation_reason"]:
                    self.report.add_error(ORDERS.filename, row_number, "delivered order has a cancellation reason")
            else:
                if row["actual_delivery_minutes"] or row["rating"]:
                    self.report.add_error(ORDERS.filename, row_number, "cancelled order has delivery metrics")
                if not row["cancellation_reason"]:
                    self.report.add_error(ORDERS.filename, row_number, "cancelled order lacks a reason")
            try:
                datetime.fromisoformat(row["placed_at"])
            except ValueError:
                self.report.add_error(ORDERS.filename, row_number, "placed_at is not ISO-8601")
            self.order_statuses[identifier] = status
        self.report.row_counts[ORDERS.filename] = count

    def _validate_items(self):
        count = 0
        identifiers = set()
        for row_number, row in enumerate(read_rows(self.directory / ORDER_ITEMS.filename, ORDER_ITEMS), start=2):
            count += 1
            self._unique(ORDER_ITEMS.filename, row_number, row["order_item_id"], identifiers)
            order_id = row["order_id"]
            if order_id not in self.order_ids:
                self.report.add_error(ORDER_ITEMS.filename, row_number, "order_id does not exist")
            quantity = self._decimal(ORDER_ITEMS.filename, row_number, row["quantity"], "quantity")
            unit_price = self._decimal(ORDER_ITEMS.filename, row_number, row["unit_price_inr"], "unit_price_inr")
            line_total = self._decimal(ORDER_ITEMS.filename, row_number, row["line_total_inr"], "line_total_inr")
            if None not in {quantity, unit_price, line_total}:
                if quantity * unit_price != line_total:
                    self.report.add_error(ORDER_ITEMS.filename, row_number, "line_total_inr does not reconcile")
                self.item_subtotals[order_id] += line_total
            self._boolean(ORDER_ITEMS.filename, row_number, row["is_vegetarian"], "is_vegetarian")
        self.report.row_counts[ORDER_ITEMS.filename] = count

    def _validate_payments(self):
        count = 0
        identifiers = set()
        for row_number, row in enumerate(read_rows(self.directory / PAYMENTS.filename, PAYMENTS), start=2):
            count += 1
            self._unique(PAYMENTS.filename, row_number, row["payment_id"], identifiers)
            order_id = row["order_id"]
            if order_id not in self.order_ids:
                self.report.add_error(PAYMENTS.filename, row_number, "order_id does not exist")
            if order_id in self.payment_orders:
                self.report.add_error(PAYMENTS.filename, row_number, "order has multiple payments")
            self.payment_orders.add(order_id)
            amount = self._decimal(PAYMENTS.filename, row_number, row["amount_inr"], "amount_inr")
            if amount is not None and self.order_totals.get(order_id) != amount:
                self.report.add_error(PAYMENTS.filename, row_number, "payment amount differs from order total")
            refund = self._decimal(PAYMENTS.filename, row_number, row["refund_amount_inr"], "refund_amount_inr")
            if amount is not None and refund is not None and refund > amount:
                self.report.add_error(PAYMENTS.filename, row_number, "refund exceeds payment")
        self.report.row_counts[PAYMENTS.filename] = count

    def _validate_events(self):
        count = 0
        identifiers = set()
        last_timestamp = {}
        for row_number, row in enumerate(read_rows(self.directory / DELIVERY_EVENTS.filename, DELIVERY_EVENTS), start=2):
            count += 1
            self._unique(DELIVERY_EVENTS.filename, row_number, row["event_id"], identifiers)
            order_id = row["order_id"]
            if order_id not in self.order_ids:
                self.report.add_error(DELIVERY_EVENTS.filename, row_number, "order_id does not exist")
            self.event_types[order_id].add(row["event_type"])
            try:
                timestamp = datetime.fromisoformat(row["event_at"])
                if order_id in last_timestamp and timestamp < last_timestamp[order_id]:
                    self.report.add_error(DELIVERY_EVENTS.filename, row_number, "events are not chronological")
                last_timestamp[order_id] = timestamp
            except ValueError:
                self.report.add_error(DELIVERY_EVENTS.filename, row_number, "event_at is not ISO-8601")
        self.report.row_counts[DELIVERY_EVENTS.filename] = count

    def _validate_cross_table_rules(self):
        for order_id in self.order_ids:
            if self.item_subtotals.get(order_id) != self.order_subtotals.get(order_id):
                self.report.add_error(ORDER_ITEMS.filename, 0, f"item subtotal differs for {order_id}")
            if order_id not in self.payment_orders:
                self.report.add_error(PAYMENTS.filename, 0, f"payment missing for {order_id}")
            events = self.event_types.get(order_id, set())
            status = self.order_statuses[order_id]
            if status == "delivered" and "delivered" not in events and "picked_up_by_customer" not in events:
                self.report.add_error(DELIVERY_EVENTS.filename, 0, f"completion event missing for {order_id}")
            if status != "delivered" and "order_cancelled" not in events:
                self.report.add_error(DELIVERY_EVENTS.filename, 0, f"cancellation event missing for {order_id}")

    def _validate_manifest(self):
        path = self.directory / "dataset_manifest.json"
        if not path.is_file():
            self.report.add_error("dataset_manifest.json", 0, "file is missing")
            return
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            self.report.add_error("dataset_manifest.json", 0, str(error))
            return
        if manifest.get("synthetic") is not True:
            self.report.add_error("dataset_manifest.json", 0, "synthetic flag is not true")
        for table in TABLES:
            entry = manifest.get("tables", {}).get(table.filename, {})
            if entry.get("rows") != self.report.row_counts.get(table.filename):
                self.report.add_error("dataset_manifest.json", 0, f"row count differs for {table.filename}")
            if self.verify_checksums:
                checksum = sha256_file(self.directory / table.filename)
                if entry.get("sha256") != checksum:
                    self.report.add_error("dataset_manifest.json", 0, f"checksum differs for {table.filename}")

    def _metrics(self):
        status_counts = Counter(self.order_statuses.values())
        order_count = len(self.order_ids)
        delivered = status_counts["delivered"]
        return {
            "delivered_orders": delivered,
            "non_delivered_orders": order_count - delivered,
            "delivery_rate": round(delivered / order_count, 4) if order_count else 0,
            "average_items_per_order": round(
                self.report.row_counts.get(ORDER_ITEMS.filename, 0) / order_count,
                2,
            )
            if order_count
            else 0,
        }

    def _unique(self, table, row_number, identifier, identifiers):
        if not identifier:
            self.report.add_error(table, row_number, "primary key is blank")
        elif identifier in identifiers:
            self.report.add_error(table, row_number, "primary key is duplicated")
        identifiers.add(identifier)

    def _bounded_number(self, table, row_number, raw_value, minimum, maximum, field_name):
        value = self._decimal(table, row_number, raw_value, field_name)
        if value is not None and not Decimal(str(minimum)) <= value <= Decimal(str(maximum)):
            self.report.add_error(table, row_number, f"{field_name} is out of range")

    def _decimal(self, table, row_number, raw_value, field_name):
        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            self.report.add_error(table, row_number, f"{field_name} is not numeric")
            return None
        if not value.is_finite():
            self.report.add_error(table, row_number, f"{field_name} is not finite")
            return None
        return value

    def _boolean(self, table, row_number, value, field_name):
        if value not in {"true", "false"}:
            self.report.add_error(table, row_number, f"{field_name} is not a boolean")


def validate_dataset(directory="data", verify_checksums=True):
    return DatasetValidator(directory, verify_checksums=verify_checksums).validate()
