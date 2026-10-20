# Mneme — current direction and next steps

This is the current project entry, not a promise to implement every possible
extension. The earlier slice-by-slice roadmap is preserved byte-for-byte in
[the historical roadmap](docs/history/initial-next-steps.md). Read that file as
history, not as the current completion list or a list of available commands.

## Memory path

```text
memory_tag -> agentic micro-consolidation -> mnion -> authored relations
           -> recognizable entrance -> deliberate return
           -> separate decision about further incorporation
```

This is a capability path, not mandatory promotion: a capture may be noise,
deferred, or remain a useful standalone mnion. Neither retrieval nor graph
connectivity automatically creates an engram.

## Implemented mechanisms

- Ephemeral capture, call-age/wall-clock lifecycle, pre-capture comparison,
  review pressure, unread-active selection, and explicit review closure.
- Multi-mnion packet outcomes: grouped, reviewed noise, deferred, and unresolved.
- Reconstructable read-model, exact item retrieval and compact topic routes.
- Minimal direct `MemoryPointer` construction/resolution; this is not a full
  pointer ledger or retrieval-attempt lifecycle.
- Optional authored claims and separate later claim annotations that preserve
  original bodies, rationale, valence, receipts and exact addresses.
- Authored `continues / corrects / follows_from` connections and bounded
  `get_neighborhood`; no persistent arc/episode storage tier.
- Hermes-native topic/claim ingress with at most one transient connected
  entrance. Exact routes in a cue take priority; otherwise the latest eligible
  authored connection provides a reminder. This is not semantic relevance,
  unresolved-thread detection or rotation. Full bodies remain behind `get_item`.

## What the evidence establishes

- [Controlled claim recall](docs/experiments/claim-recall-controlled/RESULTS.md)
  tested navigation with and without claims on a fixed small corpus.
- [Authored connection practice](docs/experiments/authored-connections/RESULTS.md)
  verified persistence, exact return, original preservation and safe retry.
- The [connected ingress contract](docs/plans/connected-ingress.md) describes
  the deployed bounded entry shape and its explicit limits.

A successful relation return is not a controlled relations-efficacy result,
a general causal-memory proof, or completed long-term consolidation. Mocked-host
adapter tests are not native validation of every supported host.

## Remaining planned work

### 1. Evaluate the added value of authored relations

A narrowed [one-arc connected-entry pilot](docs/experiments/connected-entry-pilot/RESULTS.md)
compared the same claims/routes/tools with and without an initial edge preview:
6 recorded trials, 5 complete, 1 output-limit censored; in two completed matched
pairs no navigation advantage was observed. This checks initial-entry affordance,
not graph availability or general relation efficacy. Do not treat this descriptive
pilot as a reason to expand or remove the existing working graph/ingress.

Extend the controlled recall work to questions requiring multiple memories and
relationship grounds, not just dates. Hold bodies, route coverage, budgets and
questions constant when comparing claims-only with claims-plus-relations.
Isolate conversation, kernel and repository leakage. Score navigation, actual
body retrieval, relationship reconstruction and unsupported additions separately.

Source: [October plan, Slice 4, Step 4](docs/plans/2026-10-08-claims-and-relations-next-slices.md).

### 2. Try one deliberate connected-form consolidation

Open one bounded arc and author what began, changed, why and remains. Preserve
source routes, disagreement and uncertainty. A new synthesis must not rewrite or
impersonate original mnions. Explicitly accept, defer or decline one engram
candidate before building a queue or expanding the mechanism.

Source: [October plan, Slice 4, Step 5](docs/plans/2026-10-08-claims-and-relations-next-slices.md).

### 3. Confirm a connected-form metapointer

Draft an authored entrance from opened originals and relations; bind it to exact
item/connection evidence and a bounded retrieval action. Probe the route before
claiming durable, repeatable addressability. A candidate hint may exist earlier.
Only then choose the smallest persistence/ingress change justified by the result.
The current two-node/one-edge preview is not automatically that metapointer.

