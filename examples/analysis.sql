SELECT
    substr(placed_at, 1, 7) AS month,
    COUNT(*) AS orders,
    ROUND(SUM(CASE WHEN order_status = 'delivered' THEN total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
    ROUND(100.0 * SUM(order_status = 'delivered') / COUNT(*), 2) AS delivery_rate_pct
FROM orders
GROUP BY month
ORDER BY month;

SELECT
    weather,
    traffic,
    ROUND(AVG(actual_delivery_minutes), 2) AS average_delivery_minutes,
    ROUND(100.0 * SUM(actual_delivery_minutes <= promised_minutes) / COUNT(*), 2) AS on_time_rate_pct
FROM orders
WHERE order_status = 'delivered' AND fulfillment_mode = 'delivery'
GROUP BY weather, traffic
ORDER BY weather, traffic;

SELECT
    r.primary_cuisine,
    COUNT(*) AS orders,
    ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN o.total_inr ELSE 0 END), 2) AS delivered_gmv_inr,
    ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.rating END), 2) AS average_rating
FROM orders o
JOIN restaurants r ON r.restaurant_id = o.restaurant_id
GROUP BY r.primary_cuisine
ORDER BY delivered_gmv_inr DESC;
