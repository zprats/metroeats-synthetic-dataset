import math
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from metroeats.catalog import (
    ACQUISITION_CHANNELS,
    AGE_BANDS,
    CITIES,
    CUISINES,
    CUSTOMIZATIONS,
    DEVICE_TYPES,
    LOYALTY_TIERS,
    MENU,
    PAYMENT_METHODS,
    RESTAURANT_PREFIXES,
    RESTAURANT_SUFFIXES,
)
from metroeats.csvio import atomic_csv_writer, sha256_file, write_json
from metroeats.models import Customer, DatasetConfig, GeneratedDataset, Restaurant
from metroeats.schema import CUSTOMERS, DELIVERY_EVENTS, ORDER_ITEMS, ORDERS, PAYMENTS, RESTAURANTS, TABLES


IST = timezone(timedelta(hours=5, minutes=30))
DATA_START = date(2025, 1, 1)
DATA_END = date(2025, 12, 31)
HOUR_WEIGHTS = (2, 1, 1, 1, 1, 2, 4, 7, 9, 7, 5, 12, 17, 17, 12, 7, 7, 9, 13, 20, 24, 22, 16, 8)
CUISINE_WEIGHTS = (16, 13, 14, 11, 10, 9, 7, 6, 5, 5, 4)


class DatasetGenerator:
    def __init__(self, config):
        self.config = config
        self.random = random.Random(config.seed)
        self.row_counts = {table.filename: 0 for table in TABLES}
        self.customer_order_counts = defaultdict(int)
        self.event_sequence = 0

    def generate(self):
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        restaurants = self._generate_restaurants()
        customers = self._generate_customers()
        self._generate_facts(restaurants, customers)
        byte_sizes = {}
        checksums = {}
        for table in TABLES:
            path = self.config.output_directory / table.filename
            byte_sizes[table.filename] = path.stat().st_size
            checksums[table.filename] = sha256_file(path)
        manifest = {
            "dataset": "MetroEats Marketplace Operations",
            "schema_version": "1.0.0",
            "synthetic": True,
            "currency": "INR",
            "timezone": "Asia/Kolkata",
            "period_start": DATA_START.isoformat(),
            "period_end": DATA_END.isoformat(),
            "seed": self.config.seed,
            "tables": {
                name: {
                    "rows": self.row_counts[name],
                    "bytes": byte_sizes[name],
                    "sha256": checksums[name],
                }
                for name in sorted(self.row_counts)
            },
        }
        write_json(self.config.output_directory / "dataset_manifest.json", manifest)
        return GeneratedDataset(self.config.output_directory, dict(self.row_counts), byte_sizes, checksums)

    def _generate_restaurants(self):
        restaurants = []
        city_weights = [city.order_weight for city in CITIES]
        used_names = defaultdict(int)
        with atomic_csv_writer(self.config.output_directory, RESTAURANTS) as writer:
            for index in range(1, self.config.restaurant_count + 1):
                city = self.random.choices(CITIES, weights=city_weights, k=1)[0]
                primary_cuisine = self.random.choices(CUISINES, weights=CUISINE_WEIGHTS, k=1)[0]
                secondary_cuisine = self.random.choice([value for value in CUISINES if value != primary_cuisine])
                price_band = self.random.choices((1, 2, 3, 4), weights=(34, 42, 20, 4), k=1)[0]
                average_menu_price = int(
                    round(
                        sum(item[3] for item in MENU[primary_cuisine])
                        / len(MENU[primary_cuisine])
                        * (0.72 + price_band * 0.2)
                    )
                )
                is_chain = self.random.random() < 0.17
                if is_chain:
                    chain_number = index % 140
                    base_name = f"{RESTAURANT_PREFIXES[chain_number % len(RESTAURANT_PREFIXES)]} {RESTAURANT_SUFFIXES[chain_number % len(RESTAURANT_SUFFIXES)]}"
                else:
                    base_name = f"{self.random.choice(RESTAURANT_PREFIXES)} {self.random.choice(RESTAURANT_SUFFIXES)}"
                used_names[(city.name, base_name)] += 1
                occurrence = used_names[(city.name, base_name)]
                restaurant_name = base_name if occurrence == 1 else f"{base_name} {city.zones[occurrence % len(city.zones)]}"
                latitude, longitude = self._nearby_coordinate(city.latitude, city.longitude, 0.16)
                restaurant = Restaurant(
                    restaurant_id=f"RST{index:07d}",
                    name=restaurant_name,
                    city=city.name,
                    zone=self.random.choice(city.zones),
                    primary_cuisine=primary_cuisine,
                    secondary_cuisine=secondary_cuisine,
                    price_band=price_band,
                    avg_item_price_inr=average_menu_price,
                    avg_prep_minutes=max(12, min(48, round(self.random.gauss(25 + price_band * 2, 6)))),
                    service_rating=round(max(2.6, min(4.9, self.random.gauss(4.12, 0.38))), 1),
                    rating_count=max(8, int(self.random.lognormvariate(6.7, 1.1))),
                    onboarded_at=self._random_date(date(2017, 1, 1), date(2024, 12, 31)),
                    is_chain=is_chain,
                    latitude=latitude,
                    longitude=longitude,
                )
                restaurants.append(restaurant)
                writer.writerow(
                    {
                        "restaurant_id": restaurant.restaurant_id,
                        "restaurant_name": restaurant.name,
                        "city": restaurant.city,
                        "zone": restaurant.zone,
                        "primary_cuisine": restaurant.primary_cuisine,
                        "secondary_cuisine": restaurant.secondary_cuisine,
                        "price_band": restaurant.price_band,
                        "avg_item_price_inr": restaurant.avg_item_price_inr,
                        "avg_prep_minutes": restaurant.avg_prep_minutes,
                        "service_rating": f"{restaurant.service_rating:.1f}",
                        "rating_count": restaurant.rating_count,
                        "onboarded_at": restaurant.onboarded_at.isoformat(),
                        "is_chain": self._boolean(restaurant.is_chain),
                        "latitude": f"{restaurant.latitude:.6f}",
                        "longitude": f"{restaurant.longitude:.6f}",
                    }
                )
                self.row_counts[RESTAURANTS.filename] += 1
        return restaurants

    def _generate_customers(self):
        customers = []
        city_weights = [city.order_weight for city in CITIES]
        for_index = range(1, self.config.customer_count + 1)
        with atomic_csv_writer(self.config.output_directory, CUSTOMERS) as writer:
            for index in for_index:
                city = self.random.choices(CITIES, weights=city_weights, k=1)[0]
                customer = Customer(
                    customer_id=f"CUS{index:08d}",
                    signup_date=self._weighted_signup_date(),
                    city=city.name,
                    home_zone=self.random.choice(city.zones),
                    acquisition_channel=self.random.choices(
                        ACQUISITION_CHANNELS,
                        weights=(30, 20, 16, 18, 7, 9),
                        k=1,
                    )[0],
                    loyalty_tier=self.random.choices(LOYALTY_TIERS, weights=(61, 24, 11, 4), k=1)[0],
                    age_band=self.random.choices(AGE_BANDS, weights=(19, 43, 23, 10, 5), k=1)[0],
                    preferred_cuisine=self.random.choices(CUISINES, weights=CUISINE_WEIGHTS, k=1)[0],
                    marketing_opt_in=self.random.random() < 0.62,
                    device_type=self.random.choices(DEVICE_TYPES, weights=(69, 27, 4), k=1)[0],
                )
                customers.append(customer)
                writer.writerow(
                    {
                        "customer_id": customer.customer_id,
                        "signup_date": customer.signup_date.isoformat(),
                        "city": customer.city,
                        "home_zone": customer.home_zone,
                        "acquisition_channel": customer.acquisition_channel,
                        "loyalty_tier": customer.loyalty_tier,
                        "age_band": customer.age_band,
                        "preferred_cuisine": customer.preferred_cuisine,
                        "marketing_opt_in": self._boolean(customer.marketing_opt_in),
                        "device_type": customer.device_type,
                    }
                )
                self.row_counts[CUSTOMERS.filename] += 1
        return customers

    def _generate_facts(self, restaurants, customers):
        restaurants_by_city = defaultdict(list)
        restaurants_by_city_cuisine = defaultdict(list)
        customers_by_city = defaultdict(list)
        for restaurant in restaurants:
            restaurants_by_city[restaurant.city].append(restaurant)
            restaurants_by_city_cuisine[(restaurant.city, restaurant.primary_cuisine)].append(restaurant)
        for customer in customers:
            customers_by_city[customer.city].append(customer)
        city_names = tuple(name for name in customers_by_city if restaurants_by_city[name])
        if not city_names:
            raise ValueError("no customer city has an available restaurant")
        city_weights = [len(customers_by_city[name]) for name in city_names]
        calendar = self._weighted_calendar()
        with (
            atomic_csv_writer(self.config.output_directory, ORDERS) as order_writer,
            atomic_csv_writer(self.config.output_directory, ORDER_ITEMS) as item_writer,
            atomic_csv_writer(self.config.output_directory, PAYMENTS) as payment_writer,
            atomic_csv_writer(self.config.output_directory, DELIVERY_EVENTS) as event_writer,
        ):
            for index in range(1, self.config.order_count + 1):
                city_name = self.random.choices(city_names, weights=city_weights, k=1)[0]
                customer = self.random.choice(customers_by_city[city_name])
                preferred_group = restaurants_by_city_cuisine[(city_name, customer.preferred_cuisine)]
                if preferred_group and self.random.random() < 0.57:
                    restaurant = self.random.choice(preferred_group)
                else:
                    restaurant = self.random.choice(restaurants_by_city[city_name])
                placed_at = self._placed_at(calendar)
                order_id = f"ORD2025{index:08d}"
                items, subtotal = self._make_items(order_id, restaurant)
                fulfillment_mode = self.random.choices(("delivery", "pickup"), weights=(96, 4), k=1)[0]
                distance_km = 0.0 if fulfillment_mode == "pickup" else round(min(15.0, max(0.4, self.random.gammavariate(2.15, 1.35))), 2)
                weather = self._weather(city_name, placed_at.month)
                traffic = self._traffic(placed_at.hour, placed_at.weekday(), weather)
                promo_code, discount = self._promotion(customer, placed_at, weather, subtotal)
                delivery_fee = self._delivery_fee(distance_km, fulfillment_mode, promo_code)
                tax = round(subtotal * 0.05, 2)
                tip = self._tip(fulfillment_mode)
                total = round(max(0.0, subtotal - discount + delivery_fee + tax + tip), 2)
                promised_minutes = self._promised_minutes(restaurant, distance_km, traffic, weather, fulfillment_mode)
                status, cancellation_reason = self._order_outcome(
                    restaurant,
                    distance_km,
                    traffic,
                    weather,
                    fulfillment_mode,
                )
                actual_minutes = self._actual_minutes(promised_minutes, traffic, weather, fulfillment_mode) if status == "delivered" else None
                rating = self._rating(actual_minutes, promised_minutes, restaurant.service_rating) if status == "delivered" else None
                order_writer.writerow(
                    {
                        "order_id": order_id,
                        "customer_id": customer.customer_id,
                        "restaurant_id": restaurant.restaurant_id,
                        "city": city_name,
                        "placed_at": self._timestamp(placed_at),
                        "order_status": status,
                        "fulfillment_mode": fulfillment_mode,
                        "subtotal_inr": self._money(subtotal),
                        "discount_inr": self._money(discount),
                        "delivery_fee_inr": self._money(delivery_fee),
                        "tax_inr": self._money(tax),
                        "tip_inr": self._money(tip),
                        "total_inr": self._money(total),
                        "promo_code": promo_code,
                        "distance_km": f"{distance_km:.2f}",
                        "weather": weather,
                        "traffic": traffic,
                        "promised_minutes": promised_minutes,
                        "actual_delivery_minutes": "" if actual_minutes is None else actual_minutes,
                        "cancellation_reason": cancellation_reason,
                        "rating": "" if rating is None else rating,
                    }
                )
                self.row_counts[ORDERS.filename] += 1
                for item in items:
                    item_writer.writerow(item)
                    self.row_counts[ORDER_ITEMS.filename] += 1
                payment_writer.writerow(
                    self._payment_row(
                        index,
                        order_id,
                        placed_at,
                        status,
                        total,
                        cancellation_reason,
                    )
                )
                self.row_counts[PAYMENTS.filename] += 1
                for event in self._delivery_events(
                    order_id,
                    restaurant,
                    placed_at,
                    status,
                    fulfillment_mode,
                    distance_km,
                    actual_minutes,
                    promised_minutes,
                ):
                    event_writer.writerow(event)
                    self.row_counts[DELIVERY_EVENTS.filename] += 1
                self.customer_order_counts[customer.customer_id] += 1

    def _make_items(self, order_id, restaurant):
        item_count = self.random.choices((1, 2, 3, 4, 5), weights=(18, 34, 28, 14, 6), k=1)[0]
        choices = MENU[restaurant.primary_cuisine]
        rows = []
        subtotal = 0.0
        for position in range(1, item_count + 1):
            item_name, category, vegetarian, base_price = self.random.choice(choices)
            quantity = self.random.choices((1, 2, 3), weights=(82, 16, 2), k=1)[0]
            price_multiplier = 0.74 + restaurant.price_band * 0.2 + self.random.uniform(-0.07, 0.08)
            unit_price = float(max(39, int(round(base_price * price_multiplier / 5) * 5)))
            line_total = unit_price * quantity
            subtotal += line_total
            rows.append(
                {
                    "order_item_id": f"{order_id}-I{position:02d}",
                    "order_id": order_id,
                    "item_position": position,
                    "item_name": item_name,
                    "item_category": category,
                    "cuisine": restaurant.primary_cuisine,
                    "quantity": quantity,
                    "unit_price_inr": self._money(unit_price),
                    "line_total_inr": self._money(line_total),
                    "is_vegetarian": self._boolean(vegetarian),
                    "customization": self.random.choices(CUSTOMIZATIONS, weights=(70, 7, 5, 5, 3, 10), k=1)[0],
                }
            )
        return rows, round(subtotal, 2)

    def _promotion(self, customer, placed_at, weather, subtotal):
        first_order = self.customer_order_counts[customer.customer_id] == 0
        options = [("NONE", 0.0)]
        if first_order:
            options.extend((("WELCOME100", min(100.0, subtotal * 0.3)),) * 4)
        options.extend(
            (
                ("SAVE20", min(120.0, subtotal * 0.2)),
                ("FREEDEL", 0.0),
                ("NONE", 0.0),
                ("NONE", 0.0),
            )
        )
        if placed_at.weekday() >= 5:
            options.extend((("WEEKEND15", min(150.0, subtotal * 0.15)),) * 2)
        if weather in {"rain", "heavy_rain"}:
            options.append(("RAINYDAY", min(90.0, subtotal * 0.12)))
        if customer.loyalty_tier in {"gold", "platinum"}:
            options.extend((("LOYAL25", min(175.0, subtotal * 0.25)),) * 2)
        return self.random.choice(options)

    def _delivery_fee(self, distance_km, fulfillment_mode, promo_code):
        if fulfillment_mode == "pickup" or promo_code == "FREEDEL":
            return 0.0
        fee = 19 + max(0.0, distance_km - 2.0) * 8
        return float(int(math.ceil(fee / 5.0) * 5))

    def _tip(self, fulfillment_mode):
        if fulfillment_mode == "pickup" or self.random.random() > 0.13:
            return 0.0
        return float(self.random.choices((10, 20, 30, 50, 100), weights=(18, 36, 25, 17, 4), k=1)[0])

    def _promised_minutes(self, restaurant, distance_km, traffic, weather, fulfillment_mode):
        if fulfillment_mode == "pickup":
            return max(15, int(round((restaurant.avg_prep_minutes + 5) / 5) * 5))
        traffic_buffer = {"low": 0, "moderate": 5, "high": 11, "severe": 18}[traffic]
        weather_buffer = {"clear": 0, "cloudy": 1, "rain": 6, "heavy_rain": 13, "heatwave": 3}[weather]
        estimate = restaurant.avg_prep_minutes + distance_km * 3.1 + traffic_buffer + weather_buffer
        return max(20, int(math.ceil(estimate / 5.0) * 5))

    def _order_outcome(self, restaurant, distance_km, traffic, weather, fulfillment_mode):
        cancellation_probability = 0.035
        cancellation_probability += 0.035 if weather == "heavy_rain" else 0.012 if weather == "rain" else 0.0
        cancellation_probability += 0.025 if traffic == "severe" else 0.01 if traffic == "high" else 0.0
        cancellation_probability += 0.018 if distance_km > 9 else 0.0
        cancellation_probability += 0.017 if restaurant.avg_prep_minutes > 36 else 0.0
        cancellation_probability -= 0.012 if fulfillment_mode == "pickup" else 0.0
        if self.random.random() >= cancellation_probability:
            return "delivered", ""
        reasons = (
            "customer_changed_mind",
            "restaurant_closed",
            "item_unavailable",
            "courier_unavailable",
            "address_issue",
            "payment_failure",
        )
        weights = [22, 13, 20, 23, 8, 14]
        if weather == "heavy_rain":
            weights[3] += 25
        reason = self.random.choices(reasons, weights=weights, k=1)[0]
        if reason == "customer_changed_mind":
            return "cancelled_by_customer", reason
        if reason in {"restaurant_closed", "item_unavailable"}:
            return "cancelled_by_restaurant", reason
        return "delivery_failed", reason

    def _actual_minutes(self, promised_minutes, traffic, weather, fulfillment_mode):
        deviation = self.random.gauss(-2.5, 7.0)
        deviation += 8 if traffic == "severe" else 3 if traffic == "high" else 0
        deviation += 10 if weather == "heavy_rain" else 4 if weather == "rain" else 0
        if fulfillment_mode == "pickup":
            deviation -= 2
        return max(12, int(round(promised_minutes + deviation)))

    def _rating(self, actual_minutes, promised_minutes, restaurant_rating):
        delay = max(0, actual_minutes - promised_minutes)
        score = restaurant_rating + self.random.gauss(0.15, 0.55) - delay * 0.045
        return max(1, min(5, int(round(score))))

    def _payment_row(self, index, order_id, placed_at, status, amount, cancellation_reason):
        method = self.random.choices(PAYMENT_METHODS, weights=(49, 18, 8, 13, 8, 4), k=1)[0]
        initiated_at = placed_at + timedelta(seconds=self.random.randint(8, 70))
        failure_reason = ""
        refund_amount = 0.0
        if status == "delivered":
            if method == "cash":
                payment_status = "collected"
                settled_at = placed_at + timedelta(minutes=self.random.randint(60, 240))
                gateway_fee = 0.0
            elif self.random.random() < 0.018:
                payment_status = "partially_refunded"
                settled_at = placed_at + timedelta(days=self.random.randint(2, 5))
                refund_amount = round(amount * self.random.choice((0.1, 0.2, 0.25, 0.5)), 2)
                gateway_fee = round(amount * 0.018, 2)
            else:
                payment_status = "captured"
                settled_at = placed_at + timedelta(days=self.random.randint(1, 3))
                gateway_fee = round(amount * 0.018, 2)
        elif method == "cash":
            payment_status = "not_collected"
            settled_at = None
            gateway_fee = 0.0
        elif cancellation_reason == "payment_failure":
            payment_status = "failed"
            settled_at = None
            failure_reason = self.random.choice(("bank_declined", "timeout", "insufficient_funds", "authentication_failed"))
            gateway_fee = 0.0
        elif self.random.random() < 0.28:
            payment_status = "voided"
            settled_at = None
            gateway_fee = 0.0
        else:
            payment_status = "refunded"
            settled_at = placed_at + timedelta(days=self.random.randint(1, 5))
            refund_amount = amount
            gateway_fee = round(amount * 0.004, 2)
        return {
            "payment_id": f"PAY2025{index:08d}",
            "order_id": order_id,
            "payment_method": method,
            "payment_status": payment_status,
            "amount_inr": self._money(amount),
            "gateway_fee_inr": self._money(gateway_fee),
            "initiated_at": self._timestamp(initiated_at),
            "settled_at": "" if settled_at is None else self._timestamp(settled_at),
            "failure_reason": failure_reason,
            "refund_amount_inr": self._money(refund_amount),
        }

    def _delivery_events(
        self,
        order_id,
        restaurant,
        placed_at,
        status,
        fulfillment_mode,
        distance_km,
        actual_minutes,
        promised_minutes,
    ):
        courier_id = "" if fulfillment_mode == "pickup" else f"CUR{self.random.randint(1, 8_500):07d}"
        destination_latitude, destination_longitude = self._destination_coordinate(
            restaurant.latitude,
            restaurant.longitude,
            distance_km,
        )
        if status == "delivered":
            total_minutes = actual_minutes or promised_minutes
            confirmed = min(4, max(1, int(total_minutes * 0.08)))
            if fulfillment_mode == "pickup":
                schedule = (
                    ("order_placed", 0, 1.0, "customer_app"),
                    ("restaurant_confirmed", confirmed, 1.0, "restaurant_app"),
                    ("ready_for_pickup", max(confirmed + 1, total_minutes - 4), 1.0, "restaurant_app"),
                    ("picked_up_by_customer", total_minutes, 0.0, "customer_app"),
                )
            else:
                assigned = max(confirmed + 1, int(total_minutes * 0.18))
                picked_up = max(assigned + 2, int(total_minutes * 0.62))
                schedule = (
                    ("order_placed", 0, 1.0, "customer_app"),
                    ("restaurant_confirmed", confirmed, 1.0, "restaurant_app"),
                    ("courier_assigned", assigned, 1.0, "dispatch"),
                    ("picked_up", picked_up, 0.9, "courier_app"),
                    ("delivered", total_minutes, 0.0, "courier_app"),
                )
        else:
            cancelled_minute = self.random.randint(2, max(3, min(14, promised_minutes // 3)))
            schedule = (
                ("order_placed", 0, 1.0, "customer_app"),
                ("restaurant_confirmed", 1, 1.0, "restaurant_app"),
                ("order_cancelled", cancelled_minute, 1.0, "dispatch"),
            )
        rows = []
        for event_type, minute, remaining_ratio, source in schedule:
            self.event_sequence += 1
            progress = 1.0 - remaining_ratio
            latitude = restaurant.latitude + (destination_latitude - restaurant.latitude) * progress
            longitude = restaurant.longitude + (destination_longitude - restaurant.longitude) * progress
            rows.append(
                {
                    "event_id": f"EVT{self.event_sequence:010d}",
                    "order_id": order_id,
                    "courier_id": courier_id,
                    "event_type": event_type,
                    "event_at": self._timestamp(placed_at + timedelta(minutes=minute)),
                    "latitude": f"{latitude:.6f}",
                    "longitude": f"{longitude:.6f}",
                    "distance_remaining_km": f"{distance_km * remaining_ratio:.2f}",
                    "event_source": source,
                }
            )
        return rows

    def _weighted_calendar(self):
        days = []
        weights = []
        current = DATA_START
        while current <= DATA_END:
            weight = 1.22 if current.weekday() >= 5 else 1.0
            if current.month in {10, 11, 12}:
                weight *= 1.08
            days.append(current)
            weights.append(weight)
            current += timedelta(days=1)
        return days, weights

    def _placed_at(self, calendar):
        days, weights = calendar
        day = self.random.choices(days, weights=weights, k=1)[0]
        hour = self.random.choices(tuple(range(24)), weights=HOUR_WEIGHTS, k=1)[0]
        return datetime.combine(
            day,
            time(hour, self.random.randrange(60), self.random.randrange(60)),
            tzinfo=IST,
        )

    def _weather(self, city_name, month):
        city = next(city for city in CITIES if city.name == city_name)
        if month in city.rain_months:
            if city_name == "Mumbai":
                return self.random.choices(
                    ("clear", "cloudy", "rain", "heavy_rain"),
                    weights=(20, 27, 36, 17),
                    k=1,
                )[0]
            return self.random.choices(
                ("clear", "cloudy", "rain", "heavy_rain"),
                weights=(39, 31, 24, 6),
                k=1,
            )[0]
        if month in {3, 4, 5, 6} and city_name in {"Delhi NCR", "Ahmedabad", "Hyderabad"}:
            return self.random.choices(("clear", "cloudy", "heatwave"), weights=(65, 15, 20), k=1)[0]
        return self.random.choices(("clear", "cloudy", "rain"), weights=(76, 19, 5), k=1)[0]

    def _traffic(self, hour, weekday, weather):
        if hour in {8, 9, 18, 19, 20, 21}:
            values = ("moderate", "high", "severe")
            weights = (31, 49, 20)
        elif hour in {12, 13, 14, 17, 22}:
            values = ("low", "moderate", "high", "severe")
            weights = (12, 52, 30, 6)
        else:
            values = ("low", "moderate", "high")
            weights = (58, 36, 6)
        traffic = self.random.choices(values, weights=weights, k=1)[0]
        if weather == "heavy_rain" and traffic in {"low", "moderate"}:
            return "high"
        if weekday >= 5 and hour < 17 and traffic == "high":
            return "moderate"
        return traffic

    def _weighted_signup_date(self):
        start = date(2019, 1, 1)
        end = date(2024, 12, 31)
        span = (end - start).days
        position = int(span * (self.random.random() ** 0.58))
        return start + timedelta(days=position)

    def _random_date(self, start, end):
        return start + timedelta(days=self.random.randint(0, (end - start).days))

    def _nearby_coordinate(self, latitude, longitude, spread):
        return (
            latitude + self.random.uniform(-spread, spread),
            longitude + self.random.uniform(-spread, spread),
        )

    def _destination_coordinate(self, latitude, longitude, distance_km):
        angle = self.random.uniform(0, math.tau)
        latitude_delta = math.cos(angle) * distance_km / 111.0
        longitude_scale = max(0.2, math.cos(math.radians(latitude)))
        longitude_delta = math.sin(angle) * distance_km / (111.0 * longitude_scale)
        return latitude + latitude_delta, longitude + longitude_delta

    @staticmethod
    def _money(value):
        return f"{value:.2f}"

    @staticmethod
    def _timestamp(value):
        return value.isoformat(timespec="seconds")

    @staticmethod
    def _boolean(value):
        return "true" if value else "false"


def generate_dataset(config=None):
    return DatasetGenerator(config or DatasetConfig()).generate()
