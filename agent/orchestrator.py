from __future__ import annotations
import os
import concurrent.futures as _fut
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List
import importlib
import pkgutil

from .collectors.base import get_collectors
from .analysis.analyzer import Analyzer
from .reporters.json_writer import write_json
from .reporters.markdown_writer import write_markdown

def _autoload_collectors():
    from agent import collectors as _pkg  # local import to avoid circulars

    for mod in pkgutil.walk_packages(_pkg.__path__, _pkg.__name__ + "."):
        importlib.import_module(mod.name)

_autoload_collectors()


def run_collection(settings, reports_dir: Path) -> Path:
    start = dt.datetime.utcnow()

    results: List[Dict] = []
    max_workers = settings.threads or min(32, os.cpu_count() * 5)
    futures = []

    with _fut.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for coll_cls in get_collectors():
            coll = coll_cls(settings)
            for res in coll.discover():
                futures.append(pool.submit(coll.collect, res))

        for f in _fut.as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                print(f"A collector failed: {e}")

    # Find previous run data for temporal analysis
    previous_results = []
    previous_run_timestamp_str = None
    try:
        # Get all previous JSON reports, sort them to find the latest one
        json_reports = sorted(reports_dir.glob("run-*.json"), reverse=True)
        if json_reports:
            previous_report_path = json_reports[0]
            with open(previous_report_path, "r") as f:
                previous_run_data = json.load(f)
                previous_results = previous_run_data.get("results", [])
                previous_run_timestamp_str = previous_run_data.get("finished")
                print(f"Loaded {len(previous_results)} results from previous run for temporal analysis.")
    except (IndexError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load previous run data for temporal analysis: {e}")
        previous_results = []

    # Run analysis
    analyzer = Analyzer(settings)
    summary = analyzer.run_analysis(
        current_results=results,
        previous_results=previous_results,
        current_timestamp=start,
        previous_timestamp_str=previous_run_timestamp_str,
    )

    run_payload = {
        "started": start.isoformat(timespec="seconds") + "Z",
        "finished": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "results": results,
        "analysis_summary": summary,
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = write_json(run_payload, reports_dir)
    write_markdown(run_payload, reports_dir)

    return json_path
