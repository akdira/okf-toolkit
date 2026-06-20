---
type: BigQuery Table
title: orders
description: Core e-commerce orders table containing order headers and item-level detail.
resource: bigquery://acme-prod/analytics/orders
tags:
  - ecommerce
  - core
  - transactional
timestamp: 2026-06-20T00:00:00Z
---

# orders

The `orders` table is the central transactional table for the Acme Corp e-commerce platform. Each row represents a single line item within an order.

## Schema

| Column | Type | Description |
|--------|------|-------------|
| order_id | STRING | Unique order identifier |
| customer_id | STRING | Foreign key to [customers](customers.md) |
| order_date | TIMESTAMP | When the order was placed |
| item_id | STRING | Product identifier |
| item_name | STRING | Human-readable product name |
| quantity | INT64 | Number of units purchased |
| unit_price | NUMERIC | Price per unit in USD |
| total_line | NUMERIC | Computed: quantity × unit_price |
| status | STRING | Order status (pending, shipped, delivered, cancelled) |

## Partitioning

- Partitioned by `order_date` (daily)
- Clustered by `customer_id`

## Usage Notes

- Always filter by `order_date` to avoid full scans
- The `customer_id` field joins to [customers](customers.md) for profile enrichment
- Sensitive columns (PII) should be masked via BigQuery column-level security
