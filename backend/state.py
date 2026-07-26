"""
Global In-Memory State for Eco-Loop Backend.
"""

from typing import Dict, Any, Optional

class SystemState:
    def __init__(self):
        self.simulation_status: str = "IDLE"
        self.current_run_id: str = "summer-ai-v2-1785084104"
        self.season: str = "summer"
        self.data_mode: str = "VALIDATED_REPLAY"
        self.replay_index: int = 0
        self.replay_active: bool = False

system_state = SystemState()
