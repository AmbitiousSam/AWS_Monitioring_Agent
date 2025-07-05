from typing import List, Dict, Any, Optional

def analyze_alb(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ALB data point for potential issues."""
    if item.get("http_5xx_errors", 0) > 20:
        return {
            "service": "ALB",
            "resource": item["resource"],
            "issue": "High 5xx Error Count",
            "metric": "HTTP 5xx Errors",
            "value": item["http_5xx_errors"],
            "threshold": "> 20",
        }
    if item.get("avg_latency_ms", 0) > 100:
        return {
            "service": "ALB",
            "resource": item["resource"],
            "issue": "High Target Response Time",
            "metric": "Avg Latency (ms)",
            "value": item["avg_latency_ms"],
            "threshold": "> 100ms",
        }
    return None

def analyze_rds(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single RDS data point for potential issues."""
    # Check for high CPU on non-read replicas
    if "read" not in item["resource"] and item.get("cpu_utilization", 0) > 75:
         return {
            "service": "RDS",
            "resource": item["resource"],
            "issue": "High CPU Utilization on Primary DB",
            "metric": "CPU Utilization (%)",
            "value": item["cpu_utilization"],
            "threshold": "> 75%",
        }
    # Check for high CPU on read replicas (indicates inefficient queries)
    if "read" in item["resource"] and item.get("cpu_utilization", 0) > 20:
         return {
            "service": "RDS",
            "resource": item["resource"],
            "issue": "Elevated CPU on Read Replica",
            "metric": "CPU Utilization (%)",
            "value": item["cpu_utilization"],
            "threshold": "> 20%",
        }
    return None


def analyze_elasticache(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ElastiCache data point for potential issues."""
    if item.get("cache_hit_rate", 100) < 80 and "redis" in item["resource"]: # Only for redis clusters
        return {
            "service": "ElastiCache",
            "resource": item["resource"],
            "issue": "Low Cache Hit Rate",
            "metric": "Cache Hit Rate (%)",
            "value": item["cache_hit_rate"],
            "threshold": "< 80%",
        }
    if item.get("evictions", 0) > 1000:
        return {
            "service": "ElastiCache",
            "resource": item["resource"],
            "issue": "High Eviction Count",
            "metric": "Evictions (Count)",
            "value": item["evictions"],
            "threshold": "> 1000",
        }
    return None


# A map to call the correct analyzer function based on namespace
ANALYZER_MAP = {
    "alb": analyze_alb,
    "rds": analyze_rds,
    "elasticache": analyze_elasticache,
}


def run_pre_analysis(collected_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Runs a pre-analysis on the collected data to identify specific issues
    based on predefined rules.
    """
    findings = []
    for item in collected_data:
        namespace = item.get("namespace")
        if analyzer_func := ANALYZER_MAP.get(namespace):
            if finding := analyzer_func(item):
                findings.append(finding)
    return findings
