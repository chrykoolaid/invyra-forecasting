# ADR-0001 — Python-First Forecasting Engine

## Status

Accepted

## Context

Invyra needs a forecasting engine that can eventually support enterprise-grade forecasting across Inventory, ScanOps, Purchasing, Suppliers, Dashboard, Reports, POS, CRM, and future planning workflows.

The engine must remain explainable and commercially usable in Phase 1. It must not start as an overbuilt AI platform.

## Decision

Build the forecasting engine as a Python-first core package with an optional FastAPI integration layer.

The core engine must run directly in Python without requiring API startup.

## Rationale

Python is well suited for forecasting, analytics, statistical modeling, and future ML/MLOps expansion. Keeping the API separate prevents business logic from drifting into endpoint handlers.

## Consequences

Positive: clean service boundaries, easy local testing, API-ready integration, future ML-ready architecture, lower Phase 1 complexity.

Tradeoffs: disciplined schema governance, environment separation, and future integration wrappers are required.
