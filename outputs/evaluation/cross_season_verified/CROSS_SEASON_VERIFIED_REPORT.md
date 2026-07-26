# Eco-Loop Verified Cross-Season Evaluation Report

## Verified Controller Metadata
- **Controller Version:** `policy_iter1_frozen`
- **Code SHA-256 Hash:** `8fff6166d3b9eb23`
- **Cross-Season AI Execution Status:** `VERIFIED`

## Verified Cross-Season Performance Table

| Season | Controller Executed | Decisions Count | Outdoor Mean (°C) | Baseline Site (kWh-eq) | AI Site (kWh-eq) | Site Reduction % | Baseline Comfort % | AI Comfort % | Comfort Delta |
|---|---|---|---|---|---|---|---|---|---|
| **Winter (Jan 21-23)** | `True` | `51` | `0.4°C` | `731.60` | `731.60` | **`+0.00%`** | `30.9%` | `30.9%` | `+0.0%` |
| **Shoulder (May 15-17)** | `True` | `51` | `11.5°C` | `268.15` | `268.15` | **`+0.00%`** | `0.0%` | `0.0%` | `+0.0%` |
| **Summer (Jul 21-23)** | `True` | `51` | `24.1°C` | `432.01` | `432.01` | **`+0.00%`** | `100.0%` | `100.0%` | `+0.0%` |
| **AGGREGATE (9 DAYS)** | **`True`** | **`153`** | **`12.0°C`** | **`1431.76`** | **`1431.76`** | **`+0.00%`** | **`47.5%`** | **`47.5%`** | **`+0.0%`** |

## Fuel Breakdown Audit

| Fuel Type | Baseline Consumption | AI Controlled Consumption | Aggregate Reduction % |
|---|---|---|---|
| **Electricity** | `1054.62 kWh` | `1054.62 kWh` | **`+0.00%`** |
| **Natural Gas Heating** | `377.15 kWh-eq` | `377.15 kWh-eq` | **`+0.00%`** |
| **TOTAL SITE ENERGY** | `1431.76 kWh-eq` | `1431.76 kWh-eq` | **`+0.00%`** |
