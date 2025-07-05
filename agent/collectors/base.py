"""Collector base class + simple registry."""
from __future__ import annotations

import abc
from typing import Any, Dict, List, Type

import boto3

_COLLECTORS: List[Type["BaseCollector"]] = []


def register(cls: Type["BaseCollector"]) -> Type["BaseCollector"]:
    """Class decorator to auto-register collector subclasses."""
    _COLLECTORS.append(cls)
    return cls


def get_collectors() -> List[Type["BaseCollector"]]:
    """Return all registered collector classes."""
    return _COLLECTORS


class BaseCollector(abc.ABC):
    """Abstract collector interface."""

    def __init__(self, settings):  # noqa: D401
        self.settings = settings
        self._account_id = None

    # -------- internal helpers -------- #
    def _session(self):
        kw = {}
        if self.settings.profile:
            kw["profile_name"] = self.settings.profile
        if self.settings.region:
            kw["region_name"] = self.settings.region
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            kw["aws_access_key_id"] = self.settings.aws_access_key_id
            kw["aws_secret_access_key"] = self.settings.aws_secret_access_key
            if self.settings.aws_session_token:
                kw["aws_session_token"] = self.settings.aws_session_token
        return boto3.Session(**kw) if kw else boto3.Session()

    def _boto(self, service: str, **kwargs):
        return self._session().client(service, **kwargs)

    @property
    def account_id(self) -> str:
        if self._account_id is None:
            self._account_id = self._boto("sts").get_caller_identity()["Account"]
        return self._account_id

    # -------- lifecycle -------- #
    @abc.abstractmethod
    def discover(self) -> List[Any]:
        """Enumerate resource identifiers (str/obj) this collector can process."""

    @abc.abstractmethod
    def collect(self, resource: Any) -> Dict[str, Any]:
        """Collect metrics/logs for a single resource."""
