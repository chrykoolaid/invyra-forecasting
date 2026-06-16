# Architecture

The Invyra Forecasting Engine is a Python-first core engine with an optional FastAPI integration layer.

```text
Invyra modules
  ├─ Inventory
  ├─ ScanOps
  ├─ Reorder Review
  ├─ Purchasing
  ├─ Suppliers
  ├─ Dashboard
  └─ Reports
        │
        ▼
Optional FastAPI Layer
        │
        ▼
Forecasting Service
        │
        ├─ Data validation
        ├─ Feature calculation
        ├─ Simple forecast models
        ├─ Risk scoring
        ├─ Confidence scoring
        ├─ Recommendation logic
        ├─ Explanation builder
        ├─ Snapshot writer
        └─ Audit logger
```

Core areas: `schemas`, `data`, `features`, `models`, `risk`, `recommendations`, `confidence`, `explanation`, `audit`, `services`, `api`, `jobs`, and `utils`.

Design rules: core works without API; API has no business logic; forecasting does not mutate stock; no automatic purchasing; all recommendations need explanations; low confidence is shown honestly; LIVE/TRAINING/TEST separation is first-class.
