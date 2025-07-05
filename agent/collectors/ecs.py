"""ECS collector – now returns CPU & memory utilisation per service.

Data collected per cluster:
- service_count
- avg/max CPU (%) last N hours (cluster level)
- avg/max Memory (%) last N hours (cluster level)

In later phases we’ll drill down to container‑level stats and log queries.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List


from .base import BaseCollector, register

ISO = "%Y-%m-%dT%H:%M:%SZ"

@register
class ECSCollector(BaseCollector):
    namespace = "ecs"

    def _scan_logs(self, log_group_name: str, since: dt.datetime) -> Dict[str, int]:
        logs = self._boto("logs")
        keywords = self.settings.log_keywords
        results = {k: 0 for k in keywords}

        for keyword in keywords:
            try:
                response = logs.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=int(since.timestamp() * 1000),
                    filterPattern=f'"{keyword}"',
                )
                # The `events` list gives us the count directly
                results[keyword] = len(response.get("events", []))
            except logs.exceptions.ResourceNotFoundException:
                # Log group might not exist yet for a new service
                pass
        return results

    def _cpu_mem_stats(self, cluster_name: str, service_name: str, since: dt.datetime, now: dt.datetime):
        cw = self._boto("cloudwatch")
        # Get a single datapoint for the entire lookback window.
        # The period must be a multiple of 60.
        period = self.settings.lookback_hours * 3600
        metrics = {
            "CPUUtilization": {},
            "MemoryUtilization": {},
        }
        for metric_name in metrics:
            response = cw.get_metric_statistics(
                Namespace="AWS/ECS",
                MetricName=metric_name,
                Dimensions=[
                    {"Name": "ClusterName", "Value": cluster_name},
                    {"Name": "ServiceName", "Value": service_name},
                ],
                StartTime=since,
                EndTime=now,
                Period=int(period),
                Statistics=["Average", "Maximum"],
            )
            datapoints = response.get("Datapoints", [])
            if datapoints:
                # With a single datapoint, avg and max are the same as the value
                avg = datapoints[0]["Average"]
                max_val = datapoints[0]["Maximum"]
            else:
                avg = max_val = 0.0
            metrics[metric_name] = {"avg": avg, "max": max_val}
        return metrics

    # ---------- BaseCollector impl ---------- #
    def discover(self) -> List[str]:
        ecs = self._boto("ecs")
        if "*" in self.settings.ecs_clusters:
            return ecs.list_clusters()["clusterArns"]
        return self.settings.ecs_clusters

    def collect(self, cluster_arn: str) -> Dict[str, Any]:
        ecs = self._boto("ecs")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)
        cluster_name = cluster_arn.split("/")[-1]

        service_arns = ecs.list_services(cluster=cluster_arn, maxResults=100)["serviceArns"]
        if not service_arns:
            return {
                "namespace": self.namespace,
                "resource": cluster_arn,
                "service_count": 0,
                "cpu_avg": 0.0,
                "cpu_max": 0.0,
                "mem_avg": 0.0,
                "mem_max": 0.0,
                "log_errors": {},
                "collected_at": now.strftime(ISO),
            }

        # Describe services to get log configuration
        described_services = ecs.describe_services(cluster=cluster_arn, services=service_arns)["services"]

        all_cpu_avg, all_cpu_max = [], []
        all_mem_avg, all_mem_max = [], []
        total_log_errors = {k: 0 for k in self.settings.log_keywords}

        for service in described_services:
            service_name = service["serviceName"]
            stats = self._cpu_mem_stats(cluster_name, service_name, since, now)
            if stats["CPUUtilization"]["avg"] is not None:
                all_cpu_avg.append(stats["CPUUtilization"]["avg"])
            if stats["CPUUtilization"]["max"] is not None:
                all_cpu_max.append(stats["CPUUtilization"]["max"])
            if stats["MemoryUtilization"]["avg"] is not None:
                all_mem_avg.append(stats["MemoryUtilization"]["avg"])
            if stats["MemoryUtilization"]["max"] is not None:
                all_mem_max.append(stats["MemoryUtilization"]["max"])

            # Scan logs
            log_config = service.get("logConfiguration")
            if log_config and log_config.get("logDriver") == "awslogs":
                log_group = log_config.get("options", {}).get("awslogs-group")
                if log_group:
                    log_stats = self._scan_logs(log_group, since)
                    for k, v in log_stats.items():
                        total_log_errors[k] += v

        # Aggregate the results
        final_cpu_avg = sum(all_cpu_avg) / len(all_cpu_avg) if all_cpu_avg else 0.0
        final_cpu_max = max(all_cpu_max) if all_cpu_max else 0.0
        final_mem_avg = sum(all_mem_avg) / len(all_mem_avg) if all_mem_avg else 0.0
        final_mem_max = max(all_mem_max) if all_mem_max else 0.0

        return {
            "namespace": self.namespace,
            "resource": cluster_arn,
            "service_count": len(service_arns),
            "cpu_avg": round(final_cpu_avg, 2),
            "cpu_max": round(final_cpu_max, 2),
            "mem_avg": round(final_mem_avg, 2),
            "mem_max": round(final_mem_max, 2),
            "log_errors": total_log_errors,
            "collected_at": now.strftime(ISO),
        }
