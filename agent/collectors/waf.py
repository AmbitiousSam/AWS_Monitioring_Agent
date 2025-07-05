from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .base import BaseCollector, register


@register
class WAFCollector(BaseCollector):
    namespace = "waf"

    def discover(self) -> List[str]:
        """Discover all WAFv2 Web ACL ARNs."""
        if "*" not in self.settings.waf_web_acls:
            return self.settings.waf_web_acls

        waf = self._boto("wafv2")
        arns = []
        for scope in ["REGIONAL", "CLOUDFRONT"]:
            try:
                acls = waf.list_web_acls(Scope=scope)["WebACLs"]
                arns.extend([acl["ARN"] for acl in acls])
            except Exception:
                # May fail if WAF is not used in the region
                pass
        
        # Filter based on config, if it's not "*"
        if self.settings.waf_web_acls != ["*"]:
            filtered_arns = []
            for pattern in self.settings.waf_web_acls:
                for arn in arns:
                    if pattern in arn:
                        filtered_arns.append(arn)
            return filtered_arns
            
        return arns

    def collect(self, resource_id: str) -> Dict[str, Any]:
        """Collect metrics for a single WAF Web ACL."""
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        # ARN format: arn:aws:wafv2:REGION:ACCOUNT:SCOPE/webacl/NAME/ID
        parts = resource_id.split(":")
        region = parts[3]
        name_part = parts[5].split("/")
        scope = name_part[0].upper()
        web_acl_name = name_part[2]
        
        # CloudFront metrics are always in us-east-1
        metrics_region = "us-east-1" if scope == "CLOUDFRONT" else region

        # Boto sessions are cached, so this should be efficient
        cw_metrics = self._boto("cloudwatch", region_name=metrics_region)

        def _get_metric(metric_name, stat="Sum"):
            stats = cw_metrics.get_metric_statistics(
                Namespace="AWS/WAFV2",
                MetricName=metric_name,
                Dimensions=[
                    {"Name": "WebACL", "Value": web_acl_name},
                    {"Name": "Region", "Value": metrics_region},
                ],
                StartTime=since,
                EndTime=now,
                Period=self.settings.lookback_hours * 3600,
                Statistics=[stat],
                Unit="Count",
            )
            points = stats.get("Datapoints", [])
            return round(points[0][stat], 2) if points else 0.0

        return {
            "namespace": self.namespace,
            "resource": web_acl_name,
            "scope": scope,
            "allowed_requests": _get_metric("AllowedRequests"),
            "blocked_requests": _get_metric("BlockedRequests"),
            "collected_at": now.isoformat(),
        }
