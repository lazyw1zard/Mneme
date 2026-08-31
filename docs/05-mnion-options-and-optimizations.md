# Mnion Options and Optimizations

Status: living project note

This file is the shelf for practical tuning ideas while mnion is still a small working primitive. It should collect options, tradeoffs, and future optimizations without forcing Mneme into a premature schema.

## Current implemented defaults

```text
DEFAULT_TTL_SECONDS = 604800  # 7 days, wall-clock fallback
DEFAULT_CALL_TTL = 32         # Mneme/mnion-call lifetime
DEFAULT_ACTIVE_MNION_LIMIT = 20
```

Meaning:

```text
wall TTL  = safety cap if the organ is not called for a long time
call TTL  = main lifecycle axis: how many memory-organ passes a tag survives
active limit = prompt-facing/read path budget guard
```

## Current storage

```text
~/.local/state/nira-mneme/mnions.jsonl
~/.local/state/nira-mneme/mneme_seq.json
```

`mneme_seq.json` remains deliberately tiny:

```json
{"seq": 2}
```

It counts only Mneme/mnion calls, not every model generation, Hermes turn, Telegram delivery, Codex run, or tool execution.

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
normal read -> newest 20 active mnions
explicit audit -> full/expired ledger
```

Future tuning options:

- keep fixed `20` until real usage shows pressure;
- split by valence buckets: high-valence active tags get priority;
- cap by estimated serialized chars, not count;
- produce a compact active brief instead of raw records.

## Future config file

Do not add config until values need tuning in practice. When needed, prefer a small local config such as:

```text
~/.config/nira-mneme/config.toml
```

Candidate shape:

```toml
[mnion]
default_ttl_seconds = 604800
default_call_ttl = 32
active_limit = 20
consolidation_threshold = 0.7

[storage]
state_dir = "~/.local/state/nira-mneme"
```

Rules for config:

- code constants remain safe defaults;
- missing config should not break the organ;
- invalid config should fail loudly in CLI/tests, not silently distort memory;
- MCP adapter may use config, but core should still accept explicit parameters for tests and portability;
- config is operational tuning, not ontology.

## Optimization shelf

### A. Avoid reading huge JSONL forever

Current `load_mnions` still scans the JSONL file, then returns a bounded active window. This prevents prompt flooding but not IO growth.

Future options:

1. `active_mnions.jsonl` sidecar updated by sweep;
2. archived expired records moved to `mnions.archive.jsonl`;
3. small SQLite index only after JSONL becomes too slow;
4. compact active brief cache generated from active records.

Decision rule:

```text
only optimize storage when measured IO or token pressure appears
```

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
load_mnions()
  -> active only
  -> bounded limit
```

Audit path:

```text
load_mnions(include_expired=True, limit=None)
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

- no full Mneme database;
- no raw transcript ingestion;
- no automatic kernel/engram writes;
- no Hermes/Codex dependency for lifecycle;
- no prompt dump of full mnion ledger;
- no promotion from `memory_tag.capture` alone.

## Working maxim

```text
cheap to notice;
bounded to read;
expensive to keep.
```
