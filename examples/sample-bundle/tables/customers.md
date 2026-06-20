---
type: BigQuery Table
title: customers
description: Customer master data including profiles, segmentation, and lifetime value.
resource: bigquery://acme-prod/analytics/customers
tags:
  - ecommerce
  - core
  - customer
  - pii
timestamp: 2026-06-20T00:00:00Z
---

# customers

The `customers` table contains master customer data used across the Acme Corp analytics ecosystem.

## Schema

| Column | Type | Description |
|--------|------|-------------|
| customer_id | STRING | Primary key |
| email | STRING | Customer email address (PII) |
| first_name | STRING | Given name (PII) |
| last_name | STRING | Family name (PII) |
| signup_date | TIMESTAMP | Account creation date |
| last_active | TIMESTAMP | Most recent interaction timestamp |
| lifetime_value | NUMERIC | Total spend across all orders |
| tier | STRING | Segment label (bronze, silver, gold, platinum) |

## Referenced By

- [orders](orders.md) references `customer_id` as a foreign key

## Security

- Email, first_name, and last_name are classified as PII
- Query access should be restricted to authorized teams via BigQuery row-level security
