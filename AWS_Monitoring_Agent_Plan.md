# AWS Monitoring Agent - Project Plan

This document outlines the plan, requirements, and technical specifications for building a custom AWS Monitoring Agent.

## 1. Project Goal

The primary goal is to build a script-based agent that provides comprehensive monitoring and anomaly detection for a production AWS environment. The agent will inspect key services, analyze logs, and generate a consolidated text-based report. It is designed to be triggered manually, with future plans for daemonized execution, a public release, and integration with alerting tools.

## 2. User Requirements

This section summarizes the specific requirements gathered.

### 2.1. AWS Configuration & Access
- **Credentials:** The script will check for AWS credentials in the environment. If not found, it will prompt the user to provide them, which will be stored in a `config.ini` file.
- **Region:** The primary monitoring region is `us-east-2`.
- **Account Scope:** Initially, the agent will target a single production account, with the architecture allowing for future expansion to multiple accounts via the configuration file.

### 2.2. Scope & Monitored Resources
- **ECS:** Monitor all available ECS clusters.
- **RDS:** Monitor all available RDS instances (initially, with future support for Aurora).
- **OpenSearch:** Monitor all available OpenSearch domains.
- **CloudFormation:** Monitor stacks with a name prefix of `pp` and a suffix of `production`.

### 2.3. Log Monitoring & Anomaly Detection
- **Log Sources:**
    - ECS container logs (from CloudWatch)
    - RDS logs
    - DMS logs
    - WAF logs
- **Anomaly Definition:** The custom logic will search for:
    - Error rate spikes
    - 4xx and 5xx HTTP status codes
    - Language-specific errors (e.g., stack traces)
    - Performance degradation patterns
- **Monitoring Cadence:** Initially, the tool will be triggered manually. The discussion around real-time monitoring vs. periodic checks leans towards a configurable, triggered execution model. The agent should be able to analyze logs from the past 3 months.
- **Implementation:** Anomaly detection will be based on custom logic, driven by configurable patterns, rather than relying on AWS CloudWatch Anomaly Detection.

### 2.4. System & Service Information
- **Metrics:**
    - Standard system metrics: CPU, memory, disk, network utilization.
    - Service metrics: ALB/Listener data, including Target Response Time (TRT).
- **Source:** Metrics will be gathered from CloudWatch for services running on ECS.

### 2.5. Output & Integration
- **Reporting:** The primary output will be a consolidated, text-based report suitable for sharing. A UI/dashboard is a future goal.
- **Integrations:** No third-party integrations (Slack, PagerDuty) are required for the initial version.
- **Data Storage:** The agent will not store historical data to avoid management overhead. Reports are generated on-demand.

### 2.6. Technical Preferences
- **Language:** Python.
- **AI/ML Model:** The use of local (Ollama) vs. cloud (OpenAI) models is a future consideration, not part of the initial build.
- **Execution Model:** The agent will be a trigger-based script. A daemon/service model is a future option.
- **Deployment:** The application should be containerized using Docker.

## 3. Plan of Action

The project will be developed in the following phases.

**Phase 1: Project Foundation & Configuration**
1.  Establish the project directory structure.
2.  Create a `config.ini` to store AWS credentials, region, and resource filters.
3.  Develop a Python module to read the configuration and initialize a `boto3` session.
4.  Set up a `requirements.txt` file, starting with `boto3`.

**Phase 2: Resource Discovery**
1.  Implement a function to list CloudFormation stacks filtered by the configured prefix and suffix.
2.  Implement functions to list all ECS clusters, RDS instances, and OpenSearch domains.

**Phase 3: Data Collection & Analysis**
1.  Implement functions to fetch CloudWatch metrics (CPU, Memory, 5xx errors) for discovered resources.
2.  Implement functions to fetch and filter CloudWatch logs based on a configurable list of keywords (e.g., "ERROR", "Exception", "timeout").
3.  Develop the custom anomaly detection logic (metric threshold comparison and log keyword matching).

**Phase 4: Reporting**
1.  Structure all collected data into a single Python dictionary.
2.  Write a function to format this dictionary into a clean, human-readable text report.

**Phase 5: Main Orchestrator (`main.py`)**
1.  Write the main script to orchestrate the process: initialize session, discover resources, run analysis, and generate the final report.

## 4. Tech Stack

- **Language:** Python 3.9+
- **AWS SDK:** Boto3
- **Configuration:** Python's built-in `configparser` library
- **Containerization:** Docker

## 5. Key References

- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)

