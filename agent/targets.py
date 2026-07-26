"""
Agent Targets & Benchmark Thresholds.
Defines comfort (PMV), peak electricity demand, and indoor air quality (CO2) target evaluations.
"""

from dataclasses import dataclass

@dataclass
class ComfortTarget:
    """ASHRAE 55 Thermal Comfort Target based on Fanger PMV."""
    MIN_PMV: float = -0.5
    MAX_PMV: float = +0.5

    def evaluate_pmv(self, pmv: float) -> str:
        """Categorizes PMV into COMFORTABLE, TOO_COLD, or TOO_HOT."""
        if pmv < self.MIN_PMV:
            return "TOO_COLD"
        elif pmv > self.MAX_PMV:
            return "TOO_HOT"
        return "COMFORTABLE"

@dataclass
class PeakDemandTarget:
    """
    Facility Peak Electricity Demand Target for DOE Small Office Reference Building.
    Baseline peak for 511 m² small office is ~12-18 kW.
    Default threshold set to 15.0 kW.
    """
    PEAK_THRESHOLD_KW: float = 15.0  # kW
    NEAR_LIMIT_THRESHOLD_KW: float = 12.0  # kW

    def evaluate_demand(self, demand_kw: float) -> str:
        """Categorizes electricity demand into NORMAL, NEAR_LIMIT, or ABOVE_LIMIT."""
        if demand_kw >= self.PEAK_THRESHOLD_KW:
            return "ABOVE_LIMIT"
        elif demand_kw >= self.NEAR_LIMIT_THRESHOLD_KW:
            return "NEAR_LIMIT"
        return "NORMAL"

@dataclass
class IndoorAirQualityTarget:
    """ASHRAE 62.1 Indoor Air Quality CO2 Target."""
    CO2_THRESHOLD_PPM: float = 1000.0  # ppm

    def evaluate_co2(self, co2_ppm: float) -> str:
        """Categorizes CO2 into GOOD, ELEVATED, or HIGH."""
        if co2_ppm > self.CO2_THRESHOLD_PPM:
            return "HIGH"
        elif co2_ppm >= 800.0:
            return "ELEVATED"
        return "GOOD"
