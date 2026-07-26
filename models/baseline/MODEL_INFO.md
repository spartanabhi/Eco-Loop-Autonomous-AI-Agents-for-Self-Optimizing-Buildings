# Baseline Building Model Documentation

## Model Overview
- **Source Model:** `RefBldgSmallOfficeNew2004_Chicago.idf` (DOE Commercial Reference Building - Small Office)
- **EnergyPlus Version:** 26.1.0
- **Weather File:** `USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw` (Chicago O'Hare TMY3)
- **Building Type:** 1-Story Commercial Small Office (5,500 sq ft / 511 m²)
- **Run Period:** Winter Design Day (`01/21`) to Annual / Evaluation Period

## Key Thermal Zones
1. `Core_ZN` (Core office space)
2. `Perimeter_ZN_1` (Perimeter Zone 1 - South)
3. `Perimeter_ZN_2` (Perimeter Zone 2 - East)
4. `Perimeter_ZN_3` (Perimeter Zone 3 - North)
5. `Perimeter_ZN_4` (Perimeter Zone 4 - West)
6. `Attic` (Unconditioned roof plenum)

## Internal Heat Gains & Occupancy
- **People Objects:** 5 objects (`Core_ZN People`, `Perimeter_ZN_1 People` through `Perimeter_ZN_4 People`)
- **Occupancy Schedule:** `BLDG_OCC_SCH`
- **Activity Schedule:** `ACTIVITY_SCH`

## HVAC & Thermostat System
- **HVAC System:** Packaged Single-Zone Direct Expansion (PSZ-AC / PSZ-HP) per zone
- **Thermostat Objects:** `ZoneControl:Thermostat` linked to `ThermostatSetpoint:DualSetpoint`
- **Heating Setpoint Schedule:** `HTGSETP_SCH` (Default heating setpoint: 21.1 °C occupied / 15.6 °C unoccupied)
- **Cooling Setpoint Schedule:** `CLGSETP_SCH` (Default cooling setpoint: 23.9 °C occupied / 26.7 °C unoccupied)

## Sensor & Metric Reporting Status
- **Zone Temperature:** `[AVAILABLE]` (`Zone Mean Air Temperature` [°C])
- **Energy Consumption:** `[AVAILABLE]` (`Electricity:Facility` [J], `NaturalGas:Facility` [J], `Fans:Electricity` [J])
- **Thermal Comfort (PMV):** `[AVAILABLE]` (`Zone Thermal Comfort Fanger Model PMV` [-])
- **Indoor Air Quality (IAQ/CO2):** `[REQUIRES CONFIGURATION]` (Requires `ZoneAirContaminantBalance` object and CO2 generation rates)

## Future PyEnergyPlus Live Control Path
To execute live, real-time closed-loop setpoint overrides in PyEnergyPlus callbacks during active simulation:
- **Primary Mechanism:** Actuator schedule override
  - **Component Type:** `Schedule:Compact`
  - **Control Type:** `Schedule Value`
  - **Actuator Keys:** `HTGSETP_SCH` (Heating Setpoint) and `CLGSETP_SCH` (Cooling Setpoint)
- **Alternative Mechanism:** Zone temperature control actuator
  - **Component Type:** `Zone Temperature Control`
  - **Control Type:** `Heating Setpoint` / `Cooling Setpoint`
  - **Actuator Keys:** `Core_ZN`, `Perimeter_ZN_1`, `Perimeter_ZN_2`, `Perimeter_ZN_3`, `Perimeter_ZN_4`
