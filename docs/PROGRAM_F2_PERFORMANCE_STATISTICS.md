# Program F2 — Performance Statistics

## Purpose

Program F2 derives read-only model performance statistics from existing forecast-evaluation results, but only when the corresponding Program E evidence passes the locked E7 ranking-evidence eligibility policy.

## Statistics

- eligible evaluation count
- mean absolute error (MAE)
- root mean squared error (RMSE)
- mean absolute percentage error (MAPE), where defined
- average bias
- average accuracy score
- average calibration gap
- optional forecast-horizon-specific summaries

## Governance

F2 joins certified evidence to the immutable F1 model/version registry and validates model, evaluation, forecast and horizon identities. Uncertified, partial, censored, incomplete or missing evidence does not contribute.

F2 does not persist mutations, rank models, select models, assign weights, alter lifecycle status, retrain models or change forecast generation. Forecasting remains advisory-only and Inventory remains the operational source of truth.
