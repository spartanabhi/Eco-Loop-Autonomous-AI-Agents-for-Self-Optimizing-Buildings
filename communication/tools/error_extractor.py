"""
Runtime Error Extractor Tool.
Extracts and summarizes warnings, severe errors, and fatal errors from EnergyPlus eplusout.err.
"""

from pathlib import Path
from typing import Dict, Any, List

def extract_runtime_errors(err_file_path: str) -> Dict[str, Any]:
    """
    Parses EnergyPlus eplusout.err file and returns structured error summary.
    """
    path = Path(err_file_path)
    if not path.is_file():
        return {
            "status": "error",
            "message": f"Error file not found at '{path}'."
        }

    warnings: List[str] = []
    severe_errors: List[str] = []
    fatal_errors: List[str] = []
    completion_msg: str = ""

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if "** Warning **" in stripped:
                warnings.append(stripped)
            elif "** Severe  **" in stripped:
                severe_errors.append(stripped)
            elif "** Fatal   **" in stripped:
                fatal_errors.append(stripped)
            elif "EnergyPlus Completed Successfully" in stripped or "EnergyPlus Terminated" in stripped:
                completion_msg = stripped

    return {
        "status": "success",
        "file_path": str(path),
        "completion_message": completion_msg or "No explicit completion message found",
        "warning_count": len(warnings),
        "severe_count": len(severe_errors),
        "fatal_count": len(fatal_errors),
        "sample_warnings": warnings[:5],
        "severe_errors": severe_errors,
        "fatal_errors": fatal_errors
    }
