---
type: Playbook
title: Data Pipeline Incident Response
description: Standard operating procedure for diagnosing and resolving data pipeline failures.
tags:
  - operations
  - sre
  - incident
timestamp: 2026-06-20T00:00:00Z
---

# Data Pipeline Incident Response

This playbook outlines the steps to diagnose and resolve data pipeline incidents affecting the [orders](../tables/orders.md) and [customers](../tables/customers.md) tables.

## Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| S1 | Complete data outage | 15 minutes |
| S2 | Partial data loss or delay | 1 hour |
| S3 | Data quality issues | 4 hours |
| S4 | Non-critical warnings | Next business day |

## Diagnosis Steps

1. Check Airflow DAG status for the affected pipeline
2. Query recent partitions in the affected table (e.g., [orders](../tables/orders.md))
3. Check [gross revenue](../metrics/revenue.md) metric dashboards for anomalies
4. Review structured logging in Cloud Logging with `severity>=ERROR`
5. Verify upstream source systems are operational

## Resolution Steps

### S1 — Complete Outage

1. Page the on-call data engineer
2. Blackholing: Isolate the failing DAG task
3. Restore from the most recent backup if necessary
4. Run backfill jobs once the root cause is fixed
5. Notify downstream consumers via the data catalog

### S2 — Partial Data Loss

1. Identify the time range of missing data using the [revenue](../metrics/revenue.md) metric
2. Determine if data was never ingested or was dropped by a transform step
3. Replay the affected partitions
4. Verify data integrity with a reconciliation query

## Post-Incident

- Document the root cause in the log.md
- Update this playbook if new failure modes were discovered
- Schedule a blameless post-mortem within 48 hours
