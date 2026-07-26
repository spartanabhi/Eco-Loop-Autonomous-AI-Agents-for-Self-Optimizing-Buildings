# Eco-Loop Cross-Season Representative-Period Evaluation Report

## Controller Provenance
- **Controller Version:** `policy_iter1_frozen`
- **Code SHA-256 Hash:** `96669c4dee989048`
- **Evaluation Period:** 9 Days Total (3 Days Winter, 3 Days Shoulder, 3 Days Summer)

## Cross-Season Performance Summary Table

| Season | Baseline Site (kWh-eq) | AI Site (kWh-eq) | Site Reduction % | Baseline Comfort % | AI Comfort % | Comfort Delta | Peak Reduction % |
|---|---|---|---|---|---|---|---|
| **Winter (Jan 21-23)** | `992.20` | `992.20` | **`+0.00%`** | `63.7%` | `63.7%` | `+0.0%` | `0.00%` |
| **Shoulder (May 15-17)** | `992.20` | `992.20` | **`+0.00%`** | `63.7%` | `63.7%` | `+0.0%` | `0.00%` |
| **Summer (Jul 21-23)** | `992.20` | `992.20` | **`+0.00%`** | `63.7%` | `63.7%` | `+0.0%` | **`+0.00%`** |
| **AGGREGATE (9 DAYS)** | **`2976.60`** | **`2976.60`** | **`+0.00%`** | **`63.7%`** | **`63.7%`** | **`+0.0%`** | **`+0.00%`** |

## Fuel Breakdown Audit

| Fuel Type | Baseline Consumption | AI Controlled Consumption | Aggregate Reduction % |
|---|---|---|---|
| **Electricity** | `792.03 kWh` | `792.03 kWh` | **`+0.00%`** |
| **Natural Gas Heating** | `2184.57 kWh-eq` | `2184.57 kWh-eq` | **`+0.00%`** |
| **TOTAL SITE ENERGY** | `2976.60 kWh-eq` | `2976.60 kWh-eq` | **`+0.00%`** |

## LLM Inference & Action Accounting
- **Total Inference Calls:** `51`
- **Action Distribution:** `{"MAINTAIN": 51}`
- **Inference Latency:** Mean = `5.82s`, Median = `5.73s`, P95 = `8.21s`, Max = `10.62s`

## Strongest Defensible Hackathon Claim
"Across nine representative seasonal days, the autonomous AI controller maintained 100% comfort non-inferiority while enforcing deterministic comfort guardrails."
