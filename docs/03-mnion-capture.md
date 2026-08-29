# Mnion Capture Slice

Status: implemented prototype

This slice adds the first executable edge of Mneme without implementing Mneme itself.

## Agentic call

```text
I need a way to catch a live memory movement before it becomes durable memory.
```

The component is a capture organ, not a memory organ:

```text
stimulus / correction / self-promise / affect signal
  -> mnion_capture
  -> cheap ephemeral mnion tag
  -> decay unless later valence/review captures it
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

## Storage

Default ledger:

```text
~/.local/state/nira-mneme/mnions.jsonl
```

This is append-only JSONL. It is the audit trail for capture, not Mneme's future storage identity.

## MCP surface

The MCP adapter exposes one tool:

```text
mnion_capture
```

Inputs:

```text
stub          bounded one-sentence trace
source_ref    where the tag came from
trigger       why capture is considered
affect_hints functional emotion / salience hints
evidence      short observable evidence, not invented feeling
ttl_seconds   default 3600
```

The tool returns a record plus `do_not_infer` guards:

```text
not durable memory;
no graph/embedding/deep node/kernel/engram was created;
promotion requires later valence/review governance.
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
