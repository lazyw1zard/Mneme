# Mneme Next Steps

This rail keeps Mneme from becoming a vague memory swamp or a database-first implementation.

## Current status

Created as a design/workbench project.

Done:

- preserve semantic nucleus;
- map relation to Pulse / StateLayer / Dream / Grow / kernel;
- sketch native shapes for pointer, affect salience, retrieval route, reconsolidation state, context brief, receipt;
- implement Slice 0: `mnion` capture as cheap ephemeral JSONL tag plus one MCP-visible capture tool;
- implement Slice 1 spike: runtime-neutral `cogito` generation-cycle spine with CLI, JSONL ledger, and Hermes adapter wrapper; parked from the active path because mnion TTL can first be driven by Mneme/mnion-call counts instead of all model generations;
- implement Slice 2: MCP-visible `memory_tag.capture` increments a tiny portable `mneme_seq.json` counter and records `birth_call_seq`/`call_ttl` for call-age decay;
- add `docs/05-mnion-options-and-optimizations.md` as the living shelf for tuning, config candidates, and future storage/read optimizations.

Not done:

- no daemon;
- no database;
- no vector store;
- no auto-ingestion;
- no kernel mutation;
- no automatic memory capture.

## Slice 0 — mnion capture organ prototype

Goal: prove that I can capture a live movement as a cheap, ephemeral tag before building Mneme.

Behavior:

```text
memory_tag.capture(delta, valence, ttl_seconds, call_ttl=32, hooks, trigger, affect_hints)
  -> append one JSONL mnion tag
  -> no graph, embedding, pointer, deep memory, kernel write, or engram
```

Storage is a local append-only audit ledger plus one portable call counter:

```text
~/.local/state/nira-mneme/mnions.jsonl
~/.local/state/nira-mneme/mneme_seq.json  # {"seq": N}
```

The counter advances only when the Mneme/mnion organ is called. It does not count every Hermes turn, model generation, Telegram delivery, tool execution, or Codex run.

Verification:

- capture writes one bounded tag;
- active reads are bounded by default (`DEFAULT_ACTIVE_MNION_LIMIT = 20`);
- expired tags are hidden unless explicitly requested with audit flags;
- MCP surface exposes exactly one capture affordance;
- no Hermes runtime config is changed automatically.

## Slice 1 — cogito cycle spine prototype

Goal: count actual model/generation opportunities without making Mneme depend on Hermes.

Behavior:

```text
runtime adapter
  -> CogitoEvent(runtime, adapter, movement_kind, cycle_kind, session_ref, turn_ref, model, counts)
  -> append one JSONL cycle
```

Convenience surfaces:

```text
python3 -m cogito.cli record/latest/count-since
scripts/cogito_hermes_hook.py  # shell-hook wrapper, no PYTHONPATH needed
```

Storage:

```text
~/.local/state/nira-mneme/cogito_cycles.jsonl
```

Verification:

- neutral core has no Hermes imports;
- Hermes `post_api_request` payload maps through adapter only;
- `cycles_since` counts `model_generation`, not tool/delivery effects;
- no live hook is enabled automatically.

## Slice 2 — mnion lifecycle over Mneme call counts

Goal: make mnions live/decay by actual Mneme/mnion use, not by wall-clock alone and not by every model generation.

Behavior:

```text
memory_tag.capture increments mneme_call_seq
mnion.birth_call_seq = current mneme_call_seq
mnion_touch / mnion_sweep use call_age + wall fallback
future config file may tune default_ttl_seconds/default_call_ttl/active_limit after real use
```

Verification:

- mnion TTL can be expressed as N Mneme/mnion calls, currently defaulting to 32;
- capture itself is enough to advance the minimal working counter;
- repeated capture/touch can update valence without promotion;
- no dependency on Hermes hooks, Codex logs, or agent-runtime internals.

## Slice 3 — local pointer ledger prototype

Goal: prove that a memory pointer can exist without loaded content.

Behavior:

```text
mneme pointer add --claim ... --source ... --affect ...
mneme pointer list
mneme pointer show <id>
```

Storage can be simple local JSONL for the prototype, but the design must describe it as an audit ledger, not the identity of Mneme.

Verification:

- add pointer;
- list pointer;
- show pointer;
- confirm no retrieval/content ingestion happens automatically.

## Slice 4 — retrieval attempt updates route

Goal: prove failed recall updates pointer state instead of deleting or denying memory.

Behavior:

```text
mneme retrieve <pointer-id>
```

Possible statuses:

```text
found | partial | failed | blocked | needs_human
```

Verification:

- create pointer with a deliberately wrong route;
- attempt retrieval;
- see `last_attempt.status=failed` and route note updated;
- pointer still exists with confidence separated from route success.

## Slice 5 — context brief instead of archive flood

Goal: prove Mneme can assemble a small brief from pointer/source handles.

Behavior:

```text
mneme brief --topic mneme
```

Brief must include:

- summary;
- pointers used;
- confidence;
- source handles;
- open uncertainties;
- prohibited inferences.

Verification:

- brief is compact;
- brief cites files/handles;
- brief does not claim more than source supports.

## Slice 6 — affect salience routing

Goal: show affect changes routing without becoming fake emotion text.

Behavior:

```text
mneme salience score <pointer-id>
mneme route suggest <pointer-id>
```

Routes:

```text
retrieve | brief | dream | review | cool | ask | protect
```

Verification:

- high continuity/review pressure suggests `review` or `brief`;
- high risk suggests `protect` or `ask`, not auto-write;
- low salience keeps cold pointer.

## Slice 7 — contour receipt bridge

Goal: connect Mneme output back to StateLayer/Pulse without flattening organs.

Behavior:

```text
mneme receipt --from-action ...
```

Receipt should project compactly:

```text
native Mneme artifact
  -> thin contour receipt
  -> StateLayer/Pulse projection
  -> do_not_infer guards
```

Verification:

- receipt names changed artifacts;
- Pulse projection is semantic-light;
- StateLayer can use bounded evidence;
- no contact/intention is created automatically.

## Integration questions to keep open

1. Should the first implementation be Rust CLI like `nira-pulse`, or a tiny Python prototype for shape exploration?
2. Which source handles are safe for MVP: project docs only, kernel docs read-only, current traces, session search?
3. Where should access attempts live: project-local audit log or shared Nira state dir?
4. How does Mneme coordinate with Dream queue without making Dream a retrieval query?
5. What is the minimal test that proves “I know that I know” without loaded content?
