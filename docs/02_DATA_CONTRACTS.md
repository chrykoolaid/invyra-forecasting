# Data Contracts

## Inputs

Item: `item_id`, `sku`, `name`, `category`, `unit_of_measure`, `minimum_order_quantity`.

Location: `location_id`, `name`, `location_type`.

Stock Position: `item_id`, `location_id`, `on_hand`, `reserved`, `environment`.

Stock Movement: `movement_id`, `item_id`, `location_id`, `movement_date`, `movement_type`, `quantity`, `environment`.

Sales-equivalent movement types: `SALE`, `POS_SALE`, `WASTAGE`, `MARKDOWN_SALE`, `TRANSFER_OUT`, `ADJUSTMENT_OUT`.

Supplier Profile: `supplier_id`, `item_id`, `lead_time_days`, `lead_time_variability_days`, `minimum_order_quantity`.

## Outputs

Forecast result, risk result, recommendation result, confidence result, explanation result, audit event, and forecast snapshot.
