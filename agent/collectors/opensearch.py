from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .base import BaseCollector, register


@register
class OpenSearchCollector(BaseCollector):
    namespace = "opensearch"

    def discover(self) -> List[str]:
        """Discover all OpenSearch domain names."""
        if "*" in self.settings.opensearch_domains:
            opensearch = self._boto("opensearch")
            domains = opensearch.list_domain_names()["DomainNames"]
            return [d["DomainName"] for d in domains]
        return self.settings.opensearch_domains

    def collect(self, resource_id: str) -> Dict[str, Any]:
        """Collect metrics for a single OpenSearch domain."""
        cw = self._boto("cloudwatch")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        def _get_metric(metric_name, unit="Percent"):
            stats = cw.get_metric_statistics(
                Namespace="AWS/ES",
                MetricName=metric_name,
                Dimensions=[
                    {"Name": "DomainName", "Value": resource_id},
                    {"Name": "ClientId", "Value": self.account_id},
                ],
                StartTime=since,
                EndTime=now,
                Period=3600,
                Statistics=["Average"],
                Unit=unit,
            )
            points = stats.get("Datapoints", [])
            return round(points[0]["Average"], 2) if points else 0.0

        search_latency_seconds = _get_metric("SearchLatency", unit="Seconds")
        indexing_latency_ms = _get_metric("IndexingLatency", unit="Milliseconds")

        query_cache_hits = _get_metric("QueryCacheHitCount", unit="Count")
        query_cache_misses = _get_metric("QueryCacheMissCount", unit="Count")

        total_queries = query_cache_hits + query_cache_misses
        query_cache_hit_rate = (
            (query_cache_hits / total_queries) * 100 if total_queries > 0 else 0.0
        )

        return {
            "namespace": self.namespace,
            "resource": resource_id,
            "cpu_utilization": _get_metric("CPUUtilization"),
            "free_storage_space": _get_metric("FreeStorageSpace", unit="Megabytes"),
            "cluster_status_red": _get_metric("ClusterStatus.red", unit="Count"),
            "cluster_status_yellow": _get_metric("ClusterStatus.yellow", unit="Count"),
            "search_latency_ms": round(search_latency_seconds * 1000, 2),
            "indexing_latency_ms": indexing_latency_ms,
            "query_cache_hit_rate": round(query_cache_hit_rate, 2),
            "collected_at": now.isoformat(),
        }
