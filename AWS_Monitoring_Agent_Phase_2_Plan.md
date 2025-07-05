# AWS Monitoring Agent - Phase 2: Advanced Features

This document outlines the plan for extending the AWS Monitoring Agent with advanced monitoring, anomaly detection, and cost analysis capabilities.

## Core Objectives
- **Deepen Monitoring:** Move beyond basic CloudWatch metrics to service-specific and performance-level data (Performance Insights, ElastiCache, WAF).
- **Automated Anomaly Detection:** Proactively identify issues by analyzing logs.
- **Cost Optimization:** Provide insights into AWS costs and recommendations for savings.
- **AI-Powered Insights:** Leverage LLMs to summarize findings and provide actionable recommendations.

## Proposed Implementation Plan

### 1. Log Anomaly Detection & ALB Monitoring
- **ECS Log Analysis:** Enhance the `ECSCollector` to scan service log groups for error keywords.
- **ALB/Target Group Collector:** Create a new collector for Application Load Balancers to monitor HTTP error codes and unhealthy hosts.

### 2. Deep Database & Data Service Monitoring
- **RDS Performance Insights:** Enhance the `RDSCollector` to pull data from Performance Insights, identifying slow queries and database load.
- **OpenSearch Internals:** Enhance the `OpenSearchCollector` to connect to the cluster endpoint and gather data on indices, documents, and shards.

### 3. Expanded Service Coverage
- **ElastiCache Collector:** Add a new collector for Redis/Memcached.
- **WAF & DMS Collectors:** Add support for AWS WAF and Database Migration Service.

### 4. Cost Analysis & AI Integration
- **Cost Collector:** Integrate with AWS Cost Explorer to report on service costs.
- **AI Summarizer:** Use the generated JSON report as context for an LLM (like OpenAI or a local Ollama model) to produce an executive summary with actionable insights.
