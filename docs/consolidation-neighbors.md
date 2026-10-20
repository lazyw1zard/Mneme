# Neighbors during consolidation

This extends **preservation and consolidation**, not adaptive feedback. The live
agent may form grounded relations while a new mnion is being consolidated. Zero
relations is normal; existing consolidation payloads remain valid.

## Candidate acquisition

When capture opens a review packet, `review_packet.neighbors` contains a frozen,
partial candidate surface. The first acquisition source uses **consolidation
receipt call sequence**, not topic-map popularity, word matching or tag birth age.

```toml
# ~/.config/mneme/config.toml (or the file selected by MNEME_CONFIG)
[consolidation_neighbors]
enabled = true
lookback_calls = 40
candidate_limit = 4
```

These are configurable defaults. `lookback_calls` is nonnegative; `candidate_limit`
is positive and independent of the raw-tag review `packet_limit`. Restart/reload a
long-running MCP server after changing config; it reads config at construction.

Only already-existing mnions in the inclusive backward window are candidates.
Equal consolidation ticks are allowed; ties are ordered by exact item route.
A compound sequence/route index and `limit + 1` read bound acquisition and supply a
real overflow witness (`has_more`), even with many objects on one tick. No bodies
are preloaded. Missing, boolean, negative or noninteger legacy ticks remain unknown
and are excluded, not repaired to zero. Empty, disabled and unavailable surfaces
are distinguishable. A missing candidate source does not prevent zero-link review.
The counter is a Mneme capture clock, not elapsed time or every model generation.

The compact surface carries status, reason, anchor, lookback, limit, candidates
(`review_id`, optional `claim`, `mneme_call_seq`) and `has_more`. Candidate acquisition
is independent of relation application: a future selected pointer may supply the
same exact-route/claim candidates without changing the review payload. This slice
does not implement a pointer-provider framework or an arbitrary-source MCP input.

## Optional authorship

Read selected originals with `get_item` before writing a relation. Claims and
proximity are navigation, not factual grounds. Add optional top-level `relations`
to either legacy or multi-mnion `consolidate_review` payloads:

```json
{
  "selected_ids": ["memory_tag_example_a", "memory_tag_example_b"],
  "summary": "The new understanding, authored by the live agent.",
  "valence": 0.7,
  "member_ids": ["memory_tag_example_a", "memory_tag_example_b"],
  "relations": [{
    "mnion_index": 1,
    "target_review_id": "review_existing_example",
    "relation_kind": "continues",
    "relation_summary": "The specific development of the opened original, including grounds and uncertainty."
  }]
}
```

Example identifiers are placeholders: use the exact pending selected IDs and an
exact route from the pending candidate surface. `mnion_index` starts at 1 and
addresses the new mnion (or position in `mnions[]`). The direction is **new source
continues/corrects/follows_from existing target**. At most 8 relations are accepted;
unknown fields, invalid indices, duplicate relations, unavailable/out-of-surface
or malformed target routes are rejected before recording semantic outcomes.
No-item review packets cannot carry relations. Later deliberate relations remain
available through `connect_items`, including routes outside the temporal window.

## Persistence and recovery

New mnions and resolved `MnionConnection` records are appended in **one review
receipt**, not sequentially to two independent ledgers. The original standalone
connection ledger remains append-only and both sources feed existing adjacency.
The Mnion semantic body is unchanged. Original items, claims and routes are never
rewritten; external connection append order is retained, with review connections
woven by recording timestamp. This serial-writer slice does not claim a concurrent
multi-process transaction or immunity to torn filesystem writes.

Before the latch is cleared, item and connection projection must succeed. After a
recorded projection failure, retry the **same** review payload: the pending attempt
reuses the recorded receipt/edge IDs; changed authorship is rejected. Ordinary
capture may repair and verify the complete recorded result before lazy clearing.
A successful closure returns `connections[]`; get_neighborhood returns the same
edges and connected ingress can expose eligible endpoints with claims. An identical
later connect_items call reuses an inline edge instead of duplicating it.

This proves a formation/return path, not general usefulness of temporal candidates,
causality, feedback reinforcement, or automatic semantic consolidation.
