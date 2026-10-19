-- QUERY: monthly
SELECT
    month,
    COUNT(*) AS orders,
    SUM(is_completed) AS completed_orders,
    SUM(is_return) AS returned_orders,
    ROUND(SUM(CASE WHEN status = 'delivered' THEN amount ELSE 0 END), 2) AS net_revenue,
    ROUND(1.0 * SUM(is_return) / NULLIF(SUM(is_completed), 0), 4) AS return_rate,
    ROUND(1.0 * SUM(is_late) / NULLIF(SUM(is_completed), 0), 4) AS late_rate
FROM orders
GROUP BY month
ORDER BY month;

-- QUERY: categories
SELECT
    category,
    SUM(is_completed) AS completed_orders,
    SUM(is_return) AS returned_orders,
    ROUND(SUM(CASE WHEN status = 'delivered' THEN amount ELSE 0 END), 2) AS net_revenue,
    ROUND(1.0 * SUM(is_return) / NULLIF(SUM(is_completed), 0), 4) AS return_rate
FROM orders
GROUP BY category
ORDER BY net_revenue DESC;

-- QUERY: regions
SELECT
    region,
    SUM(is_completed) AS completed_orders,
    ROUND(SUM(CASE WHEN status = 'delivered' THEN amount ELSE 0 END), 2) AS net_revenue,
    ROUND(1.0 * SUM(is_late) / NULLIF(SUM(is_completed), 0), 4) AS late_rate
FROM orders
GROUP BY region
ORDER BY net_revenue DESC;

-- QUERY: channels
SELECT
    channel,
    SUM(is_completed) AS completed_orders,
    ROUND(SUM(CASE WHEN status = 'delivered' THEN amount ELSE 0 END), 2) AS net_revenue,
    ROUND(1.0 * SUM(is_return) / NULLIF(SUM(is_completed), 0), 4) AS return_rate
FROM orders
GROUP BY channel
ORDER BY net_revenue DESC;
