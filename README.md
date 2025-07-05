# AWS Diagnostic Agent

**Goal:** A lightweight, extensible, and container-friendly agent that monitors AWS environments, performs intelligent analysis on collected data, and generates concise, actionable executive summary reports.

This agent uses a hybrid AI approach, combining rule-based pre-analysis with local LLM-powered summarization to deliver high-quality insights without sending sensitive data to external services.

## Features

- **Comprehensive Data Collection:** Gathers metrics and configuration data from key AWS services:
  - ECS (including CloudWatch Logs)
  - Application Load Balancers (ALB)
  - RDS
  - OpenSearch
  - ElastiCache (Redis)
  - WAF
  - CloudFormation
- **Hybrid AI Analysis:**
  - **Rule-Based Pre-analyzer:** Deterministically checks for common issues like high error rates, resource saturation, misconfigurations, and performance degradation.
  - **LLM-Powered Summarization:** Uses a local LLM (e.g., Ollama with Llama 3) to generate a human-readable executive summary from the pre-analyzer's findings.
- **Extensible:** Easily add new collectors and analysis rules.
- **Secure:** Keeps all data, including metrics and analysis, local. No data is sent to third-party APIs.
- **Flexible Reporting:** Generates both detailed JSON and clean Markdown reports.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd aws-monitoring-agent
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Set up a local LLM (if you haven't already):**
    This agent is designed to work with [Ollama](https://ollama.ai/). Follow their instructions to install it and pull a model.
    ```bash
    ollama pull llama3
    ```

## How to Run

Ensure your AWS credentials are set up correctly in your environment or via a profile.

```bash
python -m agent.cli collect --profile <your-aws-profile>
```

Reports will be saved to the `reports/` directory by default.

## Configuration (`config.ini`)

For persistent settings, create a `config.ini` file in the project root. The agent will automatically load it. Here is a commented example:

```ini
# config.ini

[aws]
# (Optional) The AWS profile to use for credentials.
# If omitted, relies on standard AWS credential chain (env vars, etc.).
profile = default

# The AWS region to target.
region = us-east-2

# How many hours back to look for metrics.
lookback_hours = 3

# Number of threads for concurrent data collection. 0 means auto-detect.
threads = 0

# (Optional) Explicit AWS credentials. Not recommended; use profiles instead.
# aws_access_key_id =
# aws_secret_access_key =
# aws_session_token =

[ecs]
# Comma-separated list of ECS cluster names to monitor. '*' means all.
clusters = *

# Comma-separated list of keywords to search for in CloudWatch Logs.
log_keywords = FATAL,ERROR,Exception,Traceback,5xx,4xx,Timeout,Connection

[alb]
# Comma-separated list of ALB names to monitor. '*' means all.
names = *

[rds]
# Comma-separated list of RDS instance identifiers. '*' means all.
instances = *

[opensearch]
# Comma-separated list of OpenSearch domain names. '*' means all.
domains = *

[elasticache]
# Comma-separated list of ElastiCache cluster IDs. '*' means all.
clusters = *

[waf]
# Comma-separated list of WAF Web ACL names. '*' means all.
web_acls = *

[cloudformation]
# Filter stacks by a prefix or suffix. '*' means all.
stack_prefix = *
stack_suffix = *

[llm]
# The LLM provider to use. Currently 'ollama' is supported.
provider = ollama

# The model to use for summarization.
model = llama3

# The host for the Ollama API.
host = http://localhost:11434
```
