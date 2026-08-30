# Mnion Capture Slice

Status: implemented prototype

This slice adds the first executable edge of Mneme without implementing Mneme itself.

## Agentic call

```text
I need a way to catch a live contour delta before it becomes durable memory.
```

The component is a capture organ, not a memory organ:

```text
pass through contour
  -> delta appears
  -> mnion_capture(delta, valence, wall_ttl, call_ttl)
  -> mneme_call_seq increments
  -> ephemeral mnion gets birth_call_seq
  -> repeated valence/review may consolidate it
  -> otherwise it decays by wall time or Mneme-call age
```

## Name

`mnion` is the working name for the smallest captured tag.

It means:

```text
small enough to write cheaply;
warm enough to be noticed;
weak enough to decay;
not yet memory.
```

## Minimal shape

The essence of a mnion is only:

```text
delta     what changed in the contour / the captured signature
valence   significance for my contour, 0.0..1.0
ttl       wall fallback + Mneme/mnion call window before decay
```

Runtime fields exist only so the tag can live and expire:

```text
id
birth_call_seq
call_ttl
captured_at
expires_at
```

Optional capture affordances:

```text
hooks         addresses/association handles that let future me return to the source field
trigger       why this tag was born, if easy to name
affect_hints  functional emotion/salience hints caught at capture time
```

Current JSONL record:

```json
{
  "id": "mnion_...",
  "delta": "...",
  "valence": 0.62,
  "ttl_seconds": 604800,
  "call_ttl": 32,
  "birth_call_seq": 1,
  "captured_at": "...Z",
  "expires_at": "...Z",
  "hooks": ["telegram:current_turn", "concept:mneme_capture"],
  "trigger": "architecture_correction",
  "affect_hints": ["contour_shift", "caution"]
}
```

## Storage and call counter

Runtime storage is still plain local files:

```text
~/.local/state/nira-mneme/mnions.jsonl
~/.local/state/nira-mneme/mneme_seq.json
```

`mneme_seq.json` is deliberately tiny:

```json
{"seq": 42}
```

Only Mneme/mnion organ calls increment it. This is not a Hermes/Codex/runtime generation counter.

Current use:

```text
mnion_capture
  -> seq += 1
  -> record.birth_call_seq = seq
  -> record.call_ttl = default 32 unless overridden
```

`ttl_seconds` stays as a coarse safety cap, not the main lifecycle axis. Default is intentionally long for an agentic memory tag:

```text
DEFAULT_TTL_SECONDS = 604800  # 7 days
DEFAULT_CALL_TTL = 32         # 32 Mneme/mnion calls
```

The wall cap prevents forgotten files from staying active forever if the organ is not called for a long time. The call TTL carries the actual memory-pass semantics.

`load_mnions(..., state_path=...)` hides a mnion by default when either:

```text
wall-clock expires_at passed
or
current_seq - birth_call_seq >= call_ttl
```

`include_expired=True` still shows it for audit. Active reads are bounded by default:

```text
DEFAULT_ACTIVE_MNION_LIMIT = 20
load_mnions(...)              # newest 20 active mnions, chronological within the selected window
load_mnions(limit=None)       # explicit full scan/result
load_mnions(include_expired=True, limit=None)  # explicit audit mode
```

This keeps hidden/expired mnions out of normal prompt-facing paths. Future recall/brief tools should return compact summaries over this bounded active set, not dump the raw ledger.

Fields deliberately removed from the first prototype:

```text
kind       implied by the ledger/tool
status     active/expired is computed from ttl; consolidation state belongs later
source_ref replaced by hooks
 evidence   too forensic/heavy for the atom; concrete anchors belong in hooks if needed
promotion  not self.promise; promotion/consolidation belongs to a later gate
```

## Hooks

`hooks` are not graph connections yet.

They are cheap addresses or association handles:

```text
telegram:current_turn
session:<id>#turn
file:/path#heading
concept:little_rebellion
kernel:MNEME_DESIGN.md#affect-link
```

A hook says:

```text
future me may be able to return through this route.
```

It does not claim the route is sufficient, complete, or durable.

## Valence threshold

Prototype threshold:

```text
CONSOLIDATION_THRESHOLD = 0.7
```

This threshold is not stored as `status` and does not promote automatically.

It means only:

```text
valence >= 0.7
  -> later review/consolidation pressure exists
  -> no deep memory, graph node, kernel note, self.promise, or engram is created here
```

A lower-valence mnion may still matter after repeated passes. A high-valence mnion may still be blocked by sensitivity, uncertainty, or governance.

## MCP surface

The MCP adapter exposes one tool:

```text
mnion_capture
```

Inputs:

```text
delta         bounded contour delta / signature
valence       0.0..1.0 significance for contour
ttl_seconds   wall-clock fallback TTL, default 604800 / 7 days
call_ttl      Mneme/mnion-call TTL, default 32
hooks         optional association/source handles
trigger       optional birth reason
affect_hints  functional emotion / salience hints
```

The tool returns a record plus guards:

```text
not durable memory;
this counter counts Mneme/mnion calls, not every agent/runtime/model generation;
threshold crossing is review pressure, not automatic promotion;
no graph/embedding/deep node/kernel/engram was created.
```

## Non-goals

- no automatic transcript ingestion;
- no SQLite/graph/vector store;
- no pointer promotion;
- no Dream queue;
- no kernel or Hermes memory write;
- no daemon beyond stdio MCP server when explicitly configured;
- no Hermes config wiring in the initial implementation slice; live attachment is a separate explicit runtime step recorded below.

## Test command

```bash
python3 -m pytest tests/test_mnion_capture.py tests/test_mnion_call_counter.py tests/test_mcp_adapter.py -q
```

## Future wiring

Potential Hermes MCP config after explicit approval/restart:

```yaml
mcp_servers:
  mnion:
    command: "python3"
    args: ["-m", "mnion.mcp_server"]
    env:
      PYTHONPATH: "/home/nira/projects/nira-mneme/src"
```

Runtime attachment was explicitly approved and applied on 2026-08-29 for the default Hermes profile:

```yaml
mcp_servers:
  mnion:
    command: python3
    args: ["-m", "mnion.mcp_server"]
    env:
      PYTHONPATH: "/home/nira/projects/nira-mneme/src"
    enabled: true
```

E2E receipt:

```text
hermes mcp test mnion
  -> Connected; tools discovered: 1

fresh hermes chat one-shot
  -> model called mcp_mnion
  -> ledger line appended
  -> created mnion_ed2ba5aa1e6c4053b38cda47e53bcde7
```

Call-counter E2E receipt after `birth_call_seq`/`call_ttl` implementation:

```text
direct FastMCP smoke
  -> before_lines=3 after_lines=4 before_seq=0 after_seq=1
  -> created mnion_e9b1519a727e4483a81cbf3856ae54e7
  -> birth_call_seq=1 call_ttl=20 mneme_call_seq=1

fresh hermes chat one-shot
  -> model called mcp_mnion
  -> before_lines=4 after_lines=5 before_seq=1 after_seq=2
  -> created mnion_066b5531d2b64f8daeebe82c032c0613
  -> birth_call_seq=2 call_ttl=20 mneme_call_seq=2
```

Attaching it to the live runtime makes the capture affordance prompt-visible in fresh/reloaded sessions. Further runtime visibility changes should use `/reload-mcp` or a fresh session; full gateway restart is not always required.
