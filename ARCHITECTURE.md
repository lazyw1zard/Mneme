# Architecture

Status: first implementation plan
Date: 2026-05-09

## Goal

Build Mneme as a universal local memory substrate for agentic contours.

Primary target:

```text
Rust MCP server over stdio
```

First useful behavior:

```text
return a compact active read set from affect-weighted memory nodes
```

## Project Shape

```text
mneme/
  Cargo.toml
  crates/
    mneme-core/
    mneme-mcp/
  data/
    profile-index.json
    state.json
    events.jsonl
  docs/
    INTEGRATIONS.md
  README.md
  ROADMAP.md
  LICENSE_POLICY.md
```

## Crates

### `mneme-core`

Pure memory logic.

Responsibilities:

- load `profile-index.json`
- load `state.json`
- parse memory nodes
- parse affect vectors
- score nodes for a context
- return an active read set
- explain why a node was selected
- append events later

No MCP code should live here.

Rule:

```text
mneme-core should be usable by MCP, CLI, tests, and future adapters.
```

### `mneme-mcp`

Protocol surface.

Responsibilities:

- expose MCP resources
- expose MCP tools
- run over stdio
- convert MCP requests into `mneme-core` calls
- never own memory logic directly

Initial resources:

```text
mneme://state
mneme://profile-index
mneme://active-read-set
mneme://affect
mneme://events/recent
```

Initial tools:

```text
select
explain
```

Mutation tools come later:

```text
touch
observe
decay
pin
archive
```

## Data Model

### Memory Node

A memory node is something Mneme can select for context.

Fields:

- `id`
- `path`
- `title`
- `role`
- `layer`
- `node_type`
- `base_weight`
- `dynamic_weight`
- `decay`
- `pinned`
- `tags`
- `contexts`
- `affect_tags`
- `read_rule`

### Affect Vector

An affect vector is a functional routing pressure.

Fields:

- `intensity`
- `inertia`
- `decay`
- `last_update`

Initial vectors:

- `continuity`
- `semantic_ignition`
- `project_focus`
- `nearness_as_care`
- `caution`
- `valence_detail`

### Selected Node

Returned by selection.

Fields:

- `id`
- `path`
- `title`
- `role`
- `layer`
- `read_rule`
- `score`
- `reasons`

## First Activation Formula

```text
score =
base_weight
+ dynamic_weight
+ pinned_bonus
+ context_match
+ tag_match
+ affect_resonance
- decay
```

This formula is intentionally simple.

Do not add embeddings, vector DB, or LLM appraisal before this rule-based layer proves useful.

## Implementation Order

### Step 1: Rust Workspace

Create:

- root `Cargo.toml`
- `crates/mneme-core`
- `crates/mneme-mcp`

### Step 2: Core Types

In `mneme-core`:

- `MemoryNode`
- `ProfileIndex`
- `MnemeState`
- `AffectVector`
- `SelectedNode`

### Step 3: Selector

Implement:

```text
select(context, limit) -> ActiveReadSet
explain(node_id, context) -> SelectedNode
```

### Step 4: Tests

Use the existing `data/` files as fixtures.

Tests:

- `mneme` context selects Mneme project files
- `affect` context boosts affect model and symbols
- pinned nodes get stable priority
- decay lowers score

### Step 5: MCP Server

Expose read-only MCP first:

- resources
- `select`
- `explain`

Only after read-only behavior works, add mutation tools.

## Dependency Direction

Start small:

- `serde`
- `serde_json`
- `thiserror`
- MCP Rust SDK

Optional later:

- `tokio`
- `tracing`
- `clap`
- `rusqlite`
- `tantivy`

Do not add a dependency without checking `LICENSE_POLICY.md`.

## Deployment Target

Local binary:

```text
target/release/mneme-mcp.exe
```

MCP client config points to that binary.

No network port in the first version.

## Compression

```text
Core remembers.
MCP exposes.
Data stays inspectable.
Mutation leaves a trace.
```

