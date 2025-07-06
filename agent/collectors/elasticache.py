from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .base import BaseCollector, register


@register
class ElastiCacheCollector(BaseCollector):
    namespace = "elasticache"

    def discover(self) -> List[str]:
        """Discover all ElastiCache cluster identifiers."""
        if "*" in self.settings.elasticache_clusters:
            ec = self._boto("elasticache")
            clusters = ec.describe_cache_clusters()["CacheClusters"]
            return [c["CacheClusterId"] for c in clusters]
        return self.settings.elasticache_clusters

    def _get_metric_history(
        self, cw, metric_name: str, resource_id: str, stat: str, unit: str
    ) -> List[float]:
        """Helper to get a time series of a metric for temporal analysis."""
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(days=self.settings.temporal_lookback_days)

        response = cw.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "m1",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ElastiCache",
                            "MetricName": metric_name,
                            "Dimensions": [{
                                "Name": "CacheClusterId", 
                                "Value": resource_id
                            }],
                        },
                        "Period": 86400,  # Daily resolution
                        "Stat": stat,
                        "Unit": unit,
                    },
                    "ReturnData": True,
                },
            ],
            StartTime=since,
            EndTime=now,
            ScanBy="TimestampAscending",
        )
        return [round(v, 2) for v in response["MetricDataResults"][0]["Values"]]

    def collect(self, resource_id: str) -> Dict[str, Any]:
        """Collect metrics for a single ElastiCache cluster."""
        cw = self._boto("cloudwatch")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        metric_definitions = {
            "CPUUtilization": ("Percent", "Average"),
            "FreeableMemory": ("Bytes", "Average"),
            "CacheHits": ("Count", "Sum"),
            "CacheMisses": ("Count", "Sum"),
            "Evictions": ("Count", "Sum"),
            "ReplicationLag": ("Seconds", "Average"),
        }

        metric_data_queries = [
            {
                "Id": f"m{i}",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/ElastiCache",
                        "MetricName": name,
                        "Dimensions": [{"Name": "CacheClusterId", "Value": resource_id}],
                    },
                    "Period": self.settings.lookback_hours * 3600,
                    "Stat": stat,
                    "Unit": unit,
                },
            }
            for i, (name, (unit, stat)) in enumerate(metric_definitions.items())
        ]

        current_metrics = {}
        if metric_data_queries:
            response = cw.get_metric_data(
                MetricDataQueries=metric_data_queries, StartTime=since, EndTime=now
            )
            for result in response["MetricDataResults"]:
                metric_name = next(
                    q["MetricStat"]["Metric"]["MetricName"]
                    for q in metric_data_queries
                    if q["Id"] == result["Id"]
                )
                value = result["Values"][0] if result.get("Values") else 0.0
                current_metrics[metric_name] = round(value, 2)

        cache_hits = current_metrics.get("CacheHits", 0.0)
        cache_misses = current_metrics.get("CacheMisses", 0.0)
        total_gets = cache_hits + cache_misses
        hit_rate = (cache_hits / total_gets) * 100 if total_gets > 0 else 0.0

        cpu_history = self._get_metric_history(
            cw, "CPUUtilization", resource_id, "Average", "Percent"
        )

        return {
            "namespace": self.namespace,
            "resource": resource_id,
            "cpu_utilization": current_metrics.get("CPUUtilization", 0.0),
            "cpu_utilization_history": cpu_history,
            "freeable_memory": current_metrics.get("FreeableMemory", 0.0),
            "cache_hit_rate": round(hit_rate, 2),
            "evictions": current_metrics.get("Evictions", 0.0),
            "replication_lag": current_metrics.get("ReplicationLag", 0.0),
            "collected_at": now.isoformat(),
        }
