# Program C8 — Durable History Read Provider

Program C8 composes the file-backed history and explainability repositories into the existing read-only history query service.

For each active tenant namespace, the provider rebuilds an in-memory history repository, historical index, and explainability archive from durable local files. This gives callers restart-safe read access while preserving tenant isolation and the established C5 query contract.

The provider adds no public API routes, database dependency, authentication, authorization, forecast mutation, or inventory mutation. Forecasting remains advisory-only and read-only. Inventory remains the operational source of truth.
