"""
Local Carbon Grid Intensity Module.
Provides simulated time-of-day grid carbon intensity state for PoC optimization reasoning.
NOTE: This is a deterministic local simulated schedule for PoC reasoning.
No external API calls or unverified live grid APIs are used.
"""

from dataclasses import dataclass

@dataclass
class CarbonGridState:
    """Represents local grid carbon intensity state at a specific simulation hour."""
    status: str  # "LOW", "MEDIUM", "HIGH"
    intensity_g_co2_kwh: float
    description: str

class CarbonIntensityTracker:
    """Deterministic time-of-day grid carbon intensity tracker."""

    @staticmethod
    def get_carbon_intensity(hour: int) -> CarbonGridState:
        """
        Returns grid carbon intensity state based on simulation hour (0-23).
        - Off-peak night (00:00 - 06:00): LOW carbon (~180 g CO2/kWh)
        - Daytime standard (06:00 - 15:00): MEDIUM carbon (~350 g CO2/kWh)
        - Evening peak demand (15:00 - 21:00): HIGH carbon (~550 g CO2/kWh)
        - Late evening (21:00 - 24:00): MEDIUM carbon (~300 g CO2/kWh)
        """
        if 0 <= hour < 6:
            return CarbonGridState(
                status="LOW",
                intensity_g_co2_kwh=180.0,
                description="Off-peak night generation (Low carbon)"
            )
        elif 6 <= hour < 15:
            return CarbonGridState(
                status="MEDIUM",
                intensity_g_co2_kwh=350.0,
                description="Standard daytime solar/natural gas grid mix (Medium carbon)"
            )
        elif 15 <= hour < 21:
            return CarbonGridState(
                status="HIGH",
                intensity_g_co2_kwh=550.0,
                description="Evening peak grid demand (High carbon peaker plants)"
            )
        else:
            return CarbonGridState(
                status="MEDIUM",
                intensity_g_co2_kwh=300.0,
                description="Late evening grid transition (Medium carbon)"
            )
