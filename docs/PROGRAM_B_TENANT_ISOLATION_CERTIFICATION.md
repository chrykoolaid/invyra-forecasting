# Program B Tenant Isolation Certification

## Scope

This record certifies the tenant-governance capabilities delivered through Program B1 and Program B2.1–B2.5.

Certified surfaces:

- request-scoped tenant context
- internal namespace normalization
- tenant-aware snapshot isolation
- tenant-aware monitoring metrics
- tenant-aware review context
- default-namespace backward compatibility
- advisory-only and read-only guardrails

## Isolation Model

The optional `X-Tenant-Id` header establishes request-scoped tenant context.

- Missing, blank, or whitespace-only values resolve to the `default` namespace.
- Named tenant identifiers are normalized by trimming surrounding whitespace.
- Request context uses `ContextVar` and is reset after request completion.
- Snapshot storage, monitoring metrics, and review context resolve the active namespace internally.
- Identical resource identifiers may exist independently in separate namespaces.

## Backward Compatibility

Clients that do not send `X-Tenant-Id` continue to use the `default` namespace.

Default snapshot files retain the legacy root-directory layout. No public request or response schema was changed by Program B2.

## Guardrails

Program B does not introduce:

- inventory mutation
- stock movements
- purchase-order creation or approval
- authentication or authorization
- tenant provisioning or billing
- forecast-algorithm changes
- confidence, ranking, explainability, or evidence-generation changes

Inventory remains the operational system of record. Forecasting remains advisory-only and read-only.

## Certification Evidence

Automated regression coverage verifies:

1. namespace normalization and request isolation
2. snapshot invisibility across tenants
3. metrics invisibility across tenants
4. review-context invisibility across tenants
5. shared identifier safety across isolated namespaces
6. default-namespace compatibility
7. concurrent `ContextVar` isolation
8. preservation of advisory-only, read-only, and source-of-truth guardrails

The GitHub CI workflow must pass before the B2.5 certification PR is merged.

## Known Boundaries

This certification covers logical isolation inside the current local and in-memory implementations. It does not certify external identity management, authentication, authorization, tenant provisioning, distributed storage, or cross-process tenancy. Those remain separate future hardening concerns.

## Certification Result

Program B is certified complete when the B2.5 regression suite and the full repository CI workflow pass and the certification PR is merged into `main`.
