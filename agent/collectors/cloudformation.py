from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from .base import BaseCollector, register


@register
class CloudFormationCollector(BaseCollector):
    namespace = "cloudformation"

    def discover(self) -> List[str]:
        """Discover all CloudFormation stack names."""
        cf = self._boto("cloudformation")
        stacks = cf.list_stacks(StackStatusFilter=[
            'CREATE_COMPLETE',
            'UPDATE_COMPLETE',
            'UPDATE_ROLLBACK_COMPLETE',
            'DELETE_FAILED',
            'UPDATE_ROLLBACK_FAILED',
        ])["StackSummaries"]
        names = [s["StackName"] for s in stacks]

        if self.settings.cloudformation_stack_prefix != "*":
            names = [n for n in names if n.startswith(self.settings.cloudformation_stack_prefix)]
        if self.settings.cloudformation_stack_suffix != "*":
            names = [n for n in names if n.endswith(self.settings.cloudformation_stack_suffix)]

        return names

    def collect(self, resource_id: str) -> Dict[str, Any]:
        """Collect details for a single CloudFormation stack."""
        cf = self._boto("cloudformation")
        stack = cf.describe_stacks(StackName=resource_id)["Stacks"][0]
        now = dt.datetime.utcnow()

        return {
            "namespace": self.namespace,
            "resource": resource_id,
            "stack_status": stack["StackStatus"],
            "last_updated_time": stack.get("LastUpdatedTime", stack["CreationTime"]).isoformat(),
            "collected_at": now.isoformat(),
        }
