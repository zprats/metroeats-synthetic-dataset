# MetroEats data dictionary

All timestamps are ISO 8601 values in `Asia/Kolkata` with an explicit `+05:30` offset. Monetary values are in Indian rupees. Empty CSV fields represent values that are not applicable, not zero.

## `restaurants.csv`

| Column | Type | Meaning |
| --- | --- | --- |
| `restaurant_id` | text | Stable restaurant-location key |
| `restaurant_name` | text | Synthetic storefront or chain name |
| `city` | category | Marketplace city |
| `zone` | category | Operating neighborhood |
| `primary_cuisine` | category | Main menu classification |
| `secondary_cuisine` | category | Secondary menu classification |
| `price_band` | integer | Relative price tier from 1 to 4 |
| `avg_item_price_inr` | number | Representative listed item price |
| `avg_prep_minutes` | integer | Baseline preparation time |
| `service_rating` | number | Historical service-quality score from 1 to 5 |
| `rating_count` | integer | Historical rating volume |
| `onboarded_at` | date | Marketplace onboarding date |
| `is_chain` | boolean | Whether the storefront belongs to a chain |
| `latitude` | number | Synthetic storefront latitude near the city center |
| `longitude` | number | Synthetic storefront longitude near the city center |

## `customers.csv`

| Column | Type | Meaning |
| --- | --- | --- |
| `customer_id` | text | Stable synthetic customer key |
| `signup_date` | date | Marketplace registration date |
| `city` | category | Home marketplace city |
| `home_zone` | category | Home operating neighborhood |
| `acquisition_channel` | category | First-touch acquisition source |
| `loyalty_tier` | category | Membership state: none, silver, gold, or platinum |
| `age_band` | category | Coarse synthetic age segment |
| `preferred_cuisine` | category | Modeled cuisine preference |
| `marketing_opt_in` | boolean | Synthetic consent state |
| `device_type` | category | Primary ordering platform |

## `orders.csv`

| Column | Type | Meaning |
| --- | --- | --- |
| `order_id` | text | Stable order key |
| `customer_id` | text | Foreign key to `customers.csv` |
| `restaurant_id` | text | Foreign key to `restaurants.csv` |
| `city` | category | Fulfillment city |
| `placed_at` | timestamp | Order placement time |
| `order_status` | category | Delivered, customer-cancelled, restaurant-cancelled, or delivery-failed |
| `fulfillment_mode` | category | Delivery or customer pickup |
| `subtotal_inr` | decimal | Sum of item line totals |
| `discount_inr` | decimal | Basket promotion discount |
| `delivery_fee_inr` | decimal | Customer delivery charge |
| `tax_inr` | decimal | Modeled order tax |
| `tip_inr` | decimal | Courier tip |
| `total_inr` | decimal | `subtotal - discount + delivery fee + tax + tip` |
| `promo_code` | category | Applied promotion or `NONE` |
| `distance_km` | number | Store-to-customer route estimate; zero for pickup |
| `weather` | category | Clear, cloudy, rain, heavy rain, or heatwave |
| `traffic` | category | Low, moderate, high, or severe |
| `promised_minutes` | integer | Customer-facing fulfillment promise |
| `actual_delivery_minutes` | integer | Actual completion time for delivered orders |
| `cancellation_reason` | category | Root cause for non-delivered orders |
| `rating` | integer | Post-order rating from 1 to 5 for delivered orders |

## `order_items.csv`

| Column | Type | Meaning |
| --- | --- | --- |
| `order_item_id` | text | Stable order-line key |
| `order_id` | text | Foreign key to `orders.csv` |
| `item_position` | integer | Line position within the order |
| `item_name` | text | Synthetic menu item name |
| `item_category` | category | Menu category |
| `cuisine` | category | Cuisine classification |
| `quantity` | integer | Units ordered |
| `unit_price_inr` | decimal | Price per unit |
| `line_total_inr` | decimal | `quantity × unit price` |
| `is_vegetarian` | boolean | Vegetarian item indicator |
| `customization` | category | Selected preparation customization |

## `payments.csv`

| Column | Type | Meaning |
| --- | --- | --- |
| `payment_id` | text | Stable payment-attempt key |
| `order_id` | text | Unique foreign key to `orders.csv` |
| `payment_method` | category | UPI, card, cash, wallet, or pay-later rail |
| `payment_status` | category | Captured, collected, refunded, failed, voided, or not collected |
| `amount_inr` | decimal | Amount corresponding to the order total |
| `gateway_fee_inr` | decimal | Modeled payment-processing cost |
| `initiated_at` | timestamp | Payment initiation time |
| `settled_at` | timestamp | Settlement or refund completion time |
| `failure_reason` | category | Cause for failed payment attempts |
| `refund_amount_inr` | decimal | Full or partial refund amount |

## `delivery_events.csv`

| Column | Type | Meaning |
| --- | --- | --- |
| `event_id` | text | Stable operational-event key |
| `order_id` | text | Foreign key to `orders.csv` |
| `courier_id` | text | Synthetic courier key; empty for pickup |
| `event_type` | category | Placement, confirmation, assignment, pickup, delivery, or cancellation milestone |
| `event_at` | timestamp | Event occurrence time |
| `latitude` | number | Synthetic event latitude |
| `longitude` | number | Synthetic event longitude |
| `distance_remaining_km` | number | Modeled remaining route distance |
| `event_source` | category | Customer, restaurant, dispatch, or courier system |

## Join paths

- `orders.customer_id = customers.customer_id`
- `orders.restaurant_id = restaurants.restaurant_id`
- `order_items.order_id = orders.order_id`
- `payments.order_id = orders.order_id`
- `delivery_events.order_id = orders.order_id`

## Important interpretation notes

- Delivered GMV should normally include only orders where `order_status = 'delivered'`.
- Non-delivery rate includes every order status other than delivered.
- On-time rate compares `actual_delivery_minutes` with `promised_minutes` for delivered orders only.
- Order discounts exclude free-delivery value because delivery fee waivers are represented directly in `delivery_fee_inr`.
- Geographic coordinates are synthetic approximations and must not be used for routing or real-world location decisions.
