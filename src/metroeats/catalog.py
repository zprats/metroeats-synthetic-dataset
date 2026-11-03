from dataclasses import dataclass


@dataclass(frozen=True)
class CityProfile:
    name: str
    latitude: float
    longitude: float
    order_weight: int
    rain_months: tuple[int, ...]
    zones: tuple[str, ...]


CITIES = (
    CityProfile(
        "Bengaluru",
        12.9716,
        77.5946,
        24,
        (5, 6, 7, 8, 9, 10),
        ("Indiranagar", "Koramangala", "HSR Layout", "Whitefield", "Jayanagar", "Malleshwaram"),
    ),
    CityProfile(
        "Mumbai",
        19.0760,
        72.8777,
        20,
        (6, 7, 8, 9),
        ("Bandra", "Andheri", "Powai", "Lower Parel", "Chembur", "Borivali"),
    ),
    CityProfile(
        "Delhi NCR",
        28.6139,
        77.2090,
        18,
        (7, 8, 9),
        ("Connaught Place", "Saket", "Gurugram Sector 29", "Noida Sector 18", "Rajouri Garden", "Rohini"),
    ),
    CityProfile(
        "Hyderabad",
        17.3850,
        78.4867,
        12,
        (6, 7, 8, 9, 10),
        ("Banjara Hills", "Hitech City", "Jubilee Hills", "Gachibowli", "Kondapur", "Secunderabad"),
    ),
    CityProfile(
        "Pune",
        18.5204,
        73.8567,
        10,
        (6, 7, 8, 9),
        ("Baner", "Koregaon Park", "Viman Nagar", "Kothrud", "Hinjawadi", "Hadapsar"),
    ),
    CityProfile(
        "Chennai",
        13.0827,
        80.2707,
        7,
        (10, 11, 12),
        ("T Nagar", "Anna Nagar", "Adyar", "Velachery", "Nungambakkam", "OMR"),
    ),
    CityProfile(
        "Kolkata",
        22.5726,
        88.3639,
        5,
        (6, 7, 8, 9),
        ("Salt Lake", "Park Street", "New Town", "Ballygunge", "Gariahat", "Howrah"),
    ),
    CityProfile(
        "Ahmedabad",
        23.0225,
        72.5714,
        4,
        (7, 8, 9),
        ("Navrangpura", "Satellite", "Bodakdev", "Prahlad Nagar", "Vastrapur", "Maninagar"),
    ),
)

CITY_BY_NAME = {city.name: city for city in CITIES}

