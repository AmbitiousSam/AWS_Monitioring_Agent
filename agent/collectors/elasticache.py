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

    def collect(self, resource_id: str) -> Dict[str, Any]:
        """Collect metrics for a single ElastiCache cluster."""
        cw = self._boto("cloudwatch")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        def _get_metric(metric_name, unit="Percent", stat="Average"):
            stats = cw.get_metric_statistics(
                Namespace="AWS/ElastiCache",
                MetricName=metric_name,
                Dimensions=[{"Name": "CacheClusterId", "Value": resource_id}],
                StartTime=since,
                EndTime=now,
                Period=3600,
                Statistics=[stat],
                Unit=unit,
            )
            points = stats.get("Datapoints", [])
            return round(points[0][stat], 2) if points else 0.0

        cache_hits = _get_metric("CacheHits", unit="Count", stat="Sum")
        cache_misses = _get_metric("CacheMisses", unit="Count", stat="Sum")
        total_gets = cache_hits + cache_misses
        hit_rate = (cache_hits / total_gets) * 100 if total_gets > 0 else 0.0

        return {
            "namespace": self.namespace,
            "resource": resource_id,
            "cpu_utilization": _get_metric("CPUUtilization"),
            "freeable_memory": _get_metric("FreeableMemory", unit="Bytes"),
            "cache_hit_rate": round(hit_rate, 2),
            "evictions": _get_metric("Evictions", unit="Count", stat="Sum"),
            "replication_lag": _get_metric("ReplicationLag", unit="Seconds"),
            "collected_at": now.isoformat(),
        }
