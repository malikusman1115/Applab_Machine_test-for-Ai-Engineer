# Section A - Multitenant Answering over External Data Architecture

## Overview

The system is a multitenant Answering over External Data platform combining RAG, structured tools, and an agentic planner. Each tenant has isolated data, credentials, indexes, audit trails, and usage budgets. The main flow is: authenticate user, authorize tenant and role, classify query, retrieve tenant-grounded context, call approved external tools when needed, synthesize a cited answer, log traces and costs, and run evaluation checks before returning the final response.

## Data ingestion and indexing

Tenant documents enter through batch uploads, SaaS connectors, webhooks, or scheduled sync jobs. Files are normalized into canonical text plus metadata such as tenant ID, document ID, ACLs, source URL, timestamp, sensitivity label, and version. The ingestion pipeline performs parsing, OCR when needed, table extraction, deduplication, PII classification, and document-level hashing.

Chunking uses structure-aware splitting first, with token-based fallback. Headings, tables, code blocks, and semantic sections are preserved where possible. Each chunk stores parent document metadata and ACL filters. Embeddings are generated per chunk and indexed in Azure AI Search or an equivalent vector database. Hybrid retrieval combines BM25, vector search, semantic reranking, metadata filters, freshness boosts, and ACL filters. Indexes can be physically separated per tenant for strict isolation or logically partitioned with tenant-scoped filters for cost efficiency. High-compliance tenants should use dedicated indexes and keys.

## Agentic planner and tools

The planner receives the user query, tenant policy, available tool schemas, and retrieval summary. It emits JSON tool calls only, such as `rag_search`, `web_search`, `weather`, `currency`, `calculator`, or internal business APIs. Tools have explicit schemas, timeout budgets, retry policies, allowed-domain rules, and citation contracts. The planner should not call external tools when tenant data is sufficient, and it should not call tools that are disabled by tenant policy.

A typical plan is: retrieve tenant documents, decide whether the question requires current or external information, call allowed tools in parallel, validate outputs, then synthesize a final answer with citations. The synthesizer is instructed to separate tenant-grounded facts from external facts and to refuse when evidence is insufficient. For production, tool selection should be evaluated with golden datasets and adversarial prompts.

## Cost, latency, and caching

Latency budgets are split across auth, retrieval, tool calls, reranking, and generation. Retrieval and independent tools run concurrently. Prompt caching stores stable system prompts and tenant policy blocks. Vector caching stores repeated query embeddings and frequent retrieval results. HTTP caching stores external tool responses according to TTL and source freshness. Final answer caching is only used for low-risk public queries and must include tenant, user role, policy version, query hash, and source version in the cache key.

Cost controls include per-tenant quotas, token budgets, model routing, small-model planning, larger-model synthesis only when needed, maximum tool calls, truncation policies, and fallback models. Long documents use map-reduce or hierarchical retrieval instead of sending entire files to the model.

## Security and multitenancy

Authentication uses enterprise identity such as Entra ID, OAuth, or SSO. Authorization enforces RBAC and document ACLs before retrieval and again before answer synthesis. Every chunk includes tenant ID and ACL metadata, and every search query applies mandatory filters. Secrets are stored in Key Vault and injected through managed identity. Tenant connectors use separate credentials and rotation policies.

The service blocks cross-tenant cache leakage by including tenant ID and ACL state in all cache keys. Audit logs capture user, tenant, query, tools used, source documents, policy decisions, and generated answer IDs. Sensitive logs are redacted. Network egress is restricted by allowlists, private endpoints, and per-tool policy. Prompt injection defenses include source isolation, instruction hierarchy, tool allowlists, and refusing document instructions that try to override system policy.

## Observability and evaluation

Every request emits distributed traces covering planning, retrieval, reranking, each tool call, synthesis, validation, and response. Metrics include p50/p95 latency, token usage, cache hit rate, retrieval hit rate, answer citation coverage, tool failures, timeouts, cost per tenant, and refusal rate. Dashboards show failures by tool, model, tenant, connector, and deployment version.

Offline evaluation uses golden Q&A sets, retrieval recall, groundedness checks, citation precision, policy compliance, and regression tests. Online evaluation samples answers for human review and automated hallucination checks. Alerts trigger on cost spikes, latency breaches, tool error rates, empty retrieval spikes, and cross-tenant isolation test failures.

## Deployment

The service is containerized and deployed to Azure Container Apps, AKS, or equivalent. Azure Functions can handle ingestion and scheduled connector sync. Azure AI Search stores hybrid indexes, Blob Storage stores raw and normalized documents, Key Vault stores secrets, and Application Insights or OpenTelemetry collects traces.

CI/CD runs unit tests, integration tests, security scans, schema compatibility checks, prompt regression tests, and retrieval evaluations. Deployments use blue/green or canary releases with tenant-level rollout controls. Index migrations are versioned and run side by side before traffic shifts. Rollback includes application version, prompt version, model route, and index alias rollback.

## Production extensions

Next improvements include LLM JSON-mode planning, stronger search providers, tenant-specific evaluation suites, retrieval feedback learning, semantic cache invalidation, connector backpressure, per-tool circuit breakers, human approval for high-risk actions, and deeper data-loss-prevention controls.
