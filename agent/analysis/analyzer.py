from __future__ import annotations

import json
from typing import Any, Dict, List

import ollama

from ..config import Settings
from .pre_analyzer import run_pre_analysis
from . import temporal_analyzer

class Analyzer:
    """Performs AI-powered analysis on collected data."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ollama.Client(host=settings.llm_host)

    def run_analysis(
        self,
        current_results: List[Dict[str, Any]],
        previous_results: List[Dict[str, Any]] = None,
        current_timestamp: datetime = None,
        previous_timestamp_str: str = None,
    ) -> str:
        """Runs the analysis and returns a summary."""
        if not self.settings.llm_provider:
            return "(AI analysis disabled)"

        # Run the pre-analysis to get structured findings from the current data
        static_findings = run_pre_analysis(current_results)

        # Run temporal analysis if previous data is available
        temporal_findings = []
        if previous_results and current_timestamp and previous_timestamp_str:
            temporal_findings = temporal_analyzer.compare_runs(
                current_results,
                previous_results,
                current_timestamp,
                previous_timestamp_str,
            )

        all_findings = static_findings + temporal_findings

        # If there are no findings, we can return a simple message
        if not all_findings:
            return "No significant issues or notable trends were detected in the environment."

        prompt = self._format_prompt_with_findings(all_findings)

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
            -   `### Key Observations`: A brief, high-level summary of the issues and trends.
            -   `### Potential Issues & Trends`: A bulleted list summarizing each finding. Clearly distinguish between static issues (e.g., 'High CPU') and temporal trends (e.g., 'Spike in 5xx Errors').
            -   `### Recommendations`: A bulleted list of actionable recommendations.
        2.  **Do not just repeat the data**. Interpret it. Explain *why* it's a problem. For trends, emphasize the change over time.
        3.  **Be specific**. Refer to the resource names from the findings.

        **Example Output:**

        ### Key Observations

        The environment is showing signs of stress on the main load balancer, which has seen a dramatic spike in errors. Additionally, one of the ElastiCache clusters continues to be used inefficiently.

        ### Potential Issues & Trends

        -   **Trend: Spike in 5xx Errors on `pp-production-lb`**: This load balancer's errors jumped from 5 to 150 in the last 3 hours, indicating a severe and recent degradation in the backend services.
        -   **Issue: Low Cache Hit Rate on `pp-api-production-redis-001`**: This cache's hit rate remains low at 45%, causing unnecessary load on the database.

        ### Recommendations

        -   **Immediately investigate application logs** for services behind `pp-production-lb` to identify the source of the recent 5xx error spike.
        -   **Review the caching logic** for the `pp-api-production` service to improve the cache hit rate.

        **Findings to Summarize:**
        ```json
        {findings_str}
        ```

        Now, provide the report based on the findings and instructions.
        """
