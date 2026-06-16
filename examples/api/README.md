# API Examples

Start the API:

```bash
uvicorn invyra_forecasting.api.app:app --reload
```

Then run one of the examples:

```bash
bash examples/api/curl_forecast_item.sh
bash examples/api/curl_batch_forecast.sh
bash examples/api/curl_stockout_risk.sh
bash examples/api/curl_reorder_recommendation.sh
bash examples/api/curl_override_audit.sh
bash examples/api/curl_get_audit_events.sh
bash examples/api/curl_accuracy_evaluate.sh
bash examples/api/curl_get_item_accuracy.sh
```

Windows PowerShell:

```powershell
./examples/api/powershell_forecast_item.ps1
```

These examples call local `127.0.0.1:8000` and use JSON fixtures from `data/sample/api/`.

To test snapshot readback, post a forecast request with `"write_snapshot": true`, copy the returned `snapshot_id`, then call:

```bash
curl "http://127.0.0.1:8000/snapshots/<snapshot_id>"
```
