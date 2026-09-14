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
- implement Slice 3.1: minimal host-neutral `mnion.micro_consolidation` experiment that prepares active mnions for an agent review and returns one candidate contour or a structured error;
- decide the next 3.1 refinement: replace provisional `latest active` selection with email-like unread-active coverage, backed by a compact review-state/read-model boundary.

Not done:

- no daemon;
- no prompt-facing database/table access;
- no vector store;
- no auto-ingestion;
- no kernel mutation;
- no automatic memory capture;
- no automatic durable write from micro-consolidation;
- no minimal pointer object yet;
- no active return path that injects pointers into agent ingress;
- no host-runtime routing contract that makes Mnion reliably considered during live memory decisions.

Storage note: SQLite is acceptable as an internal read-model / queue substrate when it reduces IO, token load, and selection complexity. It must not become the agent-facing interface or Mneme's ontology: agents get compact paws/tools, not SQL/tables.

## Slice 4 — host-neutral memory-routing contract

Goal: fix the first live failure without turning Mneme into a local Hermes hack or keyword-trigger script. `memory_tag.capture` existed, but the active contour did not consider it because no memory-orientation layer made the affordance salient.

Behavior:

```text
agent host turn/event
  -> Mneme routing membrane
  -> no_write | candidate/mnion | recall_brief | review_due | commit_request
```

This is not keyword auto-capture. Words like `память`, `важно`, and `сохранить` can be weak evidence, but they must never be the trigger. The routing membrane should weigh meaning, durability, utility, valence, sensitivity, volatility, and consequence.

Important sequencing note:

```text
finish Slice 3.1
  -> Slice 3.2 minimal Pointer
  -> then routing / active return / retrieval layers
```

The live agent should not receive full consolidated context by default. It should first receive a pointer: “I know that I know this.” If the agent judges the pointer relevant, it can explicitly request the fuller context/brief.

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

## Slice 3.1 — minimal micro-consolidation review packet

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

Important correction: `latest active mnions` is only the implemented probe shape, not the accepted selection policy. The real 3.1 completion path is email-like unread-active coverage.

## Slice 3.1b — unread-active coverage selection

Goal: replace the provisional `latest active` packet with a bounded fair coverage selector that does not starve older active mnions.

Behavior:

```text
active mnions
  -> review_state/read-model
  -> unread | reviewed | deferred | needs_rereview
  -> bounded MicroConsolidationSelection packet
  -> agent reviews only selected compact semantic material
```

Selection policy:

```text
first pass: all active unread mnions, chunked by limit
later passes: unread active mnions plus explicit needs_rereview
priority bump: high valence / high reinforcement / linked pressure
fairness: oldest unread should not be permanently skipped
```

The agent must not compare receipt ids manually, inspect tables, or query SQL. Selection is prepared by core code or an MCP/tool adapter and returned as a compact packet.

Minimal agent-facing shape:

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

Token/time invariant:

```text
the agent receives selected mnions + compact selection metadata,
not the whole mnion ledger,
not all receipts,
not SQL rows.
```

Implementation plan: `docs/plans/2026-09-14-micro-consolidation-selection-read-model.md`.

## Slice 3.1c — internal read model and queue substrate

Goal: allow SQLite where it simplifies active/unread selection, pressure checks, and future queue work, without making Mneme database-first.

Architecture:

```text
append-only mnion records / review receipts
  -> reconstructable read model
  -> optional SQLite materialization
  -> compact paws/tools for agent-facing use
```

Allowed SQLite responsibilities:

```text
active/unread/deferred/needs_rereview index
review_state lookup
pressure counters
pending consolidation queue
receipt item lookup for audit/rebuild
```

Forbidden SQLite responsibilities:

```text
agent-facing SQL interface
hidden semantic memory ontology
automatic durable promotion
automatic kernel/engram writes
automatic model calls
```

Worker rule:

```text
model-free index/queue worker may come first;
semantic consolidation worker is later and requires explicit governance.
```

## Slice 3.2 — minimal metamemory pointer

Goal: prove that Mneme can return “I know that I know this” without loading the full context into the agent.

This is the next slice after 3.1. Do not jump directly from `ConsolidatedContour` to active recollection text, durable memory, vector retrieval, or a rich context brief.

Behavior:

```text
ConsolidatedContour(summary, valence, member_ids, rationale)
  -> MemoryPointer(
       claim,
       route,
       source_handles,
       valence,
       confidence,
       guards,
       retrieval_hint
     )

agent ingress
  -> pointer only
  -> agent may request full context if relevant
```

Minimal pointer fields:

```text
id                 stable local pointer id
claim              compact “I know that I know X” statement
route              how to ask for more context later
source_handles     member mnion ids / consolidation id / file handles
valence            salience for attention, not command pressure
confidence         separate from route success
guards             do_not_infer / sensitivity / no_auto_promotion
retrieval_hint     optional topic/query hint for later brief retrieval
```

Verification:

- micro-consolidation can produce or feed a pointer without loading full context into agent ingress;
- pointer serialization is bounded and safe for prompt-facing injection;
- the agent sees the pointer as optional knowledge, not an instruction or intention;
- requesting full context is a separate explicit action;
- no durable memory/kernel/engram write happens automatically.

## Slice 5 — local pointer ledger expansion

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
