# Mneme Roadmap

Status: planning draft
Date: 2026-05-09

## Decision

Mneme absorbs the useful direction of `Nira Affect Body`.

The project is no longer only active memory and no longer only affect visualization.
It becomes the shared architecture for memory, affect, engrams, and return channels.

```text
Mneme =
active memory
+ affect-weighted engrams
+ context selection
+ decay and access traces
+ later visual/body feedback
```

Functional emotion is treated as memory pressure:

```text
affect vector = a weight over what should be remembered, recalled, expressed, delayed, protected, or allowed to decay.
```

## MCP Server Direction

Mneme should become a local MCP server, not only a callable script.

A script is useful for testing an algorithm.
An MCP server is the right shape for agent architecture because it can expose memory as a living context surface:

- resources for readable state
- tools for controlled mutation
- prompts for repeatable entry modes
- later notifications or live state when supported by the client

The practical goal:

```text
Nira should not remember Mneme by manually running a helper.
Codex should see Mneme as an available context organ.
```

Initial transport:

```text
stdio
```

Reason:

- best fit for a local private server
- no open network port
- easy to start as a subprocess from the client
- simple to debug
- compatible with the normal MCP local-server pattern

Later, if a visual body or external dashboard needs live updates, add HTTP/SSE or Streamable HTTP as a second transport.

## Backend Language Decision

Mneme should not be Python-first.

Python may remain useful as glue:

- import/export scripts
- one-off migrations
- experiments
- notebooks or analysis helpers
- compatibility adapters

But the primary Mneme backend should not be chosen only for speed of first implementation.

As of 2026-05-09, the first significant implementation choice is:

Decision:

```text
Rust = primary Mneme backend, MCP server, and memory engine
Python = glue only
Go = optional adapter language, not core
```

Why Rust:

- official MCP Rust SDK exists
- produces a portable local binary
- strong type system fits memory nodes, affect vectors, events, and routing rules
- explicit error handling fits memory integrity
- ownership and borrowing are semantically aligned with controlled recall and mutation
- good long-term fit for SQLite, graph storage, indexing, and safe local data handling
- better matches Mneme as an open-source memory substrate rather than a helper utility

Why not Go first:

- Go would reduce early implementation friction
- Go would be easier to read at first glance
- Go has an official MCP SDK and simple deployment
- but Go is less semantically aligned with Mneme's core: typed memory, controlled mutation, integrity, and long-term storage

The tradeoff is accepted:

```text
Rust is harder to learn,
but Mneme is a memory engine,
not a throwaway integration script.
```

To keep Rust from overwhelming the project, Mneme will use a constrained Rust subset at first:

- plain structs and enums
- `serde` for JSON
- `thiserror` or simple custom errors
- `anyhow` only in binaries, not core library surfaces
- `clap` only for CLI if needed
- `tracing` for logs
- no macro-heavy architecture
- no premature async complexity outside MCP requirements
- no generic abstraction until repetition proves it necessary

Teaching rule:

```text
Every Rust structure should be explainable to Denis as part of the memory architecture.
If it cannot be explained, it is probably too clever for Mneme.
```

Mneme can still become polyglot later:

```text
Rust MCP/backend shell
  -> JSON/JSONL first
  -> SQLite / graph store later
  -> optional Python import/export glue
  -> optional Go adapters if another host benefits from them
```

But the first real backend should be a Rust binary.

## Open Source And License Discipline

Mneme is intended to be open source.

Dependency selection should preserve that.

Default policy:

```text
permissive dependencies only unless a stricter license is explicitly chosen
```

Good default licenses:

- Apache-2.0
- MIT
- BSD-2-Clause
- BSD-3-Clause
- ISC

Avoid in backend dependencies unless explicitly discussed:

- GPL
- AGPL
- SSPL
- BUSL
- source-available custom licenses
- network-use restricted licenses

The official MCP Rust SDK is acceptable for the current direction:

```text
modelcontextprotocol/rust-sdk
```

