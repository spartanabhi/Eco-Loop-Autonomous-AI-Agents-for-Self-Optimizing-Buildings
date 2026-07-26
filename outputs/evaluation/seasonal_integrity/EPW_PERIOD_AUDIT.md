# EPW Direct Weather File Period Audit

## Target Weather File: `weather/weather.epw` (Chicago O'Hare TMY3)

| Period | Record Count | Min Outdoor Temp (°C) | Mean Outdoor Temp (°C) | Max Outdoor Temp (°C) |
|---|---|---|---|---|
| **Winter (Jan 21-23)** | `72` | `-8.3 °C` | `0.3 °C` | `12.2 °C` |
| **Shoulder (May 15-17)** | `72` | `5.6 °C` | `11.5 °C` | `16.7 °C` |
| **Summer (Jul 21-23)** | `72` | `17.8 °C` | `24.1 °C` | `31.1 °C` |

## Audit Summary
Direct parsing of `weather/weather.epw` proves that Chicago outdoor weather differs significantly between seasons:
- Winter mean outdoor drybulb: **0.3 °C** (min: -8.3 °C, max: 12.2 °C)
- Shoulder mean outdoor drybulb: **11.5 °C** (min: 5.6 °C, max: 16.7 °C)
- Summer mean outdoor drybulb: **24.1 °C** (min: 17.8 °C, max: 31.1 °C)