MENU = {
    "North Indian": (
        ("Paneer Butter Masala", "Main Course", True, 289),
        ("Dal Makhani", "Main Course", True, 239),
        ("Butter Chicken", "Main Course", False, 349),
        ("Garlic Naan", "Bread", True, 69),
        ("Jeera Rice", "Rice", True, 169),
        ("Tandoori Chicken", "Starter", False, 379),
        ("Gulab Jamun", "Dessert", True, 109),
    ),
    "South Indian": (
        ("Masala Dosa", "Main Course", True, 149),
        ("Idli Vada Combo", "Breakfast", True, 119),
        ("Ghee Podi Dosa", "Main Course", True, 189),
        ("Chicken Chettinad", "Main Course", False, 329),
        ("Curd Rice", "Rice", True, 139),
        ("Filter Coffee", "Beverage", True, 79),
        ("Mysore Pak", "Dessert", True, 99),
    ),
    "Biryani": (
        ("Chicken Dum Biryani", "Biryani", False, 299),
        ("Mutton Biryani", "Biryani", False, 399),
        ("Paneer Biryani", "Biryani", True, 269),
        ("Egg Biryani", "Biryani", False, 239),
        ("Mirchi Ka Salan", "Side", True, 89),
        ("Double Ka Meetha", "Dessert", True, 119),
        ("Masala Chaach", "Beverage", True, 69),
    ),
    "Chinese": (
        ("Hakka Noodles", "Noodles", True, 229),
        ("Chicken Fried Rice", "Rice", False, 249),
        ("Chilli Paneer", "Starter", True, 269),
        ("Chicken Manchurian", "Starter", False, 289),
        ("Veg Momos", "Dumplings", True, 169),
        ("Hot and Sour Soup", "Soup", True, 149),
        ("Darsaan", "Dessert", True, 179),
    ),
    "Fast Food": (
        ("Classic Veg Burger", "Burger", True, 159),
        ("Crispy Chicken Burger", "Burger", False, 219),
        ("Peri Peri Fries", "Side", True, 129),
        ("Chicken Wrap", "Wrap", False, 199),
        ("Veggie Loaded Sandwich", "Sandwich", True, 179),
        ("Cold Coffee", "Beverage", True, 149),
        ("Chocolate Brownie", "Dessert", True, 119),
    ),
    "Pizza": (
        ("Margherita Pizza", "Pizza", True, 249),
        ("Farmhouse Pizza", "Pizza", True, 369),
        ("Chicken Tikka Pizza", "Pizza", False, 419),
        ("Pepperoni Pizza", "Pizza", False, 449),
        ("Garlic Bread", "Side", True, 159),
        ("Cheese Dip", "Side", True, 49),
        ("Choco Lava Cake", "Dessert", True, 109),
    ),
    "Street Food": (
        ("Pav Bhaji", "Main Course", True, 159),
        ("Vada Pav", "Snack", True, 59),
        ("Pani Puri", "Chaat", True, 99),
        ("Samosa Chaat", "Chaat", True, 129),
        ("Chicken Kathi Roll", "Roll", False, 189),
        ("Dahi Puri", "Chaat", True, 119),
        ("Masala Lemonade", "Beverage", True, 79),
    ),
    "Healthy": (
        ("Quinoa Power Bowl", "Bowl", True, 329),
        ("Grilled Chicken Salad", "Salad", False, 349),
        ("Paneer Protein Bowl", "Bowl", True, 319),
        ("Avocado Toast", "Breakfast", True, 289),
        ("Berry Smoothie", "Beverage", True, 219),
        ("Hummus Platter", "Starter", True, 269),
        ("Chia Pudding", "Dessert", True, 189),
    ),
    "Continental": (
        ("Penne Arrabbiata", "Pasta", True, 319),
        ("Grilled Chicken Steak", "Main Course", False, 449),
        ("Mushroom Risotto", "Main Course", True, 389),
        ("Fish and Chips", "Main Course", False, 419),
        ("Caesar Salad", "Salad", True, 279),
        ("Tiramisu", "Dessert", True, 229),
        ("Iced Tea", "Beverage", True, 129),
    ),
    "Desserts": (
        ("Belgian Chocolate Cake", "Cake", True, 229),
        ("New York Cheesecake", "Cake", True, 249),
        ("Red Velvet Jar", "Jar Dessert", True, 179),
        ("Mango Ice Cream", "Ice Cream", True, 149),
        ("Kunafa", "Dessert", True, 269),
        ("Chocolate Waffle", "Waffle", True, 219),
        ("Cold Cocoa", "Beverage", True, 169),
    ),
    "Beverages": (
        ("Classic Milk Tea", "Tea", True, 89),
        ("Cold Brew Coffee", "Coffee", True, 179),
        ("Mango Shake", "Shake", True, 159),
        ("Watermelon Juice", "Juice", True, 129),
        ("Lemon Iced Tea", "Tea", True, 139),
        ("Chocolate Thickshake", "Shake", True, 199),
        ("Tender Coconut Water", "Juice", True, 119),
    ),
}

CUISINES = tuple(MENU)

RESTAURANT_PREFIXES = (
    "Copper",
    "Spice",
    "Urban",
    "Royal",
    "Green",
    "Bombay",
    "Deccan",
    "Coastal",
    "Heritage",
    "Midnight",
    "Daily",
    "Grandma's",
    "The Hungry",
    "Little",
    "House of",
)

RESTAURANT_SUFFIXES = (
    "Kitchen",
    "Table",
    "Cafe",
    "Bowl Co.",
    "Tiffin Room",
    "Eatery",
    "Junction",
    "Canteen",
    "Bistro",
    "Dhaba",
    "Collective",
    "Works",
)

ACQUISITION_CHANNELS = ("organic", "paid_search", "social", "referral", "offline", "partnership")
LOYALTY_TIERS = ("none", "silver", "gold", "platinum")
AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55+")
DEVICE_TYPES = ("android", "ios", "web")
PAYMENT_METHODS = ("upi", "credit_card", "debit_card", "cash", "wallet", "pay_later")
CUSTOMIZATIONS = ("none", "less_spicy", "extra_spicy", "no_onion", "no_garlic", "extra_cheese")
