# Packet outcomes and multi-mnion reviews

Status: implemented and verified in `fix: support multi-mnion packet reviews`; covers core receipt/read-model semantics, backward-compatible MCP packet outcomes, explicit queue outcomes, and fail-closed route verification.

## Problem

A selected review packet can contain more than one semantic object. The old single-mnion receipt left every non-member as `ungrouped_ids`. Keeping those ids unread prevented loss, but conflated three outcomes:

- reviewed noise that is safe to skip;
- a real trace deferred until an explicit reopen condition;
- a separate ready topic that should become another mnion now.

## Core receipt shape

`MicroConsolidationResult` can carry:

```text
mnion_groups: list[MnionGroup(mnion, member_ids)]
reviewed_noise_ids: list[memory_tag_id]
deferred: list[DeferredTagOutcome(memory_tag_id, reason, reopen_policy)]
```

Applying the result writes one packet-level audit receipt with:

```text
mnions[]             independently routed semantic items
grouped_ids          union of all semantic group members
reviewed_noise_ids   reviewed/noise queue outcome
deferred_ids         compatibility/read-state index
deferred[]           reason + reopen policy
ungrouped_ids        only packet members without a grouped/noise/deferred outcome
```

Semantic group member ids and explicit outcome ids must be disjoint and must come from the selected packet. Legacy single-mnion `MicroConsolidationResult(mnion, grouped_ids)` remains supported. Single-mnion receipts keep the top-level `mnion` field and packet review id as their established `get_item` route.

For a multi-mnion receipt, each nested mnion receives a distinct route:

```text
<packet-review-id>:mnion:1
<packet-review-id>:mnion:2
...
```

The reconstructable SQLite read-model materializes each route as a separate `MnionItem`. Agent-facing responses expose only `review_ids`, ready items, topic maps, and `get_item`; they do not expose SQL rows or receipt scans.

## MCP input modes

`consolidate_review` now has two mutually exclusive modes.

Legacy single-mnion mode remains accepted:

```text
selected_ids
summary
valence
member_ids
rationale?
```

Explicit packet mode accepts:

```text
selected_ids
mnions[] {
  summary
  valence
  member_ids
  rationale?
}
reviewed_noise_ids[]
deferred[] {
  memory_tag_id
  reason
  reopen_policy
}
ungrouped_ids[]
```

Packet mode does not default omitted selected ids to noise or ungrouped. Every selected id must occur in exactly one explicit grouped/noise/deferred/ungrouped outcome. Unknown, duplicate, overlapping, or missing ids fail closed without appending a receipt or clearing the latch.

## Queue state versus latch coverage

These remain separate questions:

```text
queue state
  grouped_ids / reviewed_noise_ids -> reviewed
  deferred_ids                     -> deferred
  ungrouped_ids                    -> unread

pending-latch audit coverage
  grouped + reviewed_noise + deferred + ungrouped can prove the selected packet was examined
```

Thus explicit noise no longer requeues, deferred tags stay deferred, and explicit/legacy ungrouped tags remain unread while still closing a reviewed pending packet.

## Fail-closed closure ordering

The MCP closure path remains:

```text
validate literal selected/outcome ids
-> reconstruct bounded pending packet
-> append one audit receipt
-> materialize the read-model
-> resolve every created review_id with get_item
-> verify receipt coverage of all pending selected_ids
-> clear pending latch
```

If materialization or any item read-back fails after receipt append, the receipt remains audit evidence and the latch remains pending. Capture-side lazy clearing also verifies every multi-mnion route before removing a retained latch.

No semantics are generated in a worker. Every summary, rationale, classification, deferred reason, and reopen policy comes from the live agent call.

## Deliberately deferred follow-up

A packet-mode review currently requires at least one semantic mnion. Supporting an all-noise or deferred-only packet needs an explicit no-item receipt/read-model verification rule so latch closure remains fail-closed without inventing a semantic object. Do not solve that by fabricating a placeholder mnion.

Further hardening can add file locking/idempotency for concurrent or repeated `consolidate_review` calls. It is outside this bounded slice.
