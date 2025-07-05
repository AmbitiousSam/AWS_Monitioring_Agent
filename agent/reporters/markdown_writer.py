from __future__ import annotations

import datetime as dt
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def write_markdown(run_payload: Dict, reports_dir: Path) -> Path:
    """Write a markdown report from the collected data."""
    lines = [
        "# AWS-Diag Report",
        f"_Run generated {run_payload['finished'].replace('Z', ' UTC')}_",
    ]

    # Add executive summary if available
    if summary := run_payload.get("analysis_summary"):
        lines.extend(["## Executive Summary", summary])

    # Group results by namespace for structured reporting
    by_namespace = defaultdict(list)
    for item in run_payload["results"]:
        by_namespace[item["namespace"]].append(item)

    # Define the order of sections in the report
    namespace_order = ["ecs", "alb", "rds", "opensearch", "elasticache", "waf", "cloudformation"]

    # Map namespaces to their desired titles in the report
    namespace_titles = {
        "ecs": "## ECS",
        "alb": "## ALB",
        "rds": "## RDS",
        "opensearch": "## OpenSearch",
        "elasticache": "## ElastiCache",
        "waf": "## WAF",
        "cloudformation": "## CloudFormation",
    }

    for namespace in namespace_order:
        if namespace in by_namespace:
            lines.append("---")
            lines.append(namespace_titles[namespace])
            formatter = globals().get(f"_format_{namespace}")
            if formatter:
                lines.extend(formatter(by_namespace[namespace]))

    content = "\n".join(lines)
    path = reports_dir / "latest.md"
    path.write_text(content)
    return path


def _format_ecs(items: List[Dict[str, Any]]) -> List[str]:
    """Format ECS collector data into markdown."""
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource']}")
        lines.append(
            f"- *Services:* **{item['service_count']}**\n"
            f"- *CPU avg / max (%):* **{item['cpu_avg']} / {item['cpu_max']}**\n"
            f"- *Mem avg / max (%):* **{item['mem_avg']} / {item['mem_max']}**"
        )
        if "log_errors" in item and any(item["log_errors"].values()):
            errors = item["log_errors"]
            error_list = [f"> {k}: {v}" for k, v in errors.items() if v > 0]
            lines.append("- *Log Anomalies:*\n" + "\n".join(error_list) + "\n")
    return lines


def _format_rds(items: List[Dict[str, Any]]) -> List[str]:
    """Format RDS collector data into markdown."""
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource']}")
        lines.append(
            f"- *CPU Utilization (%):* **{item['cpu_utilization']}**\n"
            f"- *Freeable Memory (MB):* **{item['freeable_memory']}**\n"
            f"- *DB Connections:* **{item['db_connections']}**"
        )
        pi = item.get("performance_insights", {})
        if pi.get("status") == "enabled" and pi.get("top_queries"):
            lines.append("- *Performance Insights (Top 5 Queries by Load):*")
            for query in pi["top_queries"]:
                lines.append(f"  - `load: {query['load']}`: `{query['sql']}`")
        lines.append("")
    return lines


def _format_elasticache(items: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource']}")
        lines.append(
            f"- *CPU Utilization (%):* **{item['cpu_utilization']}**\n"
            f"- *Freeable Memory (MB):* **{round(item['freeable_memory'] / 1e6, 2)}**\n"
            f"- *Cache Hit Rate (%):* **{item['cache_hit_rate']}**\n"
            f"- *Evictions (Count):* **{item['evictions']}**\n"
            f"- *Replication Lag (s):* **{item['replication_lag']}**\n"
        )
    return lines


def _format_waf(items: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource']} ({item['scope']})")
        lines.append(
            f"- *Allowed Requests:* **{item['allowed_requests']}**\n"
            f"- *Blocked Requests:* **{item['blocked_requests']}**\n"
        )
    return lines


def _format_opensearch(items: List[Dict[str, Any]]) -> List[str]:
    """Format OpenSearch collector data into markdown."""
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource']}")
        lines.append(
            f"- *CPU Utilization (%):* **{item['cpu_utilization']}**\n"
            f"- *Free Storage (MB):* **{item['free_storage_space']}**\n"
            f"- *Cluster Status (Red/Yellow):* **{item['cluster_status_red']} / {item['cluster_status_yellow']}**\n"
            f"- *Search Latency (ms):* **{item.get('search_latency_ms', 'N/A')}**\n"
            f"- *Indexing Latency (ms):* **{item.get('indexing_latency_ms', 'N/A')}**\n"
            f"- *Query Cache Hit Rate (%):* **{item.get('query_cache_hit_rate', 'N/A')}**\n"
        )
    return lines


def _format_alb(items: List[Dict[str, Any]]) -> List[str]:
    """Format ALB collector data into markdown."""
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource'].split('/')[-2]}")  # Show ALB name
        lines.append(
            f"- *HTTP 5xx Errors:* **{item['http_5xx_errors']}**\n"
            f"- *Request Count:* **{item['request_count']}**\n"
            f"- *Avg Latency (ms):* **{item['avg_latency_ms']}**\n"
            f"- *Unhealthy Hosts (Total):* **{item['unhealthy_host_count']}**"
        )
        if item["target_groups"]:
            lines.append("- *Target Groups:*")
            for tg in item["target_groups"]:
                lines.append(f"  - `{tg['name']}`: {tg['unhealthy_hosts']} unhealthy hosts")
        lines.append("")
    return lines


def _format_cloudformation(items: List[Dict[str, Any]]) -> List[str]:
    """Format CloudFormation collector data into markdown."""
    lines = []
    for item in sorted(items, key=lambda x: x["resource"]):
        lines.append(f"### {item['resource']}")
        lines.append(
            f"- *Status:* **{item['stack_status']}**\n"
            f"- *Last Updated:* **{item['last_updated_time']}**\n"
        )
    return lines