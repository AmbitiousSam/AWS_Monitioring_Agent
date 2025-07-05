from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .base import BaseCollector, register


@register
class RDSCollector(BaseCollector):
    namespace = "rds"

    def discover(self) -> List[str]:
        """Discover all RDS instance identifiers."""
        if "*" in self.settings.rds_instances:
            rds = self._boto("rds")
            instances = rds.describe_db_instances()["DBInstances"]
            return [i["DBInstanceIdentifier"] for i in instances]
        return self.settings.rds_instances

    def _get_performance_insights(self, resource_id: str, since: dt.datetime, now: dt.datetime) -> Dict[str, Any]:
        """Get Performance Insights data for an RDS instance."""
        pi = self._boto("pi")
        rds = self._boto("rds")

        try:
            instance = rds.describe_db_instances(DBInstanceIdentifier=resource_id)["DBInstances"][0]
            if not instance.get("PerformanceInsightsEnabled"):
                return {"status": "disabled"}
            dbi_resource_id = instance["DbiResourceId"]
        except (rds.exceptions.DBInstanceNotFoundFault, IndexError):
            return {"status": "not_found"}

        try:
            response = pi.get_resource_metrics(
                ServiceType='RDS',
                Identifier=dbi_resource_id,
                MetricQueries=[
                    {
                        'Metric': 'db.load.avg',
                        'GroupBy': {'Group': 'db.sql'}
                    },
                ],
                StartTime=since,
                EndTime=now,
                PeriodInSeconds=3600,
            )
            
            top_queries = []
            if response.get('MetricList'):
                metric_points = response['MetricList'][0].get('DataPoints', [])
                for point in metric_points:
                    if point.get('Dimensions'):
                        sql_text = point['Dimensions'].get('db.sql.statement', 'N/A')
                        truncated_sql = (sql_text[:150] + '...') if len(sql_text) > 150 else sql_text
                        top_queries.append({
                            "sql": truncated_sql,
                            "load": round(point['Value'], 4)
                        })
            
            top_queries = sorted(top_queries, key=lambda x: x['load'], reverse=True)[:5]

            return {
                "status": "enabled",
                "top_queries": top_queries
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def collect(self, resource_id: str) -> Dict[str, Any]:
        """Collect metrics for a single RDS instance."""
        cw = self._boto("cloudwatch")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        def _get_metric(metric_name):
            stats = cw.get_metric_statistics(
                Namespace="AWS/RDS",
                MetricName=metric_name,
                Dimensions=[{"Name": "DBInstanceIdentifier", "Value": resource_id}],
                StartTime=since,
                EndTime=now,
                Period=3600,
                Statistics=["Average"],
            )
            points = stats.get("Datapoints", [])
            return round(points[0]["Average"], 2) if points else 0.0

        pi_data = self._get_performance_insights(resource_id, since, now)

        return {
            "namespace": self.namespace,
            "resource": resource_id,
            "cpu_utilization": _get_metric("CPUUtilization"),
            "freeable_memory": _get_metric("FreeableMemory"),
            "db_connections": _get_metric("DatabaseConnections"),
            "performance_insights": pi_data,
            "collected_at": now.isoformat(),
        }
