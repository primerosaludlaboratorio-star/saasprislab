# 7. Load Testing Strategy with Locust

Date: 2026-07-10

## Status

Accepted

## Context

As PRISLAB scales in a SaaS environment (Cloud Run + PostgreSQL), ensuring the infrastructure can handle high bursts of concurrent users (e.g., receptionists creating orders during peak morning hours) is critical. We need a reproducible, scriptable, and distributed load testing framework to establish performance baselines.

## Decision

We have decided to adopt **Locust** (`locustfile.py` in `tests/load/`) as our primary load testing tool. 

Locust allows us to:
1. Write user behavior scenarios in pure Python.
2. Simulate realistic user workflows (e.g., fetching catalog -> searching patient -> creating order).
3. Easily scale out to distributed load generation if necessary.

## Consequences

- **Positive:** We can include performance metrics directly in our CI/CD pipelines or run periodic stress tests before major releases.
- **Positive:** Developers can run `locust` locally to test how query optimizations (e.g., `select_related`, Redis caching) improve throughput.
- **Negative:** Maintaining the locust test scripts adds a slight overhead, especially as API endpoints or authentication mechanisms evolve.
