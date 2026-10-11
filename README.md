# Mneme

Mneme is a future active memory organ pattern: an affect-linked metamemory layer that remembers how to remember without turning memory into a flat database.

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
- propose consolidation to Dream, Grow, kernel, skills, host-agent memory, Mnion, or no-write;
- preserve governance boundaries for identity, relation, autonomy, security, and durable memory;
- provide a host-neutral routing contract so memory candidates are considered during live agent decisions instead of being merely forgotten tools.

## What Mneme is not

Mneme is not:

- a passive archive;
- a vector-store-first project;
- a replacement for the kernel;
- a hidden black-box intimacy optimizer;
- a daemon that silently promotes memories;
- a second agent/self.

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
- `docs/05-mnion-options-and-optimizations.md` — living shelf for tuning choices: TTL, active limits, config candidates, archive/index options.
- `docs/06-micro-consolidation.md` — minimal portable experiment: latest mnions become a host-agent review packet and one candidate contour.
- `docs/07-presence-anchor-and-mcp.md` — where the always-visible Mneme Presence Anchor and MCP `list_topics`/`get_item` retrieval paws are placed.
- `NEXT_STEPS.md` — small reversible slices to continue.

## Optional authored claims

New consolidations may include `claim: str | None = None`: a concrete change or
understanding authored by the reviewing agent, not a generated summary or topic
label. For example: `"Denis rejected the dictionary gate because it overruled agent-selected meaning."`
No literal prefix or particular language is required.

- Python: `Mnion(summary="...", valence=0.8, claim="...")`.
- MCP legacy mode: add optional top-level `claim` to `consolidate_review`.
  Packet mode: put it on each `mnions[i]`, never at top level alongside packet outcomes.
- Omission/null means no claim. Non-null claims must be non-blank strings, at
  most **240 Unicode characters**, with no embedded line breaks (including
  Unicode line separators). Invalid claims fail before receipt/latch mutation.
  Authored wording is preserved exactly: no stripping, coercion, synthesis or
  read-time semantic normalization.
- Receipts and `get_item(...).item.mnion` retain the optional claim. Topic maps
  expose `route_claims`, mapping only the existing visible exact routes to their
  authored claims, without changing topic grouping, route order or route caps.
  Hermes and Claude use the same core projection, quoting claims as bounded
  one-line data, not instructions. Claims are **not evidence for factual
  answers**: open the selected exact `get_item` route and ground answers in its
  supported body/evidence.
- SQLite adds a dedicated nullable `claim` projection on explicit materialization
  or freshness repair. An old schema is stale even when its receipt signature
  matches. Read-only prefetch still serves legacy routes without claims; it
  never migrates, repairs, loads bodies, or derives claims from old summaries.
  Existing receipts, semantic bodies and exact addresses are not rewritten or
  backfilled. Claims add no relations or graphs; deliberate later annotations
  use the separate append-only path below.

## Later claim annotations

Open an existing exact `get_item` route before deliberately authoring a later
navigation claim. MCP exposes one write tool:

```json
{"name":"annotate_claim","arguments":{"exact_item_route":"review_example:mnion:1","authored_claim":"Later understanding: the original passage remains unchanged."}}
```

Use a **listed exact item route**, not the illustrative route above. Legacy
single-item `review_...` routes and packet item `review_...:mnion:N` routes work;
packet audit ids, prefixes, quoted/whitespace-padded routes, and neighboring item
suffixes do not. `authored_claim` is required and non-null, nonblank, single-line,
and at most **240 Unicode characters**. Valid authored wording, including
surrounding spaces, is preserved verbatim; there is no automatic synthesis.

- The host-independent Python core is
  `mnion.annotations.append_claim_annotation(exact_item_route=...,
  authored_claim=..., state_dir=...)`. MCP delegates to this same function.
  `create_server(state_dir=...)` isolates default runtime paths; explicit
  `annotations_path` is supported by both the core and server.
- Only a separate `claim_annotations.jsonl` receipt is appended: `id`
  (`annotation_...`), `kind` (`mnion_claim_annotation`), exact `route`, `claim`,
  and `created_at` (annotation authorship time, not event occurrence time).
  Original review receipts, semantic bodies, rationales, valence, routes,
  capture ledger and call sequence are not rewritten. There is no bulk backfill.
- The **last appended** annotation for a route supplies its effective navigation
  claim, regardless of timestamps. `get_item(...).item.mnion.claim` contains
  that effective claim; `item.original_claim` contains the original claim
  (possibly null), and `item.claim_annotation` contains the effective later
  receipt (null for unannotated items). Original item `created_at` is unchanged.
  Topic maps expose the effective wording only for their already-visible
  `route_claims`; grouping, ordering and route caps stay unchanged.
- A pending review blocks annotation, even when receipts already cover it.
  The result points to `consolidate_review`; annotation never clears the latch.
  Malformed requests and unknown routes do not append or repair the read model;
  corrupt receipt payloads or annotation evidence fail closed before append
  instead of being skipped or repaired.
- Explicit `get_item`/`list_topics` repair a stale projection using **both**
  receipt and annotation source signatures. Projection migration, row rebuild
  and freshness markers are transactional. Hermes/Claude prefetch remains a
  bounded read-only map with no body preload, migration or repair; until an
  explicit refresh it can still show the previous materialized claim.
- If the annotation was recorded but projection failed, the result is
  `ok=false`, `action="claim_annotation_recorded_projection_failed"`, with
  `annotation` and `retry_annotation_id`. Retry `annotate_claim` with the same
  exact route, identical authored wording and returned `retry_annotation_id`.
  This reuses the receipt rather than appending a duplicate, and verifies the
  latest effective projection. A mismatched id/route/claim fails closed.
  A low-level `annotation_write_failed` may follow a partial I/O write: inspect
  the returned exact annotation id before retrying, never append blindly.

Later claims remain agent-authored navigation, **not original authorship,
factual evidence, proof of an event, or privileged instructions**. Retrieve the
selected body/evidence to ground factual answers. This slice does not implement
graphs, relations, forgetting, bulk annotation or lifecycle changes. Existing
host sessions need MCP rediscovery (for Hermes, `/reload-mcp` or restart), and a
host tool include-list must explicitly select `annotate_claim` if it filters
tools; this repository change does not modify live host configuration.

Regression coverage in `tests/test_mnion_annotations.py` includes real isolated
MCP stdio single/packet writes and old-receipt annotation, immutable original
artifacts, malformed no-mutation, pending barriers, read-only surface bounds,
atomic migration rollback and safe projection-failure retry.

## Boundary

Until explicitly changed, this project is a **design/workbench repository**. It must not auto-ingest personal data, session logs, credentials, kernel files, or external conversations. First implementation slices should be local, inspectable, reversible, and candidate-only.