This direction exists in the [September graph sketch, Tasks 6–7](docs/plans/2026-09-27-mnion-event-graph-metamemory-pointers.md)
and [pointer maturity decision](DECISIONS.md). A new class/table per maturity name
is not required. This work may share an experiment with the prior steps; its
precise implementation scope remains a separate decision.

### 4. Reduce graph-placement overhead if practice requires it

Offer a few candidate neighbor routes/claims during consolidation and allow zero
or more deliberate relations in the same act. Separate `connect_items` already
works; the integrated review shape is not implemented merely because it exists.
Do not infer edges or require a mandatory second graph-placement ceremony.

## Possible slice under question — intact long-form intake

**Status: unresolved; no architecture selected and no implementation authorized.**

The current short `memory_tag.delta` intake (280 characters) cannot carry a
long intact text. An unconstrained `Mnion.summary` does not remove this intake
bottleneck, and semantic summarization does not guarantee exact preservation.
Standalone understanding must remain possible without an invented event context.

The open question is how to retain whole material and make it reachable within
Mneme's existing memory process without breaking the verified capture/review/return
loop or adding an attention-heavy parallel archive. Internal call sequence alone
provides temporal placement, not integration with provenance, relations or return.

Constraints for reconsideration:

- Preserve organic, attention-light operation; consolidation must not become a
  separate self-reflective administration ritual for every retained item.
- Do not require attachments to be inherited as cargo through every structure.
- Do not duplicate general pointer behavior with a narrow source-reference lane.
- Keep exact original preservation distinct from derived understanding; preserve
  existing mnions, receipts and routes unchanged.
- Consider larger tags, singleton review, a distinct intake object, or attachments
  only as alternatives, not agreed solutions. Possible graphics support does not
  by itself justify an attachment architecture.

This is a possible future slice, not the selected next task. Do not implement an
artifact store, broaden capture, or change schemas on the basis of this note.

## Possible later work — not the immediate bundle

- Pointer/return-attempt history; useful and unsuccessful return feedback.
- Compact source-grounded context briefs.
- Situation-sensitive arc selection, strengthening/cooling of routes.
- Engram-candidate pressure and queue after one meaningful candidate decision.
- Thin StateLayer/Pulse projections without semantic ownership moving to Pulse.
- A separately scoped forgetting policy for mature memory. Existing raw-tag TTL
  does not implement forgetting of mnions, graph relations or metapointers.
- Moving stable latency/integrity-sensitive core pieces to Rust, not adapter glue.

## Retired approaches — do not resume from old sketches

- Standalone `Mnion.events` / consolidation `events[]` prototype.
- Required dictionary/surface-overlap ingress gate and legacy body-preload APIs.
- Withdrawn Hermes origin-attestation observer: not a product dependency. Its
  canceled source is preserved outside the active product workspace; the simple
  local observer is a separate host-specific aid and must not be removed with it.

Historical mentions are evidence of decisions, not active implementation tasks.
Do not remove live capture matching/lifecycle events or useful direct-pointer
prototypes just because their names resemble a retired approach.

## Reading order and engineering boundaries

1. This file: current capability path and open work.
2. [DECISIONS](DECISIONS.md): principles, historical decisions and open proposals.
3. Accepted [connection](docs/plans/authored-connections.md) and
   [ingress](docs/plans/connected-ingress.md) contracts.
4. [Presence anchor and MCP placement](docs/07-presence-anchor-and-mcp.md).
5. [Retired-approach cleanup](docs/maintenance/retired-approaches.md): what was removed and what stays.
6. Historical plans for provenance, not automatic API requirements.

Keep core independent of MCP/host adapters. Agents receive bounded routes and
semantic packets, not SQL, raw ledgers or full corpora. Review meaning remains
agent-authored; original artifacts are immutable; public fixtures remain neutral.
For each authorized code slice use isolated tests, relevant real transport/host
smoke, independent review and verified preservation before claiming completion.
