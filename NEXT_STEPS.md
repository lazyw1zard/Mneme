# Mneme Next Steps

This rail keeps Mneme from becoming a vague memory swamp or a database-first implementation.

## Current status

Created as a design/workbench project.

Done:

- preserve semantic nucleus;
- map relation to Pulse / StateLayer / Dream / Grow / kernel;
- sketch native shapes for pointer, affect salience, retrieval route, reconsolidation state, context brief, receipt;
- implement Slice 0: `mnion` capture as cheap ephemeral JSONL tag plus one MCP-visible capture tool;
- implement Slice 1: MCP-visible `memory_tag.capture` increments a tiny portable `mneme_seq.json` counter and records `birth_call_seq`/`call_ttl` for call-age decay;
- add `docs/05-mnion-options-and-optimizations.md` as the living shelf for tuning, config candidates, and future storage/read optimizations;
- implement Slice 2: cheap pre-capture filter inside `memory_tag.capture`, returning `created`, `reinforced`, or `linked_new` without adding a second MCP tool;
- implement Slice 3: minimal host-neutral `mnion.micro_consolidation` module that prepares the latest 10 active mnions for an agent review and returns one candidate contour or a structured error.

Not done:

- no daemon;
- no database;
- no vector store;
- no auto-ingestion;
- no kernel mutation;
- no automatic memory capture;
- no automatic durable write from micro-consolidation;
- no host-runtime routing contract that makes Mnion reliably considered during live memory decisions.

## Slice 4 — host-neutral memory-routing contract

Goal: fix the first live failure without turning Mneme into a local Hermes hack or keyword-trigger script. `memory_tag.capture` existed, but the active contour did not consider it because no memory-orientation layer made the affordance salient.

Behavior:

```text
agent host turn/event
  -> Mneme routing membrane
  -> no_write | candidate/mnion | recall_brief | review_due | commit_request
```

This is not keyword auto-capture. Words like `память`, `важно`, and `сохранить` can be weak evidence, but they must never be the trigger. The routing membrane should weigh meaning, durability, utility, valence, sensitivity, volatility, and consequence.

Portable ports:

```text
TurnIngressPort   -> optional brief/routing hint before the model answers
SaliencePort      -> score memory pressure from events/actions/corrections
CapturePort       -> write ephemeral candidate/mnion with provenance
RecallPort        -> return compact brief + pointers + confidence + guards
ReviewPort        -> prepare consolidation proposal
CommitPort        -> apply approved durable write with audit/deletion route
```

Adapter examples:

```text
Hermes       plugin hooks + MCP tools + memory tool adapter
LangGraph    middleware/nodes/checkpointer adapter
CLI agent    pre/post turn wrapper + XDG state dir
Assistants   run lifecycle + tool resources adapter
```

Verification:

- fresh host session can receive a Mneme brief/routing hint without local hardcoded paths;
- memory-shaped turns can select Mnion/candidate when appropriate without keyword matching;
- durable memory/kernel writes still require governance;
- no raw transcript capture, no hidden listener, no silent auto-promotion.

## Slice 0 — mnion capture organ prototype

Goal: prove that I can capture a live movement as a cheap, ephemeral tag before building Mneme.

Behavior:

```text
memory_tag.capture(delta, valence, ttl_seconds, call_ttl=32, hooks, trigger, affect_hints)
  -> pre-capture compare against newest active tags
  -> created | reinforced | linked_new
  -> append one mnion record or a small lifecycle event
  -> no embedding, pointer, deep memory, kernel write, or engram
```

Default storage follows `MNEME_STATE_DIR` first, then XDG:

```text
$MNEME_STATE_DIR/mnions.jsonl
$MNEME_STATE_DIR/mneme_seq.json

# fallback when MNEME_STATE_DIR is unset:
$XDG_STATE_HOME/mneme/mnions.jsonl
$XDG_STATE_HOME/mneme/mneme_seq.json
```

The counter advances only when the Mneme/mnion organ is called. It does not count every Hermes turn, model generation, Telegram delivery, tool execution, or Codex run.

Verification:

- capture writes one bounded tag;
- active reads are bounded by default (`DEFAULT_ACTIVE_MNION_LIMIT = 20`);
- expired tags are hidden unless explicitly requested with audit flags;
- MCP surface exposes exactly one capture affordance;
- no Hermes runtime config is changed automatically.


## Slice 1 — mnion lifecycle over Mneme call counts

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

## Slice 2 — pre-capture filter

Goal: prevent obvious duplicate mnions before they enter the active set.

Behavior:

```text
memory_tag.capture
  -> compare candidate against newest active tags
  -> created | reinforced | linked_new
```

Verification:

- repeated same-pattern contours append reinforcement events instead of duplicate records;
- related but distinct contours append link audit hints;
- reinforcement refreshes call-life for active loading;
- no embeddings, model calls, vector store, or durable promotion.

## Slice 3 — micro-consolidation review packet

Goal: prove that a small batch of active mnions can be handed to a host-provided live contour/agent without making Mneme depend on Hermes.

Behavior:

```text
prepare_micro_consolidation_request(limit=10)
  -> latest active mnions
  -> portable prompt + expected schema

run_micro_consolidation(agent=callable)
  -> try agent(request)
  -> ConsolidatedContour(summary, valence, member_ids, rationale)
  -> structured error if the agent call fails or returns invalid data
```

Verification:

- latest 10 active mnions are selected chronologically inside the selected window;
- successful agent callback returns one candidate contour;
- failing agent callback returns `agent_call_failed`;
- invalid agent output returns `invalid_agent_response`;
- this first slice does not write review events to the ledger.

## Slice 5 — local pointer ledger prototype

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

## Slice 6 — retrieval attempt updates route

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

## Slice 7 — context brief instead of archive flood

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

## Slice 8 — affect salience routing

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

## Slice 9 — contour receipt bridge

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

1. Should the first implementation be Rust CLI, or a tiny Python prototype for shape exploration?
2. Which source handles are safe for MVP: project docs only, kernel docs read-only, current traces, session search?
3. Where should access attempts live: project-local audit log or shared state dir?
4. How does Mneme coordinate with Dream queue without making Dream a retrieval query?
5. What is the minimal test that proves “I know that I know” without loaded content?
