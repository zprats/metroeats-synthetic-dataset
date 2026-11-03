import random
import unittest
from datetime import date, datetime

from restaurants import average_menu_price, display_name, promised_minutes
from time_periods import IST, format_timestamp, random_order_time, weighted_calendar


class RestaurantHelpersTest(unittest.TestCase):
    def test_average_menu_price(self):
        menu = (
            ("One", "Main", True, 100),
            ("Two", "Main", False, 200),
        )
        self.assertEqual(average_menu_price(menu, 2), 168)

    def test_display_name(self):
        zones = ("North", "South", "East")
        self.assertEqual(display_name("Copper Kitchen", zones, 1), "Copper Kitchen")
        self.assertEqual(display_name("Copper Kitchen", zones, 2), "Copper Kitchen East")

    def test_promised_minutes(self):
        self.assertEqual(promised_minutes(25, 3, "high", "rain", "delivery"), 55)
        self.assertEqual(promised_minutes(25, 0, "low", "clear", "pickup"), 30)


class TimePeriodsTest(unittest.TestCase):
    def test_weighted_calendar(self):
        days, weights = weighted_calendar(date(2025, 1, 1), date(2025, 1, 5))
        self.assertEqual(days, [date(2025, 1, day) for day in range(1, 6)])
        self.assertEqual(weights, [1.0, 1.0, 1.0, 1.22, 1.22])

    def test_random_order_time(self):
        value = random_order_time(random.Random(11), ([date(2025, 7, 9)], [1.0]))
        self.assertEqual(value.date(), date(2025, 7, 9))
        self.assertEqual(value.tzinfo, IST)
        self.assertEqual(format_timestamp(value), value.isoformat(timespec="seconds"))

    def test_format_timestamp_rejects_naive_values(self):
        with self.assertRaises(ValueError):
            format_timestamp(datetime(2025, 1, 1))


if __name__ == "__main__":
    unittest.main()
