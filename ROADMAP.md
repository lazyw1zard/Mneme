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

### M6: Local API

Expose local state through a small service.

Possible stack:

```text
Python + FastAPI
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

Expose Mneme to agent sessions.

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
