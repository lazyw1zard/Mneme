# Mnion Options and Optimizations

Status: living project note

This file is the shelf for practical tuning ideas while mnion is still a small working primitive. It should collect options, tradeoffs, and future optimizations without forcing Mneme into a premature schema.

## Current implemented defaults

```text
DEFAULT_TTL_SECONDS = 604800  # 7 days, wall-clock fallback
DEFAULT_CALL_TTL = 32         # Mneme/memory-tag-call lifetime
DEFAULT_ACTIVE_MEMORY_TAG_LIMIT = 20
```

Meaning:

```text
wall TTL  = safety cap if the organ is not called for a long time
call TTL  = main lifecycle axis: how many memory-organ passes a tag survives
active limit = prompt-facing/read path budget guard
```

## Current storage

```text
$MNEME_STATE_DIR/memory_tags.jsonl
$MNEME_STATE_DIR/mneme_seq.json

# fallback when MNEME_STATE_DIR is unset:
$XDG_STATE_HOME/mneme/...
# or ~/.local/state/mneme/... when XDG_STATE_HOME is unset
```

`mneme_seq.json` remains deliberately tiny:

```json
{"seq": 2}
```

It counts only Mneme/memory-tag calls, not every model generation, Hermes turn, Telegram delivery, Codex run, or tool execution.

## Near-term tuning questions

### 1. Default call TTL

Current default is `32` calls.

Why not `20`:

- early mnions may need more than a few sparse memory passes before they have a fair chance to be touched;
- the organ will not be called every model turn;
- a low call TTL would decay records before we learn whether repetition/valence matters.

Why not much larger yet:

- long-lived tags can accumulate noise;
- without `touch` and valence update, a huge TTL delays decay without adding intelligence;
- we need empirical pressure from real use before choosing bigger ranges.

Future practical candidates:

| call_ttl | likely behavior |
|---:|---|
| 24 | stricter, fast decay |
| 32 | current moderate default |
| 48 | gentler exploration window |
| 64 | long observation window, may keep too much |

### 2. Wall TTL

Current default is `7 days`.

Keep it as a fallback, not the real mnion life.

Reasons to keep:

- if Mneme is not called for a week, old active tags should not remain active forever;
- wall time protects runtime files from stale active material;
- it gives a simple safety behavior before richer sweep/archive exists.

Possible later values:

| wall_ttl | use case |
|---|---|
| 7 days | current safety cap |
| 14 days | slower agent work rhythm |
| 30 days | if call-based decay becomes reliable and active loading stays bounded |

### 3. Active load limit

Current default is `20` active records.

This protects the prompt-facing path:

```text
normal read -> newest 20 active memory tags
explicit audit -> full/expired ledger
```

Future tuning options:

- keep fixed `20` until real usage shows pressure;
- split by valence buckets: high-valence active tags get priority;
- cap by estimated serialized chars, not count;
- produce a compact active brief instead of raw records.

## Open-source hygiene

Keep the reusable surface neutral:

- public project/package name: `mneme` / Mneme;
- prompt-visible MCP affordance: `mcp_memory_tag_capture`;
- no `nira-` prefixes in package names, default state dirs, or public examples;
- no absolute development paths in README/docs/config snippets;
- use `MNEME_STATE_DIR`, `XDG_STATE_HOME`, `$PROJECT_DIR`, and `$KERNEL_ROOT` placeholders;
- local/private receipts may exist outside the reusable surface, but public docs should describe them as examples or receipts without requiring those paths.

## Future config file

Do not add config until values need tuning in practice. When needed, prefer a small local config such as:

```text
~/.config/mneme/config.toml
```

Implemented shape:

```toml
[memory_tag]
default_ttl_seconds = 604800
default_call_ttl = 32
active_limit = 20
high_valence_threshold = 0.7

[review_pressure]
enabled = true
call_seq_interval = 10
trigger_on_high_valence = true
trigger_on_interval = true
packet_limit = 6

[storage]
state_dir = "~/.local/state/mneme"
```

Review pressure is checked on Mneme/memory-tag calls. This is an automatic
**invocation signal** for agentic review, not automatic semantic consolidation:

