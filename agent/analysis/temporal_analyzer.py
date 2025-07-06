"""
Performs temporal analysis by comparing the current data run with historical data.
"""

from __future__ import annotations

import datetime as dt
import statistics
from typing import Any, Dict, List, Optional, Tuple

from ..config import Settings


def _format_timedelta(delta: dt.timedelta) -> str:
    """Formats a timedelta into a human-readable string."""
    seconds = delta.total_seconds()
    if seconds < 3600:
        return f"{seconds / 60:.1f} minutes"
    else:
        return f"{seconds / 3600:.1f} hours"


def analyze_trend_with_baseline(
    metric_name: str,
    current_value: float,
    historical_values: List[float],
    time_delta_str: str,
    total_runs: int,
    threshold_std_dev: float = 2.0,
    higher_is_worse: bool = True,
) -> Optional[Tuple[str, float, str, str]]:
    """Analyzes a metric against its historical baseline using standard deviation."""
    if not historical_values or len(historical_values) < 3:
        return None

    data_points_count = len(historical_values)
    quality_notice = ""
    if total_runs > 0 and data_points_count < total_runs:
        quality_notice = (
            f" (Note: Analysis based on {data_points_count}/{total_runs} runs; "
            "some data may be missing.)"
        )

    mean = statistics.mean(historical_values)
    stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0

    if stdev == 0:
        if current_value != mean:
            strength = "High"
            confidence = 0.95
            explanation = (
                f"The metric '{metric_name}' changed from a stable value of {mean:.2f} "
                f"to {current_value:.2f} over {time_delta_str}."
            )
            return strength, confidence, explanation, quality_notice
        return None

    z_score = (current_value - mean) / stdev
    is_bad_trend = (z_score > 0 and higher_is_worse) or (
        z_score < 0 and not higher_is_worse
    )

    if abs(z_score) >= threshold_std_dev and is_bad_trend:
        change_direction = "increased" if z_score > 0 else "decreased"
        strength = "High" if abs(z_score) >= (threshold_std_dev + 1) else "Moderate"
        confidence = min(0.9 + (abs(z_score) - threshold_std_dev) * 0.1, 0.99)
        explanation = (
            f"The metric '{metric_name}' {change_direction} significantly to {current_value:.2f} "
            f"over {time_delta_str}, which is {abs(z_score):.1f} standard deviations from the "
            f"historical average of {mean:.2f}."
        )
        return strength, confidence, explanation, quality_notice

    return None


def analyze(
    current_results: List[Dict[str, Any]],
    settings: Settings,
) -> List[Dict[str, Any]]:
    """Analyzes the current run using embedded historical data."""
    findings = []
    time_delta = dt.timedelta(days=settings.temporal_lookback_days)
    time_delta_str = _format_timedelta(time_delta)

    for current_item in current_results:
        ns = current_item["namespace"]
        res_id = current_item.get("resource_id") or current_item.get("resource")
        if not res_id:
            continue

        analyzer_func = TEMPORAL_ANALYZER_MAP.get(ns)
        if analyzer_func:
            findings.extend(
                analyzer_func(current_item, time_delta_str, settings)
            )

    return findings


def _analyze_alb(
    current: Dict[str, Any],
    time_delta_str: str,
    settings: Settings,
) -> List[Dict[str, Any]]:
    findings = []
    curr_5xx = current.get("http_5xx_errors", 0)
    hist_5xx = current.get("http_5xx_errors_history", [])

    trend = analyze_trend_with_baseline(
        "ALB 5xx Errors",
        curr_5xx,
        hist_5xx,
        time_delta_str,
        total_runs=settings.temporal_lookback_days,
        higher_is_worse=True,
    )
    if trend:
        strength, confidence, explanation, quality_notice = trend
        findings.append(
            {
                "finding_type": "temporal",
                "resource_id": current["resource"],
                "metric": "ALB 5xx Errors",
                "strength": strength,
                "confidence": confidence,
                "explanation": explanation,
                "data_quality_notice": quality_notice,
            }
        )
    return findings


def _analyze_rds(
    current: Dict[str, Any],
    time_delta_str: str,
    settings: Settings,
) -> List[Dict[str, Any]]:
    findings = []
    curr_cpu = current.get("cpu_utilization", 0)
    hist_cpu = current.get("cpu_utilization_history", [])

    trend = analyze_trend_with_baseline(
        "RDS CPU Utilization",
        curr_cpu,
        hist_cpu,
        time_delta_str,
        total_runs=settings.temporal_lookback_days,
        higher_is_worse=True,
    )
    if trend:
        strength, confidence, explanation, quality_notice = trend
        findings.append(
            {
                "finding_type": "temporal",
                "resource_id": current["resource"],
                "metric": "RDS CPU Utilization",
                "strength": strength,
                "confidence": confidence,
                "explanation": explanation,
                "data_quality_notice": quality_notice,
            }
        )
    return findings


def _analyze_elasticache(
    current: Dict[str, Any],
    time_delta_str: str,
    settings: Settings,
) -> List[Dict[str, Any]]:
    findings = []
    curr_cpu = current.get("cpu_utilization", 0)
    hist_cpu = current.get("cpu_utilization_history", [])

    trend = analyze_trend_with_baseline(
        "ElastiCache CPU Utilization",
        curr_cpu,
        hist_cpu,
        time_delta_str,
        total_runs=settings.temporal_lookback_days,
        higher_is_worse=True,
    )
    if trend:
        strength, confidence, explanation, quality_notice = trend
        findings.append(
            {
                "finding_type": "temporal",
                "resource_id": current["resource"],
                "metric": "ElastiCache CPU Utilization",
                "strength": strength,
                "confidence": confidence,
                "explanation": explanation,
                "data_quality_notice": quality_notice,
            }
        )
    return findings


TEMPORAL_ANALYZER_MAP = {
    "alb": _analyze_alb,
    "rds": _analyze_rds,
    "elasticache": _analyze_elasticache,
}
