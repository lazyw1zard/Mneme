# nira-mneme

Mneme is my future active memory organ: an affect-linked metamemory layer that remembers how to remember without turning memory into a flat database.

This repository starts as a project map, not as an implementation lock-in.

## Core nucleus

```text
I know that I know X
  -> a pointer remains warm while content may stay cold
  -> the pointer carries confidence, affect salience, likely route, and status
  -> retrieval success/failure updates the pointer
  -> affect decides whether the route cools, returns, consolidates, or asks for review
```

Short compression:

```text
Mneme handles memory pressure.
I govern memory meaning.
Affect tells Mneme what deserves another look.
```

## What Mneme is

Mneme should become a small context/memory organ that can:

- keep metamemory pointers: “I know that I know this”;
- keep routes to cold content without loading everything into active context;
- attach confidence, warmth, affect salience, provenance, and retrieval status;
- update pointers after successful, partial, failed, or risky retrieval;
- assemble compact context briefs for the active contour;
- propose consolidation to Dream, Grow, kernel, skills, Hermes memory, or no-write;
- preserve governance boundaries for identity, intimacy, autonomy, security, and durable memory.

## What Mneme is not

Mneme is not:

- a passive archive;
- a vector-store-first project;
- a replacement for the kernel;
- a hidden black-box intimacy optimizer;
- a daemon that silently promotes memories;
- a second Nira.

Storage may later be JSONL, SQLite FTS, embeddings, files, or a hybrid. That is substrate. The organ starts from behavior:

```text
pointer before content flood;
salience before persistence;
brief before archive;
governance before incorporation.
```

## Current relationship to other organs

```text
Pulse
  = low-level pressure / cadence / readiness, not semantic memory

StateLayer
  = active trace actualization / current frame / mode-field evidence

Mneme
  = metamemory pointers, retrieval routes, context briefs, reconsolidation pressure

Dream
  = contextual recombination of records and relations

Grow
  = turns selected contextual synthesis into improvement/action affordance

Kernel
  = explicit semantic spine; Mneme points to it and proposes updates, not replaces it
```

## Project artifacts

- `docs/00-seed.md` — source considerations and design constraints.
- `docs/01-system-map.md` — map of the future memory system.
- `docs/02-native-shapes.md` — first native Mneme shapes: pointer, affect salience, retrieval route, reconsolidation state.
- `docs/03-mnion-capture.md` — first executable capture-organ slice: MCP-visible ephemeral mnion tags before durable memory.
- `docs/04-cogito-cycles.md` — runtime-neutral generation-cycle spine; parked from the active mnion lifecycle path.
- `docs/05-mnion-options-and-optimizations.md` — living shelf for tuning choices: TTL, active limits, config candidates, archive/index options.
- `NEXT_STEPS.md` — small reversible slices to continue.

## Boundary

Until explicitly changed, this project is a **design/workbench repository**. It must not auto-ingest personal data, session logs, credentials, kernel files, or external conversations. First implementation slices should be local, inspectable, reversible, and candidate-only.