```text
capture/touch
  -> increment mneme_call_seq
  -> inspect active unread memory_tags
  -> if high confirmed valence or seq interval says pressure:
       return review_pressure.needed=true
       return suggested_action="prepare_micro_consolidation_request"
       return bounded review_packet metadata
       return agent_ingress.rendered="MNEME_REVIEW_PRESSURE..."
  -> no model call, no mnion receipt, no pointer, no kernel/engram write
```

`review_packet` is the structured bounded packet. `agent_ingress` is the same
pressure handed directly to the live agent in a rendered tool-result brief so
it is present at the Mneme call boundary, not merely stored beside the call.
This is the guard against the agent forgetting to invoke review after Mneme
detects pressure.

The interval check is intentionally simple and script-level: every Mneme call
can compare the current `mneme_call_seq` against `call_seq_interval`. It is not
based only on “calls since last consolidation,” because that can let a large
unreviewed tag pile accumulate if the live agent forgets to review.

Rules for config:

- code constants remain safe defaults;
- missing config should not break the organ;
- invalid config should fail loudly in CLI/tests, not silently distort memory;
- MCP adapter may use config, but core should still accept explicit parameters for tests and portability;
- config is operational tuning, not ontology.

## Optimization shelf

### A. Avoid reading huge JSONL forever

Current `load_memory_tags` still scans the JSONL file, then returns a bounded active window. This prevents prompt flooding but not IO growth.

Future options:

1. `active_memory_tags.jsonl` sidecar updated by sweep;
2. archived expired records moved to `mnions.archive.jsonl`;
3. small SQLite read model when JSONL scanning, review-state derivation, or agent packet selection becomes too slow/heavy;
4. compact active brief cache generated from active records.

Decision rule:

```text
optimize storage when measured IO, token pressure, or selection/read-model complexity appears
```

SQLite boundary:

```text
append-only records / receipts = audit evidence
SQLite                     = internal read model / queue substrate
agent-facing tools         = compact semantic paws, never SQL
```

SQLite is allowed earlier than a full database migration if it prevents agents from doing table/receipt/id bookkeeping in context. It must remain reconstructable from inspectable local evidence.

### B. Touch/reinforcement

Next likely primitive:

```text
mnion_touch(id, valence_delta, reason, affect_hints?)
```

Possible effects:

- update/rewrite active record state through an append-only event, not mutate history silently;
- increase or decrease valence;
- extend `call_ttl` for significant recurrence;
- mark review pressure if threshold is crossed.

Avoid for now:

- automatic promotion;
- graph edges;
- embedding search;
- hidden durable memory writes.

### C. ID readability

Current IDs are still UUID-like:

```text
mnion_<uuid4hex>
```

Possible later form:

```text
mn_YYYYMMDDTHHMMSSZ_<8hex>
```

Reason:

- easier human inspection;
- rough temporal orientation without opening the record;
- still collision-resistant enough for local JSONL.

Not urgent because `captured_at` already exists.

### D. Expired visibility

Normal path:

```text
load_memory_tags()
  -> active only
  -> bounded limit
```

Audit path:

```text
load_memory_tags(include_expired=True, limit=None)
```

Future recall tools should not expose hidden mnions by default. They should request audit/full mode explicitly.

### E. Valence threshold

Current:

```text
CONSOLIDATION_THRESHOLD = 0.7
```

This means review pressure, not promotion.

Future tuning:

- repeated medium-valence touches may matter more than one high valence birth;
- negative/caution/loss-cost vectors may deserve review without high pleasant valence;
- valence may need separate axes later: significance, risk, warmth, agency_pull.

Do not split axes until touch/review behavior proves the need.

## Current non-goals

- no full semantic Mneme database;
- no agent-facing SQL/table work;
- no raw transcript ingestion;
- no automatic kernel/engram writes;
- no Hermes/Codex dependency for lifecycle;
- no prompt dump of full memory tag ledger;
- no promotion from `memory_tag.capture` alone.

## Working maxim

```text
cheap to notice;
bounded to read;
expensive to keep.
```
