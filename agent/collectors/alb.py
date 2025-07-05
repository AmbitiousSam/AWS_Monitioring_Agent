from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .base import BaseCollector, register

ISO = "%Y-%m-%dT%H:%M:%SZ"


@register
class ALBCollector(BaseCollector):
    namespace = "alb"

    def _get_metric_sum(
        self, cw, metric_name: str, dimensions: List[Dict[str, str]], since: dt.datetime, now: dt.datetime
    ) -> float:
        """Helper to get the sum of a metric over a period."""
        response = cw.get_metric_statistics(
            Namespace="AWS/ApplicationELB",
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=since,
            EndTime=now,
            Period=self.settings.lookback_hours * 3600,
            Statistics=["Sum"],
        )
        datapoints = response.get("Datapoints", [])
        return sum(d["Sum"] for d in datapoints)

    def _get_metric_avg(
        self, cw, metric_name: str, dimensions: List[Dict[str, str]], since: dt.datetime, now: dt.datetime
    ) -> float:
        """Helper to get the average of a metric over a period."""
        response = cw.get_metric_statistics(
            Namespace="AWS/ApplicationELB",
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=since,
            EndTime=now,
            Period=self.settings.lookback_hours * 3600,
            Statistics=["Average"],
        )
        datapoints = response.get("Datapoints", [])
        if not datapoints:
            return 0.0
        return sum(d["Average"] for d in datapoints) / len(datapoints)

    def discover(self) -> List[str]:
        """Discover all Application Load Balancers."""
        elbv2 = self._boto("elbv2")
        if "*" in self.settings.alb_names:
            paginator = elbv2.get_paginator("describe_load_balancers")
            arns = []
            for page in paginator.paginate():
                arns.extend([lb["LoadBalancerArn"] for lb in page["LoadBalancers"]])
            return arns
        return self.settings.alb_names

    def collect(self, alb_arn: str) -> Dict[str, Any]:
        """Collect metrics for a single Application Load Balancer."""
        elbv2 = self._boto("elbv2")
        cw = self._boto("cloudwatch")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        # ALB ARN format: arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/name/id
        alb_dimension_value = "/".join(alb_arn.split("/")[1:])
        alb_dimensions = [{"Name": "LoadBalancer", "Value": alb_dimension_value}]

        # Get ALB-level metrics
        http_5xx = self._get_metric_sum(cw, "HTTPCode_Target_5XX_Count", alb_dimensions, since, now)
        request_count = self._get_metric_sum(cw, "RequestCount", alb_dimensions, since, now)
        latency = self._get_metric_avg(cw, "TargetResponseTime", alb_dimensions, since, now)

        # Get Target Group metrics
        target_groups = elbv2.describe_target_groups(LoadBalancerArn=alb_arn)["TargetGroups"]
        total_unhealthy_hosts = 0
        target_group_details = []

        for tg in target_groups:
            health_check = elbv2.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
            unhealthy_hosts = sum(
                1 for th in health_check["TargetHealthDescriptions"] if th["TargetHealth"]["State"] != "healthy"
            )
            total_unhealthy_hosts += unhealthy_hosts

            target_group_details.append(
                {
                    "name": tg["TargetGroupName"],
                    "protocol": tg["Protocol"],
                    "port": tg["Port"],
                    "unhealthy_hosts": unhealthy_hosts,
                }
            )

        return {
            "namespace": self.namespace,
            "resource": alb_arn,
            "http_5xx_errors": http_5xx,
            "request_count": request_count,
            "avg_latency_ms": round(latency * 1000, 2),  # convert to ms
            "unhealthy_host_count": total_unhealthy_hosts,
            "target_groups": target_group_details,
            "collected_at": now.strftime(ISO),
        }
