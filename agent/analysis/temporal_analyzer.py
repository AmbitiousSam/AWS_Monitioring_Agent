"""
Performs temporal analysis by comparing the current data run with the previous one.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone

def _format_timedelta(delta) -> str:
    """Formats a timedelta into a human-readable string."""
    seconds = delta.total_seconds()
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} minutes"
    else:
        return f"{seconds / 3600:.1f} hours"

def compare_runs(
    current_results: List[Dict[str, Any]],
    previous_results: List[Dict[str, Any]],
    current_timestamp: datetime,
    previous_timestamp_str: str,
) -> List[Dict[str, Any]]:
    """Compares the current run with the previous run and identifies significant changes."""
    findings = []

    try:
        # Ensure current_timestamp is offset-aware, assuming UTC if naive.
        if current_timestamp.tzinfo is None:
            current_timestamp = current_timestamp.replace(tzinfo=timezone.utc)

        previous_timestamp = datetime.fromisoformat(previous_timestamp_str.replace('Z', '+00:00'))
        time_delta_str = _format_timedelta(current_timestamp - previous_timestamp)
    except (ValueError, TypeError, AttributeError):
        # Fallback if timestamps are missing or invalid
        time_delta_str = "the last run"

    # Create a lookup map for previous results for efficient access
    previous_map = {(item['namespace'], item.get('resource_id') or item.get('resource')): item for item in previous_results}

    for current_item in current_results:
        key = (current_item['namespace'], current_item.get('resource_id') or current_item.get('resource'))
        previous_item = previous_map.get(key)

        if not previous_item:
            continue

        # Get the specific analyzer for the namespace, if it exists
        analyzer_func = TEMPORAL_ANALYZER_MAP.get(current_item['namespace'])
        if analyzer_func:
            finding = analyzer_func(current_item, previous_item, time_delta_str)
            if finding:
                findings.append(finding)

    return findings

def _analyze_alb(current: Dict[str, Any], previous: Dict[str, Any], time_delta_str: str) -> Dict[str, Any] | None:
    """Analyzes ALB metrics for significant changes."""
    # Spike in 5xx errors
    prev_5xx = previous.get("http_5xx_errors", 0)
    curr_5xx = current.get("http_5xx_errors", 0)

    if curr_5xx > prev_5xx and (curr_5xx - prev_5xx) > 10:  # Threshold: increase of more than 10
        return {
            "finding_type": "temporal",
            "resource_id": current["resource"],
            "metric": "ALB 5xx Errors",
            "change_description": f"Spike in 5xx errors from {prev_5xx} to {curr_5xx} in {time_delta_str}.",
        }
    return None

def _analyze_rds(current: Dict[str, Any], previous: Dict[str, Any], time_delta_str: str) -> Dict[str, Any] | None:
    """Analyzes RDS metrics for significant changes."""
    # Sustained high CPU
    prev_cpu = previous.get("cpu_utilization", 0)
    curr_cpu = current.get("cpu_utilization", 0)

    if curr_cpu > 80 and prev_cpu > 80:  # Threshold: remains above 80%
        return {
            "finding_type": "temporal",
            "resource_id": current["resource"],
            "metric": "RDS CPU Utilization",
            "change_description": f"Sustained high CPU utilization over {time_delta_str}, currently at {curr_cpu:.2f}%.",
        }
    return None

def _analyze_elasticache(current: Dict[str, Any], previous: Dict[str, Any], time_delta_str: str) -> Dict[str, Any] | None:
    """Analyzes ElastiCache metrics for significant changes."""
    # Increase in evictions
    prev_evictions = previous.get("evictions", 0)
    curr_evictions = current.get("evictions", 0)

    if curr_evictions > prev_evictions and (curr_evictions - prev_evictions) > 100:  # Threshold: increase of 100
        return {
            "finding_type": "temporal",
            "resource_id": current["resource"],
            "metric": "ElastiCache Evictions",
            "change_description": f"Significant increase in evictions from {prev_evictions} to {curr_evictions} over {time_delta_str}.",
        }
    return None


TEMPORAL_ANALYZER_MAP = {
    'alb': _analyze_alb,
    'rds': _analyze_rds,
    'elasticache': _analyze_elasticache,
}
