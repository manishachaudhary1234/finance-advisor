## Plan: Production Trading & Financial Agent

Build a production-ready wealth advisor by evolving the current Streamlit + ADK prototype into a modular agent platform with strict schemas, tool-based reasoning, persistent memory, guardrails, and full observability. Implement in phases so each phase is independently testable and reduces risk before adding more capabilities.

**Steps**
1. Phase 1: Contracts, guardrails, and tool framework foundation. Define strict input/output schemas for profile, tool calls, and recommendations. Add request validation and output sanity checks before expanding agent behavior.
2. Implement a tool registry and tool I/O contracts. This is the controlling abstraction for all future market, portfolio, and ingestion tools. This phase blocks most downstream work.
3. Phase 2A (parallel): Build core market and portfolio tools. Start with market lookup and portfolio analysis tools needed for recommendation reasoning.
4. Phase 2B (parallel with step 3): Build document ingestion for bank statements and portfolio files (CSV/PDF), with validation and extraction into normalized schema fields.
5. Phase 3 (depends on 1-4): Implement multi-step agent executor loop. Add think-act-observe-refine flow: profile/context load, tool selection, tool execution, validation, and final structured recommendation synthesis.
6. Phase 4A (parallel): Upgrade memory layer for production session replay and long-term retrieval. Add conversation persistence and semantic retrieval for decisions and user constraints.
7. Phase 4B (parallel with step 6): Add observability and decision tracing. Capture latency, token usage, tool success/failure, recommendation confidence, and full step traces.
8. Phase 5 (depends on 5-7): Expand UI and API surfaces for uploads, recommendation history, portfolio health, and rebalancing alerts. Ensure session continuity and previous conversation restore by default.
9. Phase 6: Hardening and release readiness. Add resilience (retries, backoff, error categorization), security controls, rate limits, and production runbooks.

**Relevant files**
- c:\Learning\finance-advisor\src\agent\graph.py — current ADK chatbot + profile extraction baseline to split into modular node handlers/executor.
- c:\Learning\finance-advisor\src\agent\state.py — expand state model to include tool calls, intermediate analyses, and validation outcomes.
- c:\Learning\finance-advisor\src\memory\profile_store.py — existing long-term profile persistence; keep as canonical profile layer.
- c:\Learning\finance-advisor\src\memory\events_store.py — existing event timeline; extend for recommendation and rebalance events.
- c:\Learning\finance-advisor\app.py — current UI, session behavior, and conversation list; extend with uploads, history restore, and actionable recommendation panels.
- c:\Learning\finance-advisor\config.py — extend typed config for tool providers, storage backends, limits, and observability backends.
- c:\Learning\finance-advisor\config.yml — declare environment-specific backends, market source, rate limits, and memory retention.
- c:\Learning\finance-advisor\src\tools\registry.py — new central tool registration/discovery and invocation validation.
- c:\Learning\finance-advisor\src\tools\schemas\tool_definitions.py — new pydantic contracts for tool requests/responses.
- c:\Learning\finance-advisor\src\schemas\recommendation.py — new structured recommendation response contract.
- c:\Learning\finance-advisor\src\ingestion\parsers\pdf_parser.py — new PDF statement ingestion pipeline.
- c:\Learning\finance-advisor\src\ingestion\parsers\csv_parser.py — new CSV portfolio ingestion pipeline.
- c:\Learning\finance-advisor\src\memory\conversation_store.py — new persistent session conversation storage.
- c:\Learning\finance-advisor\src\memory\embedding_store.py — new semantic long-term retrieval layer.
- c:\Learning\finance-advisor\src\observability\tracing.py — new agent/tool trace capture.
- c:\Learning\finance-advisor\tests\integration\test_agent_loop.py — new end-to-end loop validation.

**Verification**
1. Contract verification: schema validation tests for all tool inputs/outputs and recommendation payloads.
2. Unit validation: each tool module tested with deterministic fixtures and failure-mode cases.
3. Ingestion validation: PDF/CSV parser accuracy on curated sample statements and holdings snapshots.
4. Loop validation: integration test for full query flow (profile load -> tools -> recommendation -> memory writes).
5. Safety validation: prompt-injection and malformed-file tests to confirm guardrails reject unsafe inputs.
6. Performance validation: latency budgets by scenario (no tool, single tool, multi-tool, ingestion path).
7. Regression validation: golden user scenarios for low/medium/high risk users and changing goals.

**Decisions**
- Included scope: production-grade recommendation loop, structured outputs, upload ingestion, memory, observability, and hardening.
- Excluded initial scope: broker execution/trading automation and guaranteed real-time tick infrastructure.
- Architecture direction: keep current ADK baseline and migrate incrementally to modular executor + tool registry.
- Delivery strategy: dependency-first phased rollout with parallel tracks after core contracts are stable.

**Further Considerations**
1. Market source decision: start with free market providers for MVP vs paid providers for reliability/compliance.
2. Retrieval backend decision: local vector store for MVP vs managed vector DB for scale.
3. Retention/compliance decision: finalize conversation/profile retention windows and deletion policy before production launch.
