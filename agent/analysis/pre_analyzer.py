from typing import List, Dict, Any, Optional

def analyze_alb(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ALB data point for potential issues."""
    # Extract short name from ARN for readability
    try:
        short_name = item["resource"].split('/')[-2]
    except IndexError:
        short_name = item["resource"]

    if item.get("http_5xx_errors", 0) > 20:
        return {
            "service": "ALB",
            "resource": short_name,
            "issue": "High 5xx Error Count",
            "metric": "HTTP 5xx Errors",
            "value": item["http_5xx_errors"],
            "threshold": "> 20",
        }
    if item.get("avg_latency_ms", 0) > 100:
        return {
            "service": "ALB",
            "resource": short_name,
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

def analyze_ecs(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ECS data point for potential issues."""
    for service in item.get("services", []):
        if service.get("running_tasks", 0) < service.get("desired_tasks", 0):
            return {
                "service": "ECS",
                "resource": f"{item['resource']}/{service['name']}",
                "issue": "Service Underprovisioned",
                "metric": "Running Tasks vs. Desired",
                "value": f"{service['running_tasks']}/{service['desired_tasks']}",
                "threshold": "Running < Desired",
            }
    return None

def analyze_opensearch(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single OpenSearch data point for potential issues."""
    if item.get("cluster_status_red", 0) > 0 or item.get("cluster_status_yellow", 0) > 0:
        status = "Red" if item.get("cluster_status_red", 0) > 0 else "Yellow"
        return {
            "service": "OpenSearch",
            "resource": item["resource"],
            "issue": f"Cluster in {status} State",
            "metric": "Cluster Status",
            "value": status,
            "threshold": "Not Green",
        }
    return None

def analyze_cloudformation(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single CloudFormation data point for potential issues."""
    failed_states = ["CREATE_FAILED", "ROLLBACK_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]
    if item.get("status") in failed_states:
        return {
            "service": "CloudFormation",
            "resource": item["resource"],
            "issue": "Stack in Failed State",
            "metric": "Stack Status",
            "value": item["status"],
            "threshold": f"not in {failed_states}",
        }
    return None

# A map to call the correct analyzer function based on namespace
ANALYZER_MAP = {
    "alb": analyze_alb,
    "rds": analyze_rds,
    "elasticache": analyze_elasticache,
    "ecs": analyze_ecs,
    "opensearch": analyze_opensearch,
    "cloudformation": analyze_cloudformation,
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
