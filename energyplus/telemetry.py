"""
Live EnergyPlus Telemetry Module.
Manages API handle registration, live metric acquisition during callbacks,
data structure representation, telemetry snapshot history, and outdoor weather tracking.
Includes fuel breakdown (Electricity + Natural Gas), HVAC thermal mode determination,
and strict seasonal calendar assertions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import csv

@dataclass
class TelemetrySnapshot:
    """Dataclass holding live telemetry data captured during simulation execution."""
    run_id: str
    season: str
    controller_version: str
    callback_index: int
    simulation_time: str
    month: int
    day: int
    hour: int
    minute: int
    outdoor_drybulb_c: float                # Outdoor Air Temperature (°C)
    outdoor_rh_pct: float                   # Outdoor Air Relative Humidity (%)
    zone_temperatures: Dict[str, float]      # {zone_name: temp_C}
    zone_co2: Dict[str, float]               # {zone_name: co2_ppm}
    zone_pmv: Dict[str, float]               # {zone_name: pmv_index}
    zone_occupancy: Dict[str, float]         # {zone_name: occupant_count}
    occupancy_source: str                    # "ENERGYPLUS" or "FALLBACK"
    facility_electricity_joules: float       # Raw EnergyPlus electricity meter interval energy (J)
    facility_electricity_kwh: float          # Calculated electricity interval kWh (Joules / 3,600,000)
    facility_demand_kw: float                # Calculated interval demand kW (Joules / 900,000)
    facility_gas_joules: float               # Raw EnergyPlus natural gas meter interval energy (J)
    facility_gas_kwh_eq: float               # Calculated natural gas kWh-equivalent (Joules / 3,600,000)
    total_site_energy_kwh_eq: float          # Electricity kWh + Natural Gas kWh-eq
    hvac_mode: str                           # "HEATING", "COOLING", or "DEADBAND"

class TelemetryManager:
    """Manages EnergyPlus exchange API variable/meter handles and live snapshots."""

    ZONES = ["CORE_ZN", "PERIMETER_ZN_1", "PERIMETER_ZN_2", "PERIMETER_ZN_3", "PERIMETER_ZN_4"]

    def __init__(self, run_id: str = "default_run", season: str = "winter", controller_version: str = "policy_iter1_frozen"):
        self.run_id = run_id
        self.season = season.lower()
        self.controller_version = controller_version
        self.callback_counter: int = 0
        self.handles_initialized: bool = False
        
        # Weather Handles
        self.outdoor_temp_handle: int = -1
        self.outdoor_rh_handle: int = -1

        # Variable Handles
        self.temp_handles: Dict[str, int] = {}
        self.co2_handles: Dict[str, int] = {}
        self.pmv_handles: Dict[str, int] = {}
        self.occ_handles: Dict[str, int] = {}
        
        # Meter Handles
        self.electricity_meter_handle: int = -1
        self.gas_meter_handle: int = -1

        # History
        self.snapshots: List[TelemetrySnapshot] = []

    def initialize_handles(self, api: Any, state: Any) -> bool:
        """Dynamically retrieves variable and meter handles from active EnergyPlus state."""
        if not api.exchange.api_data_fully_ready(state):
            return False

        # 0. Outdoor Weather Handles
        self.outdoor_temp_handle = api.exchange.get_variable_handle(state, "Site Outdoor Air Drybulb Temperature", "Environment")
        self.outdoor_rh_handle = api.exchange.get_variable_handle(state, "Site Outdoor Air Relative Humidity", "Environment")

        # 1. Zone Mean Air Temperature Handles
        for z in self.ZONES:
            h = api.exchange.get_variable_handle(state, "Zone Mean Air Temperature", z)
            if h != -1:
                self.temp_handles[z] = h

        # 2. Zone Air CO2 Concentration Handles
        for z in self.ZONES:
            h = api.exchange.get_variable_handle(state, "Zone Air CO2 Concentration", z)
            if h != -1:
                self.co2_handles[z] = h

        # 3. Zone Thermal Comfort Fanger Model PMV Handles
        for z in self.ZONES:
            people_key = f"{z} PEOPLE"
            h = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", people_key)
            if h == -1:
                h = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", z)
            if h != -1:
                self.pmv_handles[z] = h

        # 4. Zone People Occupant Count Handles
        for z in self.ZONES:
            h = api.exchange.get_variable_handle(state, "Zone People Occupant Count", z)
            if h != -1:
                self.occ_handles[z] = h

        # 5. Electricity Meter Handle
        self.electricity_meter_handle = api.exchange.get_meter_handle(state, "Electricity:Building")
        if self.electricity_meter_handle == -1:
            self.electricity_meter_handle = api.exchange.get_meter_handle(state, "Electricity:Facility")

        # 6. Natural Gas Meter Handle
        self.gas_meter_handle = api.exchange.get_meter_handle(state, "NaturalGas:Facility")

        self.handles_initialized = bool(self.temp_handles and self.electricity_meter_handle != -1)
        return self.handles_initialized

    def capture_snapshot(self, api: Any, state: Any) -> Optional[TelemetrySnapshot]:
        """Captures a TelemetrySnapshot from active EnergyPlus callback state."""
        if api.exchange.warmup_flag(state):
            return None

        if not self.handles_initialized:
            if not self.initialize_handles(api, state):
                return None

        self.callback_counter += 1

        month = int(api.exchange.month(state))
        day = int(api.exchange.day_of_month(state))
        raw_hr = int(api.exchange.hour(state))
        raw_min = int(api.exchange.minutes(state))

        # Strict Seasonal Calendar Assertion
        expected_months = {"winter": 1, "shoulder": 5, "summer": 7}
        if self.season in expected_months:
            expected_m = expected_months[self.season]
            if month != expected_m:
                raise ValueError(f"Calendar Integrity Violation! Season '{self.season}' expected month {expected_m}, but EnergyPlus reported month {month}!")

        # Normalize timestamp format to valid HH:MM (00 <= MM <= 59, 00 <= HH <= 23)
        add_hrs = raw_min // 60
        norm_min = raw_min % 60
        norm_hr = (raw_hr + add_hrs) % 24

        sim_time_str = f"Day {day:02d}/{month:02d} {norm_hr:02d}:{norm_min:02d}"

        # Outdoor Weather Telemetry
        outdoor_temp = 20.0
        if self.outdoor_temp_handle != -1:
            outdoor_temp = api.exchange.get_variable_value(state, self.outdoor_temp_handle)

        outdoor_rh = 50.0
        if self.outdoor_rh_handle != -1:
            outdoor_rh = api.exchange.get_variable_value(state, self.outdoor_rh_handle)

        temps: Dict[str, float] = {}
        co2s: Dict[str, float] = {}
        pmvs: Dict[str, float] = {}
        occs: Dict[str, float] = {}

        for z in self.ZONES:
            h_t = self.temp_handles.get(z, -1)
            if h_t != -1:
                temps[z] = api.exchange.get_variable_value(state, h_t)

            h_c = self.co2_handles.get(z, -1)
            if h_c != -1:
                co2s[z] = api.exchange.get_variable_value(state, h_c)

            h_p = self.pmv_handles.get(z, -1)
            if h_p != -1:
                pmvs[z] = api.exchange.get_variable_value(state, h_p)

            h_o = self.occ_handles.get(z, -1)
            if h_o != -1:
                occs[z] = api.exchange.get_variable_value(state, h_o)
            else:
                occs[z] = 0.0

        # Electricity Meter
        elec_joules = 0.0
        if self.electricity_meter_handle != -1:
            elec_joules = api.exchange.get_meter_value(state, self.electricity_meter_handle)
        
        elec_kwh = elec_joules / 3600000.0
        demand_kw = elec_joules / 900000.0 if elec_joules > 0 else 0.0

        # Natural Gas Meter
        gas_joules = 0.0
        if self.gas_meter_handle != -1:
            gas_joules = api.exchange.get_meter_value(state, self.gas_meter_handle)
        
        gas_kwh_eq = gas_joules / 3600000.0
        total_site_kwh_eq = elec_kwh + gas_kwh_eq

        # HVAC Mode Determination (based on CORE_ZN temp relative to baseline setpoints 21.0°C / 24.0°C)
        core_temp = temps.get("CORE_ZN", 21.0)
        if core_temp <= 21.0 + 0.2 and gas_joules > 0:
            hvac_mode = "HEATING"
        elif core_temp >= 24.0 - 0.2:
            hvac_mode = "COOLING"
        else:
            hvac_mode = "DEADBAND"

        snapshot = TelemetrySnapshot(
            run_id=self.run_id,
            season=self.season,
            controller_version=self.controller_version,
            callback_index=self.callback_counter,
            simulation_time=sim_time_str,
            month=month,
            day=day,
            hour=norm_hr,
            minute=norm_min,
            outdoor_drybulb_c=outdoor_temp,
            outdoor_rh_pct=outdoor_rh,
            zone_temperatures=temps,
            zone_co2=co2s,
            zone_pmv=pmvs,
            zone_occupancy=occs,
            occupancy_source="ENERGYPLUS" if self.occ_handles else "FALLBACK",
            facility_electricity_joules=elec_joules,
            facility_electricity_kwh=elec_kwh,
            facility_demand_kw=demand_kw,
            facility_gas_joules=gas_joules,
            facility_gas_kwh_eq=gas_kwh_eq,
            total_site_energy_kwh_eq=total_site_kwh_eq,
            hvac_mode=hvac_mode
        )

        self.snapshots.append(snapshot)
        return snapshot

    def save_telemetry_csv(self, file_path: str) -> None:
        """Saves captured callback telemetry snapshots to CSV."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self.snapshots:
            return

        fieldnames = [
            "run_id", "season", "controller_version", "callback_index", "simulation_time",
            "sim_month", "sim_day", "sim_hour", "sim_minute", "outdoor_drybulb_c", "outdoor_rh_pct",
            "core_zn_temp", "core_zn_co2", "core_zn_pmv", "core_zn_occ", "occupancy_source",
            "perimeter_zn_1_temp", "perimeter_zn_2_temp", "perimeter_zn_3_temp", "perimeter_zn_4_temp",
            "electricity_meter_joules", "electricity_meter_kwh", "facility_demand_kw",
            "gas_meter_joules", "gas_meter_kwh_eq", "total_site_energy_kwh_eq", "hvac_mode"
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for s in self.snapshots:
                writer.writerow([
                    s.run_id, s.season, s.controller_version, s.callback_index, s.simulation_time,
                    s.month, s.day, s.hour, s.minute, f"{s.outdoor_drybulb_c:.2f}", f"{s.outdoor_rh_pct:.1f}",
                    f"{s.zone_temperatures.get('CORE_ZN', 0.0):.2f}",
                    f"{s.zone_co2.get('CORE_ZN', 0.0):.1f}",
                    f"{s.zone_pmv.get('CORE_ZN', 0.0):.2f}",
                    f"{s.zone_occupancy.get('CORE_ZN', 0.0):.1f}",
                    s.occupancy_source,
                    f"{s.zone_temperatures.get('PERIMETER_ZN_1', 0.0):.2f}",
                    f"{s.zone_temperatures.get('PERIMETER_ZN_2', 0.0):.2f}",
                    f"{s.zone_temperatures.get('PERIMETER_ZN_3', 0.0):.2f}",
                    f"{s.zone_temperatures.get('PERIMETER_ZN_4', 0.0):.2f}",
                    f"{s.facility_electricity_joules:.2f}",
                    f"{s.facility_electricity_kwh:.4f}",
                    f"{s.facility_demand_kw:.2f}",
                    f"{s.facility_gas_joules:.2f}",
                    f"{s.facility_gas_kwh_eq:.4f}",
                    f"{s.total_site_energy_kwh_eq:.4f}",
                    s.hvac_mode
                ])
