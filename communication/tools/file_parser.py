"""
File Parser Tool.
Parses relevant EnergyPlus project files (IDF metadata, outputs, project logs) within constrained project paths.
"""

from pathlib import Path
from typing import Dict, Any, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def parse_project_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parses a constrained project file (e.g. IDF, ERR, CSV, JSON) and returns summary metadata.
    Does NOT allow unrestricted arbitrary filesystem access outside the project.
    """
    path = Path(file_path).resolve()
    
    # Security check: path must be within project root or outputs/logs directory
    if not str(path).startswith(str(PROJECT_ROOT)):
        return {"status": "error", "message": f"Access denied: path '{path}' outside project root."}

    if not path.is_file():
        return {"status": "error", "message": f"File not found: '{path}'."}

    suffix = path.suffix.lower()
    
    try:
        if suffix in [".err", ".txt", ".log"]:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return {
                "status": "success",
                "file_type": "text",
                "line_count": len(lines),
                "preview": [line.strip() for line in lines[:20]]
            }
        elif suffix in [".idf"]:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            zone_count = content.count("Zone,") + content.count("Zone\n")
            people_count = content.count("People,")
            return {
                "status": "success",
                "file_type": "idf",
                "file_size_kb": path.stat().st_size / 1024,
                "detected_zones": zone_count,
                "detected_people_objects": people_count
            }
        elif suffix in [".csv"]:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return {
                "status": "success",
                "file_type": "csv",
                "row_count": len(lines) - 1 if lines else 0,
                "headers": lines[0].strip().split(",") if lines else []
            }
        else:
            return {"status": "success", "file_type": suffix, "file_size_bytes": path.stat().st_size}
    except Exception as e:
        return {"status": "error", "message": f"Error parsing file: {e}"}
