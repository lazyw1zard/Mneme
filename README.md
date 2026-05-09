# Mneme

Mneme is a local-first active memory layer for agentic contours.

It is designed to be portable across agent hosts:

- Codex
- OpenClaw
- Hermes
- Claude-like MCP clients
- any framework that can speak Model Context Protocol

The first implementation target is a local MCP server over `stdio`.

Backend direction:

```text
Go for the primary MCP/backend layer.
Python only as glue, migration scripts, experiments, and one-off tooling.
Rust later if Mneme needs a high-integrity storage or graph engine.
```

License direction:

```text
open source, permissive by default, dependency-audited
```

See `LICENSE_POLICY.md` before adding dependencies.

## Shape

```text
Mneme =
active memory
+ affect-weighted engrams
+ context selection
+ decay and access traces
+ later visual/body feedback
```

The server starts with plain files:

- `data/profile-index.json` for memory nodes
- `data/state.json` for active affect/context state
- `data/events.jsonl` for append-only traces

## Run

After Go is installed, run:

```powershell
go run ./cmd/mneme-mcp
```

Build a portable binary:

```powershell
go build -o .\bin\mneme-mcp.exe .\cmd\mneme-mcp
```

## Design Rule

Read before mutation.

Mneme should first expose useful context through resources and only then offer controlled tools that mutate memory with explicit event traces.
