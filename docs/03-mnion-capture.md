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
  -> mnion_capture(delta, valence, ttl)
  -> ephemeral mnion
  -> repeated valence/review may consolidate it
  -> otherwise it decays
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
ttl       time window before decay
```

Runtime fields exist only so the tag can live and expire:

```text
id
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
  "ttl_seconds": 3600,
  "captured_at": "...Z",
  "expires_at": "...Z",
  "hooks": ["telegram:current_turn", "concept:mneme_capture"],
  "trigger": "architecture_correction",
  "affect_hints": ["contour_shift", "caution"]
}
```

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
ttl_seconds   default 3600
hooks         optional association/source handles
trigger       optional birth reason
affect_hints  functional emotion / salience hints
```

The tool returns a record plus guards:

```text
not durable memory;
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
- no Hermes config wiring in this slice.

## Test command

```bash
python3 -m pytest tests/test_mnion_capture.py tests/test_mcp_adapter.py -q
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

Do not apply this automatically. MCP visibility is a feature, but attaching it to the live runtime is a separate governance step.
