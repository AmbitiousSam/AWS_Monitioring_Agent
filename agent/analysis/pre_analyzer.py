from typing import List, Dict, Any, Optional

def analyze_alb(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ALB data point for potential issues."""
    try:
        short_name = item["resource"].split('/')[-2]
    except IndexError:
        short_name = item["resource"]

    if (value := item.get("http_5xx_errors", 0)) > 20:
        return {
            "finding_type": "static",
            "service": "ALB",
            "resource_id": short_name,
            "issue": "High 5xx Error Count",
            "metric": "HTTP 5xx Errors",
            "value": value,
            "threshold": "> 20",
            "strength": "High",
            "confidence": 0.9,
            "explanation": f"The load balancer recorded {value:.0f} HTTP 5xx errors, which is above the alert threshold of 20.",
        }
    if (value := item.get("avg_latency_ms", 0)) > 100:
        return {
            "finding_type": "static",
            "service": "ALB",
            "resource_id": short_name,
            "issue": "High Target Response Time",
            "metric": "Avg Latency (ms)",
            "value": f"{value:.2f}ms",
            "threshold": "> 100ms",
            "strength": "Moderate",
            "confidence": 0.7,
            "explanation": f"The average target response time was {value:.2f}ms, exceeding the 100ms threshold.",
        }
    return None

def analyze_rds(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single RDS data point for potential issues."""
    if "read" not in item["resource"] and (value := item.get("cpu_utilization", 0)) > 75:
         return {
            "finding_type": "static",
            "service": "RDS",
            "resource_id": item["resource"],
            "issue": "High CPU Utilization on Primary DB",
            "metric": "CPU Utilization (%)",
            "value": f"{value:.1f}%",
            "threshold": "> 75%",
            "strength": "High",
            "confidence": 0.9,
            "explanation": f"The primary database instance CPU is at {value:.1f}%, indicating sustained high load.",
        }
    if "read" in item["resource"] and (value := item.get("cpu_utilization", 0)) > 20:
         return {
            "finding_type": "static",
            "service": "RDS",
            "resource_id": item["resource"],
            "issue": "Elevated CPU on Read Replica",
            "metric": "CPU Utilization (%)",
            "value": f"{value:.1f}%",
            "threshold": "> 20%",
            "strength": "Moderate",
            "confidence": 0.7,
            "explanation": f"The read replica CPU is at {value:.1f}%, which may indicate inefficient queries being offloaded.",
        }
    return None

def analyze_elasticache(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ElastiCache data point for potential issues."""
    if "redis" in item["resource"] and (value := item.get("cache_hit_rate", 100)) < 80:
        return {
            "finding_type": "static",
            "service": "ElastiCache",
            "resource_id": item["resource"],
            "issue": "Low Cache Hit Rate",
            "metric": "Cache Hit Rate (%)",
            "value": f"{value:.1f}%",
            "threshold": "< 80%",
            "strength": "High",
            "confidence": 0.85,
            "explanation": f"The cache hit rate is {value:.1f}%, which is below the recommended 80%. This suggests caching is inefficient.",
        }
    if (value := item.get("evictions", 0)) > 1000:
        return {
            "finding_type": "static",
            "service": "ElastiCache",
            "resource_id": item["resource"],
            "issue": "High Eviction Count",
            "metric": "Evictions (Count)",
            "value": value,
            "threshold": "> 1000",
            "strength": "High",
            "confidence": 0.9,
            "explanation": f"There have been {value:.0f} evictions, indicating the cache may be too small for the workload.",
        }
    return None

def analyze_ecs(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single ECS data point for potential issues."""
    for service in item.get("services", []):
        if (running := service.get("running_tasks", 0)) < (desired := service.get("desired_tasks", 0)):
            return {
                "finding_type": "static",
                "service": "ECS",
                "resource_id": f"{item['resource']}/{service['name']}",
                "issue": "Service Underprovisioned",
                "metric": "Running Tasks vs. Desired",
                "value": f"{running}/{desired}",
                "threshold": "Running < Desired",
                "strength": "High",
                "confidence": 1.0,
                "explanation": f"The service is configured to run {desired} tasks but only {running} are currently running.",
            }
    return None

def analyze_opensearch(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single OpenSearch data point for potential issues."""
    if item.get("cluster_status_red", 0) > 0:
        status = "Red"
        strength = "High"
        confidence = 1.0
    elif item.get("cluster_status_yellow", 0) > 0:
        status = "Yellow"
        strength = "Moderate"
        confidence = 0.8
    else:
        return None

    return {
        "finding_type": "static",
        "service": "OpenSearch",
        "resource_id": item["resource"],
        "issue": f"Cluster in {status} State",
        "metric": "Cluster Status",
        "value": status,
        "threshold": "Not Green",
        "strength": strength,
        "confidence": confidence,
        "explanation": f"The OpenSearch cluster is in a {status} state, indicating a problem with shards or nodes.",
    }

def analyze_cloudformation(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyzes a single CloudFormation data point for potential issues."""
    failed_states = ["CREATE_FAILED", "ROLLBACK_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"]
    if (status := item.get("status")) in failed_states:
        return {
            "finding_type": "static",
            "service": "CloudFormation",
            "resource_id": item["resource"],
            "issue": "Stack in Failed State",
            "metric": "Stack Status",
            "value": status,
            "threshold": f"in {failed_states}",
            "strength": "High",
            "confidence": 1.0,
            "explanation": f"The CloudFormation stack deployment failed and is in a '{status}' state.",
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
