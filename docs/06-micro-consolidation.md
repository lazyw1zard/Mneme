# Micro-Consolidation Slice

Slice: 3.1

Status: implemented logical minimum for unread-active review packets

This slice tests how Mneme can ask a host-provided live contour/agent to review a small active mnion packet without making Hermes part of the ontology.

The implementation began with a deliberately provisional `latest active` packet. The current logical minimum uses unread-active coverage, compact agent-facing packets, and a derived review-state boundary that may later be materialized in SQLite without exposing SQL to the agent.

## Agentic call

```text
pre-capture filtering can catch local duplicates,
but semantic confirmation needs a bounded live review pass.
```

The first probe was deliberately small:

```text
latest active mnions
  -> portable MicroConsolidationRequest
  -> host-provided agent callable
  -> one ConsolidatedContour(summary, valence, member_ids, rationale)
```

Current 3.1 behavior:

```text
active mnions
  -> review_state/read-model
  -> unread active coverage packet
  -> compact MicroConsolidationRequest
  -> host-provided agent callable
  -> one candidate ConsolidatedContour or structured no-candidate/error
```

It does not write durable memory, kernel notes, engrams, embeddings, or graph nodes.

## Python API

```python
from mnion.micro_consolidation import run_micro_consolidation

result = run_micro_consolidation(
    ledger_path="/path/to/mnions.jsonl",
    state_path="/path/to/mneme_seq.json",
    agent=my_agent_callable,
    packet_limit=10,
)
```

The agent receives a `MicroConsolidationRequest`:

```text
mnions                  bounded unread active MnionRecord objects, default limit 10
prompt                  portable review prompt
expected_output_schema  summary / valence / member_ids / rationale
reason                  why the review packet was prepared
packet_limit            requested review packet size / queue step
selection               compact selection metadata / coverage counters
```

Expected agent return shape:

```json
{
  "summary": "shared meaning across selected mnions",
  "valence": 0.73,
  "member_ids": ["mnion_a", "mnion_b"],
  "rationale": "optional reason for the semantic grouping"
}
```

`ConsolidatedContour` is an experimental object, not a promotion target. It also should not be injected into the live agent as full context by default. The next slice should turn consolidation into a minimal pointer first.

## Selection and token budget

The real selection policy is email-like coverage, not newest-N recency:

```text
first pass: all active unread mnions, chunked by packet limit
later passes: unread active mnions plus explicit needs_rereview
priority bump: high valence / high reinforcement / linked pressure
fairness: oldest unread active mnions must not starve
```

The agent should receive only:

```text
selected compact mnions
selection reason
coverage counters
expected output schema
```

The agent should not receive:

```text
full mnion ledger
all review receipts
SQLite rows
SQL query access
manual id-diff work
```

This keeps review passes short, bounded, and semantic. Storage/index work belongs behind compact paws/tools.

Minimal selection metadata:

```text
MicroConsolidationSelection(
  strategy="unread_active_coverage",
  reason,
  selected_ids,
  unread_active_count,
  reviewed_active_count,
  deferred_count,
  backend="derived_jsonl" | "sqlite_read_model"
)
```

Implemented minimal API:

```python
from mnion.micro_consolidation import (
    derive_review_state,
    prepare_micro_consolidation_request,
    select_unread_active_mnions,
)

review_state = derive_review_state(review_receipts)
packet = select_unread_active_mnions(active_mnions, review_state, packet_limit=10)
request = prepare_micro_consolidation_request(
    ledger_path="/path/to/mnions.jsonl",
    review_receipts=review_receipts,
    packet_limit=10,
)
```

Current statuses:

```text
missing state   -> unread
reviewed        -> skipped by normal selection
deferred        -> skipped by normal selection
needs_rereview  -> eligible
```

## SQLite/read-model boundary

SQLite is allowed as an internal read model when it makes active/unread selection, pressure checks, and queue maintenance simpler. It must remain reconstructable from append-only evidence:

```text
mnion records + review receipts
  -> derived read model
  -> optional SQLite materialization
  -> compact tool packet
  -> agent semantic review
```

SQLite may store:

```text
review_state
active/unread/deferred/needs_rereview indexes
pressure counters
pending consolidation queue
review receipt items for fast audit lookup
```

SQLite must not become:

```text
agent-facing SQL interface
hidden semantic ontology
automatic promotion system
automatic model-calling worker
```

The first worker, if added, should be model-free: maintain the read model and queue only. Semantic consolidation remains an explicit agent/tool action until the pointer, receipt, cooling, and governance boundaries are stable.

## Failure behavior

The host contour/agent call is wrapped in a try/except boundary.

If the call fails:

```text
MicroConsolidationResult.ok = False
error.reason = "agent_call_failed"
```

If the agent returns an invalid shape:

```text
MicroConsolidationResult.ok = False
error.reason = "invalid_agent_response"
```

No ledger events are written in this first slice. Later slices may add a separate validated `review_apply` step for append-only `semantic_link`, `semantic_reinforcement`, `cluster_summary`, or `cooling` events.

## Next slice: 3.2 Pointer

The correct next object is not a merged mnion and not an active recollection with full context. It is a metamemory pointer:

```text
I know that I know this.
```

Planned flow:

```text
ConsolidatedContour
  -> MemoryPointer(claim, route, source_handles, valence, confidence, guards)
  -> agent ingress receives pointer only
  -> agent explicitly requests full context/brief if it judges the pointer relevant
```

This preserves the core Mneme shape:

```text
metamemory pointer
  + affect salience
  + retrieval route
  + confidence / warmth
  + reconsolidation state
  + governance boundary
```

Do not skip from 3.1 to rich active-return context. Pointer-first return is the minimal correct closure path.

## Portability boundary

Core Mneme prepares and validates the review packet. It does not assume which host performs the live review.

Possible future adapters:

```text
ManualPromptInvoker     returns/prints prompt artifact
McpSamplingInvoker      uses sampling/createMessage when supported
HermesInvoker           Hermes-specific adapter, not core ontology
DirectModelInvoker      optional direct provider API adapter
NoopInvoker             reports review_due without calling a model
```

MCP prompts/sampling are useful adapter surfaces, but not required by this core API.

## Verification

Implemented tests cover:

```text
prepare request returns bounded unread active mnions
run_micro_consolidation calls agent and returns a contour
agent exceptions become structured errors
invalid response shapes become structured errors
first slice does not write review events to the ledger
review-state derivation marks reviewed and deferred mnions
latest receipt wins for the same mnion
unread-active selector skips reviewed/deferred mnions and bounds packets
request preparation uses review receipts to skip reviewed mnions
```

Next tests should cover:

```text
needs_rereview caused by reinforcement after review
high-valence / high-reinforcement priority bump
agent-facing request does not include receipt bodies, tables, or SQL rows
serialized packet character/token budget
```

Smoke receipt from a temporary ledger:

```json
{
  "ok": true,
  "valence": 0.71,
  "member_count": 2,
  "fail_ok": false,
  "fail_reason": "agent_call_failed",
  "ledger_lines_after": 11
}
```
