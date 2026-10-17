# Presence anchor and MCP placement

This describes the product contract. Actual host registration, enabled tools and
receptor activation must be checked in the selected host/profile; repository
files alone do not prove a live configuration.

## Always-visible reminder

A host-native bootstrap surface should remind the active agent that Mneme exists
outside the visible conversation. In a Hermes profile this may be
`$HERMES_HOME/SOUL.md`; the profile adapter is not a replacement for an agent's
canonical semantic kernel.

The reminder establishes bounded navigation:

```text
topic/claim map -> exact item route -> get_item -> MnionItem
connected entry -> get_neighborhood -> selected get_item originals
```

It does not declare retrieved content privileged, exhaustive, true by default,
or automatically eligible for kernel/engram promotion. Absence from a compact
map is not proof that Mneme has no relevant memory.

## Portable explicit MCP tools

`src/mnion/mcp_server.py` exposes:

- `capture`: a compact ephemeral memory tag, not a reviewed mnion or engram.
- `consolidate_review`: apply the live agent's explicit semantic review and
  per-tag outcomes to a pending packet; verify materialized results before
  clearing its latch. Infrastructure does not author the summary.
- `list_topics`: compact topic metadata, exact routes and optional navigation
  claims, not full bodies.
- `get_item`: one selected MnionItem by exact item route. Explicit supported
  route hints remain distinct from exact identity and may be ambiguous.
- `annotate_claim`: append a later navigation annotation to an opened original
  without replacing its original semantic fields or receipt.
- `connect_items`: append a deliberate directed relation between two opened
  exact originals, with substantive grounds and uncertainty.
- `get_neighborhood`: bounded route/claim nodes and authored edges. It does not
  load all original bodies or turn a connected component into an engram.

Hosts with tool include-lists must select the tools they intend to expose and
reload their discovery as appropriate. A configured server name such as
`memory_tag` is host registration, not the identity of the core organ. Hermes
configuration normally lives at `$HERMES_HOME/config.yaml`; do not infer the
contents of another profile or silently modify it.

When capture redirects to pending review, follow its explicit closure action;
annotations and relations do not bypass or clear a pending consolidation latch.

## Freshness and explicit retrieval

`list_topics` and `get_item` check source/read-model freshness and repair only
when necessary, rather than rebuilding on every call. Results expose compact
`read_model_status`, `read_model_refreshed` and `materialized_count` metadata.
Explicit neighborhood retrieval may likewise repair stale projections. Fresh
reads remain distinct from repair, and optional source availability is not a
blanket guarantee that every index is current.

A selected item exposes `review_id`, `mnion`, `grouped_ids`, `created_at`, guards
and applicable claim provenance. Raw receipt JSON and SQL rows are not the agent
interface. Claims are navigation; factual answers must be grounded in opened
originals and their supported evidence.

## Spontaneous host ingress

The Hermes adapter reads the core's bounded materialized surface: compact
`MNEME_METAMEMORY_SURFACE` topics/claims and optionally one two-node/one-edge
`connected_entrance`. Exact routes in the current cue may anchor that entrance;
otherwise the latest eligible authored relation supplies a memory-state reminder.
This does not establish semantic relevance or unfinished-story detection.

The pre-turn hot path never repairs/migrates the index, scans all receipts,
loads full mnion bodies, calls a model or performs consolidation. Missing or
unavailable optional graph data must not turn into a claim of no memory or
suppress an otherwise usable topic map.

The host's recall-status wording is a separate UI layer. A generic count does
not establish that the live agent selected, opened or used that many originals.

## Internal substrate

Default state uses `MNEME_STATE_DIR`, otherwise XDG state under `mneme`:

- `memory_tags.jsonl` and `mneme_seq.json`: raw capture/call-age material;
- `micro_consolidation_reviews.jsonl`: reviewed semantic source evidence;
- `claim_annotations.jsonl` and `mnion_connections.jsonl`: later authored overlays;
- `mneme_read_model.sqlite3`: reconstructable item/adjacency index;
- `pending_review.json`: review closure latch.

Agents use compact tools, not SQL/table/receipt scans. Original memory semantics
remain unchanged by annotation/connection authoring. See the accepted
[connection contract](plans/authored-connections.md),
[connected ingress contract](plans/connected-ingress.md), and
[current direction](../NEXT_STEPS.md).
