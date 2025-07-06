from __future__ import annotations

import json
import datetime as dt
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
        current_timestamp: dt.datetime = None,
    ) -> str:
        """Runs the analysis and returns a summary."""
        if not self.settings.llm_provider:
            return "(AI analysis disabled)"

        # Run the pre-analysis to get structured findings from the current data
        static_findings = run_pre_analysis(current_results)

        # Run temporal analysis. Historical data is now embedded in the results.
        temporal_findings = temporal_analyzer.analyze(
            current_results,
            self.settings,
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
            -   `### Key Observations`: A brief, high-level summary of the most critical issues and trends.
            -   `### Potential Issues & Trends`: A bulleted list summarizing each finding.
            -   `### Recommendations`: A bulleted list of actionable recommendations.
        2.  **MANDATORY: Use Verbatim Explanations**: For each finding, you MUST use the provided `explanation` field from the JSON data as the main description. This is not a suggestion. You are required to use the text from the `explanation` field without any modification.
        3.  **Handle Data Quality Notices**: If a `data_quality_notice` field is present and not empty, you MUST append its content to the end of the explanation.
        4.  **Incorporate Confidence**: Append the `confidence` score in parentheses at the end of the finding's title, like `(Confidence: 90%)`.
        5.  **Be Specific**: Refer to the resource names (`resource_id`) from the findings.
        6.  **Do Not Interpret**: Do not add your own interpretation or summary of the findings. Your only job is to format the provided data into the specified Markdown structure.

        **Example Output:**

        ### Key Observations

        The environment is showing signs of stress on the main load balancer, which has seen a dramatic spike in errors. Additionally, one of the ElastiCache clusters continues to be used inefficiently, with a high number of evictions.

        ### Potential Issues & Trends

        -   **Trend: Spike in 5xx Errors on `pp-production-lb` (Confidence: 90%)**: The metric 'ALB 5xx Errors' increased significantly to 150.00 over the last 1.0 hours, which is 3.1 standard deviations from the historical average of 10.00.
        -   **Issue: High Eviction Count on `pp-api-production` (Confidence: 85%)**: There have been 1,500 evictions, indicating the cache may be too small for the workload. This can lead to increased latency and database load.

        ### Recommendations

        -   **Immediately investigate application logs** for services behind `pp-production-lb` to identify the source of the recent 5xx error spike.
        -   **Review the caching logic and consider resizing** the `pp-api-production` cluster to reduce evictions.

        **Findings to Summarize:**
        ```json
        {findings_str}
        ```

        Now, provide the report based on the findings and instructions.
        """
