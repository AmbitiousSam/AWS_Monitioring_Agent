from __future__ import annotations

import json
from typing import Any, Dict, List

import ollama

from ..config import Settings
from .pre_analyzer import run_pre_analysis


class Analyzer:
    """Performs AI-powered analysis on collected data."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ollama.Client(host=settings.llm_host)

    def run_analysis(self, collected_data: List[Dict[str, Any]]) -> str:
        """Runs the analysis and returns a summary."""
        if not self.settings.llm_provider:
            return "(AI analysis disabled)"

        # Run the pre-analysis to get structured findings
        findings = run_pre_analysis(collected_data)

        # If there are no findings, we can return a simple message
        if not findings:
            return "No significant issues were detected in the environment based on the current rules."

        prompt = self._format_prompt_with_findings(findings)

        try:
            response = self.client.chat(
                model=self.settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"]
        except ollama.ResponseError as e:
            if e.status_code == 404:  # Model not found
                return f"Error: The model '{self.settings.llm_model}' was not found on the ollama server. Please run `ollama pull {self.settings.llm_model}`."
            return f"Error during analysis: {e}"
        except Exception as e:
            return f"Error during analysis: {e}"

    def _format_prompt_with_findings(self, findings: List[Dict[str, Any]]) -> str:
        findings_str = json.dumps(findings, indent=2)
        return f"""
        You are an expert AWS Site Reliability Engineer (SRE). Your task is to convert the following list of JSON findings into a human-readable, Markdown-formatted executive summary.

        **CRITICAL INSTRUCTIONS:**
        1.  **Use the EXACT following Markdown structure**:
            -   `### Key Observations`: A brief, high-level summary of the issues.
            -   `### Potential Issues`: A bulleted list summarizing each finding.
            -   `### Recommendations`: A bulleted list of actionable recommendations.
        2.  **Do not just repeat the data**. Interpret it. Explain *why* it's a problem.
        3.  **Be specific**. Refer to the resource names from the findings.

        **Example Output:**

        ### Key Observations

        The environment is showing signs of stress on the main load balancer and one of the ElastiCache clusters. The primary database is performing well, but a read replica has elevated CPU.

        ### Potential Issues

        -   **High 5xx Errors on `pp-production-lb`**: This load balancer is experiencing a high number of server-side errors, which could indicate application-level bugs.
        -   **Low Cache Hit Rate on `pp-api-production-redis-001`**: This cache is not being used effectively, leading to unnecessary load on the backend services.
        -   **Elevated CPU on `enf-production-db-read`**: The CPU on this read replica is higher than expected, which may be caused by inefficient queries.

        ### Recommendations

        -   **Investigate application logs** for the services behind `pp-production-lb` to identify the source of the 5xx errors.
        -   **Review the caching logic** for the `pp-api-production` service to improve the cache hit rate.
        -   **Analyze slow query logs** on the `enf-production-db` to identify and optimize inefficient queries affecting the read replica.

        **Findings to Summarize:**
        ```json
        {findings_str}
        ```

        Now, provide the report based on the findings and instructions.
        """
