from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict


def write_json(payload: Dict, reports_dir: Path) -> Path:
    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = reports_dir / f"run-{timestamp}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path
