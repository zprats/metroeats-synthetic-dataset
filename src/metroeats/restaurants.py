import math


TRAFFIC_MINUTE_BUFFER = {
    "low": 0,
    "moderate": 5,
    "high": 11,
    "severe": 18,
}

WEATHER_MINUTE_BUFFER = {
    "clear": 0,
    "cloudy": 1,
    "rain": 6,
    "heavy_rain": 13,
    "heatwave": 3,
}


def average_menu_price(menu, price_band):
    if not menu:
        raise ValueError("menu must contain at least one item")
    if price_band not in {1, 2, 3, 4}:
        raise ValueError("price_band must be between 1 and 4")
    base_average = sum(item[3] for item in menu) / len(menu)
    return int(round(base_average * (0.72 + price_band * 0.2)))


def display_name(base_name, zones, occurrence):
    if occurrence < 1:
        raise ValueError("occurrence must be positive")
    if occurrence == 1:
        return base_name
    if not zones:
        raise ValueError("zones must contain at least one value")
    return f"{base_name} {zones[occurrence % len(zones)]}"


def promised_minutes(average_prep_minutes, distance_km, traffic, weather, fulfillment_mode):
    if fulfillment_mode == "pickup":
        return max(15, int(round((average_prep_minutes + 5) / 5) * 5))
    if fulfillment_mode != "delivery":
        raise ValueError(f"unsupported fulfillment mode: {fulfillment_mode}")
    estimate = (
        average_prep_minutes
        + distance_km * 3.1
        + TRAFFIC_MINUTE_BUFFER[traffic]
        + WEATHER_MINUTE_BUFFER[weather]
    )
    return max(20, int(math.ceil(estimate / 5.0) * 5))
