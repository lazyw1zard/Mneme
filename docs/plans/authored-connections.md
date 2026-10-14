# Authored connections: minimal closure contract

## Agentic need

I can already choose an intelligible route and open its original memory. I now need to return to an explicitly authored relationship without reconstructing predecessor/causal topology from date order or topical resemblance. This slice records the relation, not a new episode/cluster/arc memory tier.

## Only one new semantic object

`MnionConnection`: `source_review_id`, `target_review_id`, `relation_kind`, `relation_summary`; an immutable ID, recording timestamp and `created_by=agent` provide receipt provenance. Source **continues / corrects / follows_from target**. Two distinct, literal, materializable item routes are required. Intentional cross-receipt connections are allowed; packet audit IDs, hints, repaired IDs and self-links are not.

`relation_summary` is authored, nonblank, at most 1200 Unicode characters, preserving its literal wording and uncertainty. The tool cannot certify that the author actually inspected both bodies or that an event caused another; the affordance explicitly requires that prior inspection. Original bodies, rationale, valence, claims, source receipts, capture ledger and call sequence are unchanged.

## Core and portable tools

- `connect_items(...)`: append a receipt to separate `mnion_connections.jsonl`, project adjacency, reread the exact indexed connection and durable source. Identical sequential authorship reuses evidence; a projection failure returns its recorded ID for a same-authorship `retry_connection_id`. An I/O failure can follow partial append and requires inspection, not blind re-append.
- `get_neighborhood(exact_item_route, depth=1, limit=4)`: explicit mechanical bidirectional view, depth 1..2, **total** connection budget 1..8. Nodes carry only exact routes and valid authored claims; original bodies remain behind selected `get_item`. No persisted arc object, narrative synthesis, new pointer tier or engram queue.

Order is deterministic receipt order, not valence ranking or occurrence chronology. Read-back follows both incoming and outgoing relations but preserves their original directed meaning. Visited nodes/edges prevent traversal loops. `has_more` means a witnessed unreturned edge at the depth/breadth boundary, not a guessed complete-graph count.

## Audit/index boundaries

Receipts remain source evidence; the existing SQLite file gains a reconstructable adjacency table and two directional indexes. Item and adjacency projections retain separate freshness markers. Explicit neighborhood reads may repair stale projections; native prefetch, ordinary topic lists and normal `get_item` do not traverse or preload relations. Fresh reads use a short-timeout read-only connection. Each directional neighbor query is ordered and limited before combining results; a displayed limit alone would not bound high-degree backend work.

Schema, adjacency rows and its freshness marker commit together. Known invalid original/annotation/connection evidence fails before a new append. Pending review blocks connection authorship without clearing its latch. Ledger separation protects actual configured sources, counters, config, overlays, pending state, database, SQLite auxiliary paths and destination symlink/hardlink aliases. The claim writer also protects the new connection source.

The same serialization/concurrency boundary as the existing receipt authoring remains: this slice does not claim multi-process writer locking, authenticated semantic authorship, automatic supersession or deletion. Different explicit explanations may coexist as different immutable connections; interpretation/revision remains deliberate.

## Verification and practice

Parent-authored RED tests preceded implementation. Disposable environments isolate all HOME/Hermes/XDG/Mneme/config/tmp paths, propagate them to MCP subprocesses and hash live Mneme artifacts before/after testing. Hostile checks cover literal identity, empty/nonmaterializable items, separate paths and aliases, safe retries, corruption, post-projection evidence loss, cycle/depth/overflow behavior and high-degree backend work. Real MCP stdio must return a three-item/two-edge view and leave originals and counters unchanged.

After separate independent read-only spec and quality/security gates, use one bounded real relationship whose grounds were actually inspected. Save original comparisons, connection identity and practical reconstruction privately. The test is whether the relation meaning returns with its source routes and uncertainty, not whether a full graph or engram exists. Keep public code/tests neutral; real memory bodies and model traces stay private.