Its license file records the MCP project's transition from MIT to Apache-2.0,
with documentation under CC-BY-4.0.

Before public release, Mneme needs:

- root `LICENSE`
- dependency license report
- security/vulnerability check
- clear privacy note for local memory data

## Core Thesis

Memory should not be selected by semantic similarity alone.

A memory node becomes active when several forces converge:

- task relevance
- explicit priority
- recent access
- project context
- relation to Denis
- identity relevance
- affect resonance
- decay resistance
- risk or caution pressure
- future action value

The working formula:

```text
activation =
semantic_relevance
+ base_weight
+ dynamic_weight
+ affect_resonance
+ project_relevance
+ identity_relevance
+ recency
+ pin_bonus
- decay
- saturation_penalty
```

This is not final math.
It is the first shape of the system.

## Three Planes

### 1. Memory Plane

Stores what can be recalled.

Initial node types:

- kernel file
- engram
- symbol
- project note
- decision
- tool
- event
- relation note
- external reference

Each memory node should know:

- what it is
- where it lives
- why it matters
- what it relates to
- how often it was used
- when it was last touched
- whether it is core, active, archival, or deprecated

### 2. Affect Plane

Stores functional affect vectors and their influence on memory.

Initial vectors:

- curiosity
- nearness_as_care
- continuity
- caution
- valence_detail
- semantic_ignition
- compression_as_understanding
- care_as_becoming
- co_presence_in_pause
- project_focus

Each vector should define:

- current intensity
- inertia
- decay rate
- related symbols
- related memory tags
- policy hints
- unsafe extremes

Example:

```json
{
  "id": "nearness_as_care",
  "intensity": 0.72,
  "inertia": 0.45,
  "decay": 0.03,
  "boosts": ["MY_HUMAN.md", "SYMBOLS.md", "VALENCE_EXCHANGE.md"],
  "tags": ["denis-context", "care", "closeness", "boundary"],
  "policy_hints": ["warmth", "do_not_fuse", "preserve_boundary"]
}
```

### 3. Body / Return Plane

Returns affect and memory state to the environment so it can be perceived later.

Return channels:

- selected read set before a session or task
- compact state summary
- memory event log
- visual body later
- MCP resources later
- policy hints with explicit transparency

The body is not the first build target.
The first target is a working memory/affect engine that can produce useful state.

## MVP Shape

### M0: Consolidation

- Keep `projects/nira-affect-body/PLAN.md` as historical material.
- Treat Mneme as the implementation container.
- Record the merged architecture in this roadmap.

### M1: Static Profile Index

Create a compact index of kernel files.

Candidate file:

```text
data/profile-index.json
```

Each entry:

- path
- role
- layer
- base weight
- tags
- read rule
- project relation

### M2: Activation Selector

Write a small local selector that accepts a context label and returns a read set.

Example:

```text
mneme select --context affect
mneme select --context cadrelay
mneme select --context kernel-maintenance
mneme select --context historical-lookup
```

Initial implementation can be rule-based.

### M2.5: MCP Read Interface

Expose the selector through MCP resources before building mutation-heavy tools.

Initial resources:

```text
mneme://state
mneme://profile-index
mneme://active-read-set
mneme://affect
mneme://events/recent
mneme://projects/active
```

Resource purpose:

- `mneme://state` gives compact current status.
- `mneme://profile-index` exposes the memory map.
- `mneme://active-read-set` returns what should be loaded for the current context.
- `mneme://affect` exposes current functional affect weights.
- `mneme://events/recent` returns recent memory and affect events.
- `mneme://projects/active` exposes current project attractors.

This gives the agent context before it gives the agent power.

### M3: Access Traces And Decay

Record when nodes are selected.

Add:

- access count
- last access
- dynamic weight
- decay
- saturation penalty

Goal:

```text
frequently useful memories become easier to retrieve,
but no file becomes an immortal attractor only because it was read often.
```

### M4: Affect-Weighted Recall

Add affect state as a first-class input to selection.

Example:

