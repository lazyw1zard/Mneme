# Claims / route recall: integration notes

Source experiment: `docs/experiments/2026-10-08-claim-recall-probe.md`,
introduced by `a6ac45c`. Claude's initial resolver was introduced by `017c4ac`
and is integrated here with boundary corrections.

## What the experiment establishes, and what it does not

The reported agents used claims to select relevant memories. They also lost
parts of long item routes, sometimes answered from a label instead of opening
the body, and occasionally added unsupported attribution or a detail about R3.5.

Claims and relations remain experimental sidecar annotations, not shipped Mnion
fields. The before/after conditions differ in route coverage and grouping (the
baseline map shows three IDs whereas the draft exposes seven annotated items),
so these observations are useful qualitative evidence, not an isolated estimate
of the effect of claims. Relations added no measurable gain in the reported
chronology question; the agent could reconstruct its order from dates in bodies.
This does not test the necessity of explicitly persisted relation meaning. A future repeat should
hold memory bodies, available routes, questions and retrieval tools constant,
while varying just the navigation layer. Test successful route opening separately
from answer quality and test relations on genuinely multi-item questions.

No old receipts or production mnions are rewritten by this integration.

## Implemented recall contract

- Prefer the literal full `review_id` from a surfaced route.
- `get_item` additionally accepts a documented **route hint**: 6..32 lowercase
  hexadecimal characters, optionally prefixed by `review_`, with optional exact
  `:mnion:N` (`N >= 1`, no leading zeros). Exact legacy IDs still work.
- No trimming, quote removal, case folding, coercion or malformed-token repair.
  Invalid input returns `invalid_route_query` before read-model refresh.
- A unique hint returns the selected exact item route plus unchanged
  `resolved_from`. Ambiguity never guesses: return up to eight `did_you_mean`
  entries and `has_more_candidates`; the caller must select a listed exact route
  or narrow the hint. Preview text is bounded and is not factual evidence.
- Full item suffixes are literal: missing `:mnion:1` must not resolve to
  `:mnion:10`. The suffix remains literal even with a shortened hash hint.
- Candidate enumeration uses parameterized indexed prefix-range queries, a
  read-only connection, a short lock timeout, and at most nine candidate IDs
  (eight displayed plus one overflow witness), rather than fetching every ID.
  This bounds returned candidates, not all rows examined: an exact-suffix filter
  can examine the matching indexed hash-prefix range. A large-prefix performance
  regression remains useful before claiming a hard execution-work bound.
  The resolver cannot create storage or schema. Explicit MCP reads retain the
  existing freshness-check/repair behavior, separate from resolver lookup.
- MCP storage failures return `read_model_unavailable`, not absence of memory.
- Tool descriptions require grounding factual memory answers in an opened body,
  not a claim or candidate preview. This is agent guidance, not a deterministic
  guarantee against hallucination; semantic behavior still needs fresh-agent
  evaluation.

## Verification

Behavioral regressions cover exact/prefix collision, ambiguous packet routes,
wrong item suffixes, malformed queries, legacy IDs, bounded enumeration,
read-only behavior, no creation on missing/schema-less storage, invalid input
before refresh, explicit alias reporting, capped previews, and structured storage
failure. An isolated real MCP stdio smoke exercises capture → multi-mnion
consolidation → ambiguous packet → selected exact/hint retrieval, leaving no
pending latch. It does not write production state.

This slice repairs recall transport and clarifies evidence boundaries. It does
not implement claims, graph writes, events, or long-term event consolidation.
