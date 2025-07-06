"""
Configuration loader for AWS-Diag-Agent.

Priority (highest → lowest):
1. CLI overrides                      (passed in collect() call)
2. Environment variables              (e.g. AWS_DIAG_LOOKBACK_HOURS)
3. config.ini                         (project root or $XDG_CONFIG_HOME/aws-diag)
4. Code defaults                      (see DEFAULTS)
"""
from __future__ import annotations
from configparser import NoOptionError, NoSectionError

import os
from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

CONFIG_FILENAMES = ("config.ini", ".aws-diag.ini")
DEFAULTS = {
    "aws.profile": "",
    "aws.lookback_hours": "3",
    "aws.temporal_lookback_days": "14",
    "aws.threads": "0",  # 0 = auto
    "ecs.clusters": "*",
    "alb.names": "*",

    "ecs.log_keywords": "FATAL,ERROR,Exception,Traceback,5xx,4xx,Timeout,Connection",
    "aws.region": "us-east-2",
    "rds.instances": "*",
    "opensearch.domains": "*",
    "elasticache.clusters": "*",
    "waf.web_acls": "*",
    "llm.provider": "ollama",
    "llm.model": "llama3",
    "llm.host": "http://localhost:11434",
    "cloudformation.stack_prefix": "*", 
    "cloudformation.stack_suffix": "*",
    "aws.aws_access_key_id": "",
    "aws.aws_secret_access_key": "",
    "aws.aws_session_token": "",
}


def _search_config_file() -> Path | None:
    """Return first existing config file path or None."""
    paths = [
        Path.cwd() / name for name in CONFIG_FILENAMES
    ] + [
        Path.home() / ".config" / "aws-diag" / "config.ini"
    ]
    return next((p for p in paths if p.exists()), None)


@dataclass(slots=True)
class Settings:
    profile: str
    region: str
    lookback_hours: int
    temporal_lookback_days: int
    threads: int
    log_keywords: List[str]
    rds_instances: List[str]
    opensearch_domains: List[str]
    elasticache_clusters: List[str]
    cloudformation_stack_prefix: str
    cloudformation_stack_suffix: str
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None
    ecs_clusters: List[str] = field(default_factory=lambda: ["*"])
    alb_names: List[str] = field(default_factory=lambda: ["*"])
    waf_web_acls: List[str] = field(default_factory=lambda: ["*"])
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_host: str | None = None

    @classmethod
    def load(cls, cli_overrides: dict | None = None) -> "Settings":
        overrides = cli_overrides or {}
        parser = ConfigParser()
        structured = {}
        for dotted_key, value in DEFAULTS.items():
            section, option = dotted_key.split(".")
            structured.setdefault(section, {})[option] = value
        parser.read_dict(structured)

        if cfg := _search_config_file():
            parser.read(cfg)

        # env > ini

        def _get(dotted_key: str, default: str | None = None) -> str:
            """
            Resolve a config value with precedence:
            1) CLI overrides  2) AWS_DIAG_* env var  3) config.ini  4) DEFAULTS
            """
            # 1. CLI override
            if dotted_key in overrides and overrides[dotted_key] is not None:
                return overrides[dotted_key]

            # 2. Environment variable
            env_key = f"AWS_DIAG_{dotted_key.replace('.', '_').upper()}"
            if env_val := os.getenv(env_key):
                return env_val

            # 3. config.ini (parser has DEFAULTS as fallback)
            section, option = dotted_key.split(".")
            if parser.has_option(section, option):
                return parser.get(section, option)

            # 4. Function's default parameter
            if default is not None:
                return default

            # 5. DEFAULTS dict as last resort
            return DEFAULTS.get(dotted_key, "")

        clusters_raw = _get("ecs.clusters").strip()
        alb_raw = _get("alb.names").strip()
        rds_raw = _get("rds.instances").strip()
        opensearch_raw = _get("opensearch.domains").strip()
        elasticache_raw = _get("elasticache.clusters").strip()
        waf_raw = _get("waf.web_acls").strip()
        llm_provider_raw = _get("llm.provider").strip()
        llm_model_raw = _get("llm.model").strip()
        llm_host_raw = _get("llm.host").strip()
        log_keywords_raw = _get("ecs.log_keywords").strip()
        return cls(
            profile=_get("aws.profile").strip(),
            region=_get("aws.region").strip(),
            lookback_hours=int(_get("aws.lookback_hours")),
            temporal_lookback_days=int(_get("aws.temporal_lookback_days")),
            threads=int(_get("aws.threads")),
            ecs_clusters=[c.strip() for c in clusters_raw.split(",")] if clusters_raw else ["*"],
            alb_names=[n.strip() for n in alb_raw.split(",")] if alb_raw else ["*"],
            log_keywords=[k.strip() for k in log_keywords_raw.split(",") if k.strip()],
            rds_instances=[i.strip() for i in rds_raw.split(",")] if rds_raw else ["*"],
            opensearch_domains=[d.strip() for d in opensearch_raw.split(",")] if opensearch_raw else ["*"],
            elasticache_clusters=[c.strip() for c in elasticache_raw.split(",")] if elasticache_raw else ["*"],
            waf_web_acls=[w.strip() for w in waf_raw.split(",")] if waf_raw else ["*"],
            llm_provider=llm_provider_raw or None,
            llm_model=llm_model_raw or None,
            llm_host=llm_host_raw or None,
            cloudformation_stack_prefix=_get("cloudformation.stack_prefix").strip(),
            cloudformation_stack_suffix=_get("cloudformation.stack_suffix").strip(),
            aws_access_key_id=_get("aws.aws_access_key_id", "").strip() or None,
            aws_secret_access_key=_get("aws.aws_secret_access_key", "").strip() or None,
            aws_session_token=_get("aws.aws_session_token", "").strip() or None,
        )
