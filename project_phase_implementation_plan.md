# Project Phase-Wise Implementation Plan

## Project Goal
Build a production-grade Trading and Financial Advisor platform with strict contracts, a ReAct-style tool-using agent, robust ingestion, persistent memory, observability, and release hardening.

## Delivery Strategy
- Dependency-first rollout where contract and tool abstractions are completed before advanced orchestration.
- Parallel tracks begin only after shared blocking foundations are stable.
- Every phase ends with concrete exit criteria and test evidence.

## Phase 1: Contracts, Guardrails, and Tool Framework Foundation
**Objective**
Create strict schemas, validation rails, and a central tool registry that all later capabilities depend on.

**Scope**
- Tool input/output contracts for market, portfolio, and ingestion tool categories.
- Registry with registration, invocation, typed validation, and standard error envelopes.
- Request and response guardrails (domain and safety checks).

**Deliverables**
- Stable contracts in tool schema module.
- Registry abstraction with handler-level validation.
- Guardrail modules integrated with current agent flow.

**Exit Criteria**
- All tool contracts validate in unit tests.
- Registry rejects invalid input/output and reports deterministic error classes.
- Guardrails block malformed and unsafe payloads.

## Phase 2A: Core Market and Portfolio Tools
**Objective**
Add high-value financial reasoning tools for market lookup and portfolio analysis.

**Scope**
- Market data lookup tool (price snapshot, trend indicators, metadata).
- Portfolio analysis tool (allocation health, concentration, risk profile checks).
- Deterministic fixtures for repeatable tool testing.

**Deliverables**
- Registered tools with typed request/response models.
- Unit test suite covering success and failure paths.

**Exit Criteria**
- Tools pass schema and business-rule tests.
- Tool outputs can be consumed by recommendation composer without ad hoc parsing.

## Phase 2B: Document Ingestion (PDF and CSV)
**Objective**
Support statement/portfolio ingestion from user files with normalized extraction.

**Scope**
- PDF parser for statements and portfolio documents.
- CSV parser for holdings and transaction snapshots.
- Normalization to shared records for downstream reasoning.

**Deliverables**
- Ingestion parser modules and tool wrappers in registry.
- Extracted normalized records with confidence/warnings metadata.

**Exit Criteria**
- Curated sample files produce valid normalized payloads.
- Invalid or empty files fail gracefully with actionable error messages.

## Phase 3: ReAct Agent Executor Loop
**Objective**
Implement a multi-step think-act-observe-refine loop that asks clarifying questions and invokes tools safely.

**Scope**
- State model for intent, missing fields, tool calls, observations, and final response.
- Clarification policy: ask only blocking questions before tool execution.
- Structured recommendation synthesis against strict output schema.

**Deliverables**
- ReAct-style executor integrated in agent runtime.
- Clarification question contract and deterministic question prioritization.

**Exit Criteria**
- Integration test: user query -> clarifying questions -> tool calls -> recommendation.
- Final responses always validate against recommendation schema.

## Phase 4A: Memory Upgrade
**Objective**
Add production-grade session replay and long-term retrieval.

**Scope**
- Persistent conversation memory store.
- Profile and decision memory extensions.
- Retrieval interface for relevant historical context.

**Deliverables**
- Memory store modules with read/write APIs.
- Retrieval hooks used by executor during reasoning.

**Exit Criteria**
- Session continuity works across restarts.
- Historical constraints are retrieved and respected in subsequent recommendations.

## Phase 4B: Observability and Tracing
**Objective**
Instrument end-to-end behavior for debugging, quality, and performance.

**Scope**
- Trace each executor step and tool invocation.
- Record latency, success/failure, confidence, and token consumption.
- Add structured logs for diagnosis and audit readiness.

**Deliverables**
- Observability module with trace schema.
- Basic dashboards or exportable logs.

**Exit Criteria**
- Every user request has a complete step trace.
- Slow/failing segments are measurable and attributable.

## Phase 5: UI and API Expansion
**Objective**
Ship user-facing capabilities around uploads, history, and actionable portfolio insights.

**Scope**
- Upload components for PDF/CSV.
- Recommendation history and portfolio health views.
- Rebalancing alerts and prior-conversation restore by default.

**Deliverables**
- Updated Streamlit UX components and backend handlers.
- API contracts for future web/mobile clients.

**Exit Criteria**
- Users can upload statements and receive structured recommendations in one flow.
- Conversation history and prior constraints are visible and reusable.

## Phase 6: Hardening and Release Readiness
**Objective**
Prepare for production with resiliency, security, and operations readiness.

**Scope**
- Retry/backoff and error categorization.
- Rate limits and abuse safeguards.
- Security checks, secrets handling, and runbooks.

**Deliverables**
- Reliability policies implemented in critical paths.
- Deployment and incident response runbook.

**Exit Criteria**
- Performance budgets met across representative scenarios.
- Regression and safety suites pass in CI.
- Release checklist approved.

## Cross-Phase Verification Matrix
1. Contract verification: schema tests for all tool and response models.
2. Unit validation: each tool tested with deterministic fixtures.
3. Ingestion validation: PDF/CSV parsing quality on curated samples.
4. Loop validation: end-to-end test for ReAct flow.
5. Safety validation: prompt-injection and malformed-input tests.
6. Performance validation: no-tool, single-tool, and multi-tool latency budgets.
7. Regression validation: golden scenarios by user risk profile.

## Milestone Timeline (Suggested)
- Week 1-2: Phase 1 completion.
- Week 3-4: Phase 2A and Phase 2B in parallel.
- Week 5: Phase 3 integration.
- Week 6: Phase 4A and Phase 4B in parallel.
- Week 7: Phase 5 delivery.
- Week 8: Phase 6 hardening and release gate.

## Immediate Next Implementation Steps
1. Finalize tool contracts for market, portfolio, and ingestion categories.
2. Lock registry error envelopes and add missing-field detection APIs.
3. Implement CSV ingestion next to complete Phase 2B baseline.
4. Add ReAct clarification state and single-question policy before tool execution.
5. Add one integration test that proves clarification-first behavior.
