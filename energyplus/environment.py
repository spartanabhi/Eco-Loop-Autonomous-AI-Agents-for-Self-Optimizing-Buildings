"""
EnergyPlus Environment and API Discovery Module.
Discovers EnergyPlus installation, executable, and PyEnergyPlus library paths.
"""

import os
import sys
import glob
import platform
import shutil
from pathlib import Path
from typing import Optional, Dict, Tuple, Any

from config.settings import ENERGYPLUS_HOME, ENERGYPLUS_EXECUTABLE, ENERGYPLUS_PYTHON_API_PATH

def get_possible_install_locations() -> list[str]:
    """Return common installation search locations based on OS."""
    system = platform.system()
    home_dir = os.path.expanduser("~")
    locations = []

    if system == "Windows":
        locations.extend([
            r"C:\EnergyPlus*",
            r"C:\Program Files\EnergyPlus*",
            r"C:\Program Files (x86)\EnergyPlus*",
            os.path.join(home_dir, r"AppData\Local\EnergyPlus*"),
            os.path.join(home_dir, r"AppData\Local\Programs\EnergyPlus*"),
        ])
    elif system == "Linux":
        locations.extend([
            "/usr/local/EnergyPlus*",
            "/usr/local/bin/EnergyPlus*",
            "/opt/EnergyPlus*",
            os.path.join(home_dir, "EnergyPlus*"),
        ])
    elif system == "Darwin":  # macOS
        locations.extend([
            "/Applications/EnergyPlus*",
            "/usr/local/EnergyPlus*",
            os.path.join(home_dir, "Applications/EnergyPlus*"),
        ])

    expanded = []
    for loc in locations:
        expanded.extend(glob.glob(loc))
    
    # Sort descending so newer versions appear first (e.g. EnergyPlusV24 > EnergyPlusV23)
    return sorted(expanded, reverse=True)

def find_energyplus() -> Dict[str, Any]:
    """
    Search for EnergyPlus installation and PyEnergyPlus API.
    Returns dictionary with status and detected paths.
    """
    info = {
        "installed": False,
        "home": None,
        "executable": None,
        "python_api_path": None,
        "version": None,
        "error": None
    }

    # 1. Check explicit setting first
    candidate_homes = []
    if ENERGYPLUS_HOME and os.path.isdir(ENERGYPLUS_HOME):
        candidate_homes.append(ENERGYPLUS_HOME)
    
    # 2. Add discovered install locations
    candidate_homes.extend(get_possible_install_locations())

    # 3. Check PATH for executable
    path_exec = shutil.which("energyplus") or shutil.which("energyplus.exe")
    if path_exec and not candidate_homes:
        exec_dir = os.path.dirname(os.path.abspath(path_exec))
        candidate_homes.append(exec_dir)

    for home in candidate_homes:
        home_path = Path(home)
        if not home_path.is_dir():
            continue

        # Look for executable
        exec_name = "energyplus.exe" if platform.system() == "Windows" else "energyplus"
        possible_execs = [
            home_path / exec_name,
            home_path / "bin" / exec_name,
        ]
        if ENERGYPLUS_EXECUTABLE and Path(ENERGYPLUS_EXECUTABLE).is_file():
            possible_execs.insert(0, Path(ENERGYPLUS_EXECUTABLE))

        found_exec = None
        for ex in possible_execs:
            if ex.is_file():
                found_exec = str(ex)
                break

        # Look for pyenergyplus module
        possible_api_paths = [
            home_path / "pyenergyplus",
            home_path / "EnergyPlus" / "api" / "python",
            home_path,
        ]
        if ENERGYPLUS_PYTHON_API_PATH and Path(ENERGYPLUS_PYTHON_API_PATH).is_dir():
            possible_api_paths.insert(0, Path(ENERGYPLUS_PYTHON_API_PATH))

        found_api_path = None
        for api_p in possible_api_paths:
            if (api_p / "api" / "EnergyPlusAPI.py").is_file() or (api_p / "pyenergyplus").is_dir():
                found_api_path = str(api_p)
                break
            elif (api_p / "EnergyPlusAPI.py").is_file():
                found_api_path = str(api_p.parent)
                break

        if found_exec or found_api_path or home_path.is_dir():
            info["installed"] = True
            info["home"] = str(home_path)
            info["executable"] = found_exec
            info["python_api_path"] = found_api_path or str(home_path)
            info["version"] = home_path.name
            break

    return info

def setup_energyplus_path() -> Tuple[bool, Optional[str]]:
    """
    Locates EnergyPlus and adds pyenergyplus to sys.path.
    Returns (success_boolean, message).
    """
    info = find_energyplus()
    
    if not info["installed"]:
        return False, "EnergyPlus installation not found on system."

    api_path = info.get("python_api_path")
    if api_path and api_path not in sys.path:
        sys.path.insert(0, api_path)

    # Test pyenergyplus import
    try:
        from pyenergyplus.api import EnergyPlusAPI
        return True, f"PyEnergyPlus imported successfully from {api_path}"
    except ImportError as e:
        return False, f"EnergyPlus found at {info['home']}, but failed to import pyenergyplus: {e}"