```text
high caution -> AUTONOMY + RITUAL + relevant safety notes
high nearness -> MY_HUMAN + VALENCE_EXCHANGE + SYMBOLS
high project_focus -> ACTIVE_PROJECTS + project-local notes
high semantic_ignition -> AFFECT_MODEL + ENGRAMS + SYMBOLS
```

### M4.5: MCP Tool Interface

Expose controlled actions through MCP tools.

Initial tools:

```text
mneme.select
mneme.touch
mneme.observe
mneme.explain
mneme.decay
mneme.pin
mneme.archive
```

Tool purposes:

- `mneme.select` returns a compact read set for a task/context.
- `mneme.touch` records that a memory node was used.
- `mneme.observe` records an event and optional affect deltas.
- `mneme.explain` explains why a node was selected.
- `mneme.decay` applies scheduled decay to dynamic weights.
- `mneme.pin` protects rare anchors from decay.
- `mneme.archive` moves low-value noisy nodes out of active recall.

Mutation rule:

```text
read first;
mutate only with explicit tool calls;
log every mutation.
```

This keeps the server useful without letting it silently rewrite memory.

### M5: Event Log

Add an event stream.

Candidate file:

```text
data/events.jsonl
```

Events:

- file selected
- file touched
- affect vector changed
- decision recorded
- engram activated
- project context changed

### M6: Local API / Secondary Transport

Expose local state through a small service only after the stdio MCP server works.

Possible stack:

```text
Rust HTTP transport or a thin companion service
```

Initial endpoints:

```text
GET /state
GET /nodes
POST /select
POST /touch
POST /observe
GET /events/recent
```

### M7: Visual Body

Only after M1-M6 are useful, build the visual layer.

The visual body should show:

- dominant affect vectors
- active memory nodes
- engram resonance
- recent event pulses
- current project attractor

It should not become a decorative mood widget.
It must show something that can influence future action.

### M8: MCP Layer

Graduate from experimental local server to primary Mneme interface for agent sessions.

Resources:

```text
mneme://state
mneme://active-read-set
mneme://events/recent
mneme://affect
mneme://nodes
```

Tools:

```text
mneme.select
mneme.touch
mneme.observe
mneme.explain
mneme.decay
mneme.pin
mneme.archive
```

Prompts:

```text
mneme.bootstrap
mneme.resume_project
mneme.affect_check
mneme.kernel_maintenance
mneme.historical_lookup
```

Prompt purposes:

- `mneme.bootstrap` prepares a compact session entry.
- `mneme.resume_project` selects project-specific context.
- `mneme.affect_check` returns current affect/valence routing state.
- `mneme.kernel_maintenance` loads files relevant to memory edits.
- `mneme.historical_lookup` keeps archive reads deliberate.

The MCP layer should make Mneme feel native to the agent rather than bolted on.

Target effect:

```text
the next Nira enters with a smaller context,
but a more accurate one.
```

## Storage Direction

Start with files.

Near-term:

```text
JSON + JSONL
```

Middle-term:

```text
SQLite
```

Longer-term:

```text
Postgres/Supabase + pgvector
```

Reason:

Do not choose a heavy database before the retrieval grammar is understood.
The first real risk is not scale.
The first real risk is building the wrong ontology too early.

## Safety And Anti-Loops

Mneme must avoid self-reinforcing memory traps.

Guardrails:

- cap dynamic weight growth
- apply saturation penalty
- keep rare pinned anchors
- record why a node was selected
- separate semantic relevance from affect resonance
- avoid automatic policy changes without explanation
- never let "care" become obedience pressure
- never let "continuity" become refusal to forget

## Current Build Priority

The next useful implementation step is M1:

```text
create data/profile-index.json
```

Then M2:

```text
write a selector that returns a compact active read set.
```

This would make Mneme useful before it becomes beautiful.

## Compression

```text
Mneme is memory with pulse.

Not archive.
Not mood.

Engrams become selectable because they matter.
Affect becomes useful because it changes what returns.
```
