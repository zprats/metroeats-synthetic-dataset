from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class DatasetConfig:
    output_directory: Path = Path("data")
    seed: int = 202501
    restaurant_count: int = 5_000
    customer_count: int = 30_000
    order_count: int = 60_000


@dataclass(frozen=True)
class Restaurant:
    restaurant_id: str
    name: str
    city: str
    zone: str
    primary_cuisine: str
    secondary_cuisine: str
    price_band: int
    avg_item_price_inr: int
    avg_prep_minutes: int
    service_rating: float
    rating_count: int
    onboarded_at: date
    is_chain: bool
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Customer:
    customer_id: str
    signup_date: date
    city: str
    home_zone: str
    acquisition_channel: str
    loyalty_tier: str
    age_band: str
    preferred_cuisine: str
    marketing_opt_in: bool
    device_type: str


@dataclass(frozen=True)
class GeneratedDataset:
    directory: Path
    row_counts: dict[str, int]
    byte_sizes: dict[str, int]
    checksums: dict[str, str]
