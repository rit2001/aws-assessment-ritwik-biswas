"""Visible, reviewable SQL used by both tests and the local service."""

TOP_PRODUCTS = """
SELECT product_id, product_name, ROUND(SUM(revenue), 2) AS total_revenue
FROM sales
GROUP BY product_id, product_name
ORDER BY total_revenue DESC, product_name ASC
LIMIT ?
"""

REVENUE_BY_REGION = """
SELECT region, ROUND(SUM(revenue), 2) AS total_revenue
FROM sales
GROUP BY region
ORDER BY total_revenue DESC, region ASC
"""

LATEST_DATE = "SELECT MAX(order_date) AS latest_date FROM sales"

BEST_CATEGORY_PREVIOUS_7_DAYS = """
WITH bounds AS (
    SELECT MAX(order_date) AS latest_date FROM sales
)
SELECT category, ROUND(SUM(revenue), 2) AS total_revenue
FROM sales, bounds
WHERE order_date >= date(bounds.latest_date, '-7 days')
  AND order_date < bounds.latest_date
GROUP BY category
ORDER BY total_revenue DESC, category ASC
LIMIT 1
"""
