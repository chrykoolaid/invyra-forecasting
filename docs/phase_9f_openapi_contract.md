# Phase 9F — Read-Only OpenAPI Contract

## Status

Phase 9F documents the read-only Forecast Decision Review API contract for downstream consumers.

This phase is documentation-only. It does not add runtime behavior, mutation behavior, or new forecasting logic.

## API Title

```text
Invyra Forecast Decision Review API
```

## API Version

```text
9A.1
```

## OpenAPI-Style Summary

```yaml
openapi: 3.1.0
info:
  title: Invyra Forecast Decision Review API
  version: 9A.1
  description: Read-only advisory API for Forecast Decision Review dashboard and export projections.
paths:
  /forecast/decision-review/dashboard:
    get:
      summary: Get decision review dashboard projection
      operationId: getDecisionReviewDashboard
      tags:
        - forecast-decision-review
      responses:
        '200':
          description: Read-only decision review dashboard projection
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DecisionReviewApiResponse'
  /forecast/decision-review/export:
    get:
      summary: Get decision review export bundle projection
      operationId: getDecisionReviewExport
      tags:
        - forecast-decision-review
      parameters:
        - name: export_format
          in: query
          required: false
          schema:
            type: string
            enum:
              - json
              - dict
            default: json
      responses:
        '200':
          description: Read-only decision review export bundle projection
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DecisionReviewExportBundle'
        '400':
          description: Unsupported export format validation response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidationErrorResponse'
components:
  schemas:
    GovernanceFlags:
      type: object
      required:
        - advisory_only
        - read_only
        - inventory_source_of_truth_preserved
      properties:
        advisory_only:
          type: boolean
          const: true
        read_only:
          type: boolean
          const: true
        inventory_source_of_truth_preserved:
          type: boolean
          const: true
    DecisionReviewApiResponse:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - response_version
            - dashboard
            - generated_at
          properties:
            response_version:
              type: string
              example: 8H.1
            dashboard:
              $ref: '#/components/schemas/DecisionReviewDashboardProjection'
            generated_at:
              type: string
              format: date-time
    DecisionReviewDashboardProjection:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - summary
            - snapshot
            - generated_at
          properties:
            summary:
              $ref: '#/components/schemas/DecisionReviewSummary'
            snapshot:
              $ref: '#/components/schemas/DecisionReviewQueueSnapshot'
            generated_at:
              type: string
              format: date-time
    DecisionReviewSummary:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - total_count
            - ready_count
            - pending_count
            - needs_more_evidence_count
            - high_priority_count
            - medium_priority_count
            - normal_priority_count
          properties:
            total_count:
              type: integer
            ready_count:
              type: integer
            pending_count:
              type: integer
            needs_more_evidence_count:
              type: integer
            high_priority_count:
              type: integer
            medium_priority_count:
              type: integer
            normal_priority_count:
              type: integer
    DecisionReviewQueueSnapshot:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - total_count
            - items
          properties:
            total_count:
              type: integer
            items:
              type: array
              items:
                type: object
                additionalProperties: true
    DecisionReviewExportBundle:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - bundle_version
            - ready_for_delivery
            - export
            - manifest
            - validation
            - generated_at
          properties:
            bundle_version:
              type: string
              example: 8L.1
            ready_for_delivery:
              type: boolean
            export:
              $ref: '#/components/schemas/DecisionReviewExportProjection'
            manifest:
              $ref: '#/components/schemas/DecisionReviewExportManifest'
            validation:
              $ref: '#/components/schemas/DecisionReviewExportValidationResult'
            generated_at:
              type: string
              format: date-time
    DecisionReviewExportProjection:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - export_format
            - export_version
            - response
            - generated_at
          properties:
            export_format:
              type: string
              enum:
                - json
                - dict
            export_version:
              type: string
              example: 8I.1
            response:
              $ref: '#/components/schemas/DecisionReviewApiResponse'
            generated_at:
              type: string
              format: date-time
    DecisionReviewExportManifest:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - manifest_version
            - export
            - record_count
            - generated_at
          properties:
            manifest_version:
              type: string
              example: 8J.1
            export:
              $ref: '#/components/schemas/DecisionReviewExportProjection'
            record_count:
              type: integer
            generated_at:
              type: string
              format: date-time
    DecisionReviewExportValidationResult:
      allOf:
        - $ref: '#/components/schemas/GovernanceFlags'
        - type: object
          required:
            - valid
            - warnings
            - validation_version
            - generated_at
          properties:
            valid:
              type: boolean
            warnings:
              type: array
              items:
                type: string
            validation_version:
              type: string
              example: 8K.1
            generated_at:
              type: string
              format: date-time
    ValidationErrorResponse:
      type: object
      required:
        - detail
      properties:
        detail:
          type: string
          example: Unsupported decision review export format
```

## Contract Notes

This document mirrors the currently locked read-only response shapes exposed by the Phase 9A endpoint adapter.

Clients should treat the schema as additive-compatible:

- required fields should remain available
- optional fields may be added later
- unknown fields should be ignored by compatible clients
- governance flags must remain present and true

## Runtime Endpoint Source

The documented endpoint adapter is implemented in:

```text
src/invyra_forecasting/decision_review_endpoints.py
```

## Test Coverage

Relevant compatibility coverage is provided by:

```text
tests/test_phase_9a_decision_review_endpoints.py
tests/test_phase_9d_api_adapter_compatibility.py
tests/test_phase_9e_api_stability_versioning.py
```

## Governance Lock

The OpenAPI-style contract remains:

- advisory-only
- read-only
- projection-only
- safe for downstream UI/Desktop/API consumers

It does not define or imply:

- inventory mutation
- stock movement creation
- purchase order creation
- purchase order approval
- export file writing
- export data transmission
- ledger override

Inventory remains the source of truth.
