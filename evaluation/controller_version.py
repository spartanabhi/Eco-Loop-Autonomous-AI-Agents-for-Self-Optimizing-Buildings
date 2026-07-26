"""
Controller Version & Configuration Freeze Module.
Calculates SHA-256 code hash of authoritative policy & schema modules to guarantee
that zero controller policy, prompt, schema, or safety code modifications occur.
"""

import sys
import hashlib
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONTROLLER_VERSION = "policy_iter1_frozen"

# Authoritative Policy & Logic Files (Frozen)
FROZEN_POLICY_FILES = [
    PROJECT_ROOT / "agent" / "orchestrator.py",
    PROJECT_ROOT / "agent" / "prompts.py",
    PROJECT_ROOT / "agent" / "schemas.py",
    PROJECT_ROOT / "energyplus" / "control.py"
]

def calculate_controller_hash() -> str:
    """Calculates SHA-256 hash across all frozen policy code files."""
    hasher = hashlib.sha256()
    for fpath in FROZEN_POLICY_FILES:
        if fpath.is_file():
            with open(fpath, "rb") as f:
                hasher.update(f.read())
    return hasher.hexdigest()[:16]

def get_frozen_controller_metadata() -> Dict[str, str]:
    """Returns metadata dict of frozen controller version."""
    return {
        "controller_version": CONTROLLER_VERSION,
        "controller_code_hash": calculate_controller_hash(),
        "target_files_count": len(FROZEN_POLICY_FILES)
    }

if __name__ == "__main__":
    meta = get_frozen_controller_metadata()
    print("=" * 60)
    print(" FROZEN CONTROLLER METADATA")
    print("=" * 60)
    print(f" Controller Version:   {meta['controller_version']}")
    print(f" Code SHA-256 Hash:   {meta['controller_code_hash']}")
    print("=" * 60)
