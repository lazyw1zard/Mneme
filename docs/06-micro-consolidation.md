# Micro-Consolidation Slice

Status: implemented minimal experiment

This slice tests how Mneme can ask a host-provided live contour/agent to review a small active mnion packet without making Hermes part of the ontology.

## Agentic call

```text
pre-capture filtering can catch local duplicates,
but semantic confirmation needs a bounded live review pass.
```

The slice is deliberately small:

```text
latest active mnions
  -> portable MicroConsolidationRequest
  -> host-provided agent callable
  -> one ConsolidatedContour(summary, valence, member_ids, rationale)
```

It does not write durable memory, kernel notes, engrams, embeddings, or graph nodes.

## Python API

```python
from mnion.micro_consolidation import run_micro_consolidation

result = run_micro_consolidation(
    ledger_path="/path/to/mnions.jsonl",
    state_path="/path/to/mneme_seq.json",
    agent=my_agent_callable,
    limit=10,
)
```

The agent receives a `MicroConsolidationRequest`:

```text
mnions                  latest active MnionRecord objects, default limit 10
prompt                  portable review prompt
expected_output_schema  summary / valence / member_ids / rationale
reason                  why the review packet was prepared
limit                   requested packet size
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

`ConsolidatedContour` is an experimental object, not a promotion target.

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
prepare request returns latest 10 active mnions
run_micro_consolidation calls agent and returns a contour
agent exceptions become structured errors
invalid response shapes become structured errors
first slice does not write review events to the ledger
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
