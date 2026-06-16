Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/forecasts/item" `
  -ContentType "application/json" `
  -InFile "data/sample/api/forecast_item_request.json"
