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

    # Run analysis
    # Historical data is now embedded in the results from collectors.
    analyzer = Analyzer(settings)
    summary = analyzer.run_analysis(
        current_results=results,
        current_timestamp=start,
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


def run_analysis_on_report(report_path: Path, reports_dir: Path, settings):
    """
    Runs only the analysis and reporting steps on an existing JSON report.
    """
    # Load the specified report
    with open(report_path, "r") as f:
        report_payload = json.load(f)

    current_results = report_payload["results"]
    start_str = report_payload["started"]
    start = dt.datetime.fromisoformat(start_str.replace("Z", "+00:00"))


    # Run analysis
    # Historical data is embedded in the report's results, so we don't need to load other files.
    analyzer = Analyzer(settings)
    summary = analyzer.run_analysis(
        current_results=current_results,
        current_timestamp=start,
    )

    # Update the payload with the new analysis
    report_payload["analysis_summary"] = summary

    # Generate a new markdown report
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_markdown(report_payload, reports_dir)

    print(f"Re-analysis complete. Markdown report updated.")

