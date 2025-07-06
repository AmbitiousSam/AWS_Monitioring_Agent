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

    def _get_metric_history(
        self, cw, metric_name: str, resource_id: str, stat: str
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
                            "Namespace": "AWS/RDS",
                            "MetricName": metric_name,
                            "Dimensions": [{
                                "Name": "DBInstanceIdentifier", 
                                "Value": resource_id
                            }],
                        },
                        "Period": 86400,  # Daily resolution
                        "Stat": stat,
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
        """Collect metrics for a single RDS instance."""
        cw = self._boto("cloudwatch")
        now = dt.datetime.utcnow()
        since = now - dt.timedelta(hours=self.settings.lookback_hours)

        # Define metrics to fetch for the current period
        metric_definitions = {
            "CPUUtilization": "Average",
            "FreeableMemory": "Average",
            "DatabaseConnections": "Average",
        }

        metric_data_queries = [
            {
                "Id": f"m{i}",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/RDS",
                        "MetricName": metric_name,
                        "Dimensions": [{
                            "Name": "DBInstanceIdentifier", 
                            "Value": resource_id
                        }],
                    },
                    "Period": self.settings.lookback_hours * 3600,
                    "Stat": stat,
                },
                "ReturnData": True,
            }
            for i, (metric_name, stat) in enumerate(metric_definitions.items())
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

        # Fetch historical metrics for temporal analysis
        cpu_history = self._get_metric_history(
            cw, "CPUUtilization", resource_id, "Average"
        )

        pi_data = self._get_performance_insights(resource_id, since, now)

        return {
            "namespace": self.namespace,
            "resource": resource_id,
            "cpu_utilization": current_metrics.get("CPUUtilization", 0.0),
            "cpu_utilization_history": cpu_history,
            "freeable_memory": current_metrics.get("FreeableMemory", 0.0),
            "db_connections": current_metrics.get("DatabaseConnections", 0.0),
            "performance_insights": pi_data,
            "collected_at": now.isoformat(),
        }
