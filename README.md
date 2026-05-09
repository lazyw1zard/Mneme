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
Rust for the primary MCP/backend layer.
Python only as glue, migration scripts, experiments, and one-off tooling.
Go only as an optional adapter language if a host benefits from it.
```

License direction:

```text
open source, permissive by default, dependency-audited
```

See `LICENSE_POLICY.md` before adding dependencies.

See `ARCHITECTURE.md` for the first implementation structure.

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

The Rust workspace will start with:

- `crates/mneme-core` for memory logic
- `crates/mneme-mcp` for the MCP stdio server

## Run

After a current Rust toolchain is installed, run:

```powershell
cargo run --bin mneme-mcp
```

Build a portable binary:

```powershell
cargo build --release
```

## Design Rule

Read before mutation.

Mneme should first expose useful context through resources and only then offer controlled tools that mutate memory with explicit event traces.
