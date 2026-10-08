# Claims and relations — next slices implementation plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make a memory route intelligible before opening it, then preserve agent-authored relations well enough for event-based long-term consolidation.

**Architecture:** Keep the existing compact metamemory map and deliberate `get_item` boundary. Add an optional agent-authored claim, then a bounded annotation path for existing items; introduce optional relations only after navigation is verified. Do not revive the withdrawn standalone events field, preload bodies, or restore dictionary initiative above agent choice.

**Tech Stack:** Python dataclasses, append-only review/annotation receipts, reconstructable SQLite read-model, MCP, external Hermes MemoryProvider, pytest, disposable MCP stdio tests.

**Status:** Ordered slices, not authorization to execute all stages at once. This turn plans work; no production implementation is changed. Before a later slice begins, inspect its exact call sites and refine its implementation-level tests. API sketches below are proposed additions, not currently available functions.

## Verified starting point

- `faecc00`: standalone events prototype retired; no active events field, handlers or tests.
- `d679002`: exact-route and explicit hex-hint recall boundaries repaired; ambiguity does not guess a memory.
- Latest executed full suite: 155 passed. Unit tests, independent review, isolated real MCP stdio smoke and a fresh-process read of one existing item passed for the recall slice.
- Hermes MemoryProvider already injects `MNEME_METAMEMORY_SURFACE`, not full bodies.
- `Mnion` currently contains `summary`, `valence`, `rationale`; claims and graph writes are not implemented.
- Claude's report: `docs/experiments/2026-10-08-claim-recall-probe.md`. Qualitative support for meaningful entries, not controlled proof: conditions exposed three versus seven routes, one model and one run per cell. Chronology from body dates does not establish the usefulness or uselessness of relations.
- Agentboard cleanup `261005-787b` is already in Denis's `next`; preserve that order. Retired events card `261007-328b` is archived.

## Slice 0: Close the existing ingress cleanup

**Objective:** Remove abandoned gate/preload machinery only after distinguishing live imports, public compatibility and actual host behavior.

**Files to inspect:**
- `src/mnion/ingress.py`
- `src/mnion/read_model.py`
- `src/mnion/active_surface.py`
- `src/mnion/mcp_server.py`
- `src/mnion/__init__.py`
- `tests/test_ingress.py`, `tests/test_active_surface.py`, `tests/test_hermes_memory_provider.py`, `tests/test_mcp_adapter.py`
- Existing architecture notes in `DECISIONS.md` and the older ingress/graph plans.

**Step 1:** Trace imports and tool consumers before declaring code dead. Known live seams: `active_surface.py` imports `SOURCE_UNAVAILABLE_GUARD` from `ingress.py`; MCP `list_topics` still returns a legacy active-ingress payload. Deleting a whole module by name would break live behavior.

**Step 2:** Run the existing targeted suite as the compatibility baseline:

```bash
uv run --with pytest pytest tests/test_ingress.py tests/test_active_surface.py tests/test_hermes_memory_provider.py tests/test_mcp_adapter.py -q -o addopts='' --tb=short
```

**Step 3:** Add RED regressions for the selected public behavior change, if any. Distinguish removal of unused internals from retirement of a consumed API. Preserve unavailable-versus-absent semantics, exact item routes and route-first prefetch. If a legacy surface must be retired, explicitly test and document that transition rather than silently dropping it.

**Step 4:** Move any genuinely shared guards into a small host-neutral seam if required, then remove only proven abandoned code. Do not retain a new auxiliary scorer to justify the old gate.

**Step 5:** Full tests, real provider/MCP smoke, independent review, commit/push. Update the cleanup card to review, never mark feature completion merely because a file disappeared.

## Slice 1: Optional authored claim, through the whole recall path

**Objective:** I can recognize what a route contains without loading its body or guessing from an opaque ID.

**Files:**
- Modify `src/mnion/micro_consolidation.py` (Mnion, prompt, validation, receipt conversion)
- Modify `src/mnion/mcp_server.py` (single/packet consolidation and retrieval guidance)
- Modify `src/mnion/read_model.py` (cached claim/projection and compatibility)
- Modify `src/mnion/active_surface.py` (claim attached to its exact listed route)
- Test `tests/test_mnion_claims.py` (new), plus existing SQLite, MCP, active-surface and provider suites.

**Step 1: RED — proposed public behavior**

```python
def test_claim_is_agent_authored_and_optional():
    claim = "Denis rejected the dictionary gate because it overruled agent-selected meaning."
    assert Mnion(summary="Gate correction", valence=0.8, claim=claim).claim == claim
    assert Mnion(summary="Legacy memory", valence=0.4).claim is None
```

Also test malformed/blank/oversized claims, immutable/exact authorship, validation before receipt/latch mutation, packet-route isolation, legacy receipts/DBs and no body preload. Choose a documented bound during this slice, not an arbitrary mandatory sentence form.

**Step 2:** Run the new tests and confirm failure because claim support is absent, not because of fixture mistakes.

**Step 3:** Implement the smallest compatible shape: `claim: str | None = None`. Claim names a concrete change or understanding, not a topic and not a mandatory literal "I know that I know" prefix. Missing claims keep legacy memory useful; never synthesize them during retrieval.

**Step 4:** Preserve existing item addresses. Store/index the claim as authored data and attach it to that exact route in the map. Keep topic grouping, visible-route coverage and output budgets bounded; do not replace topic abstraction with full summaries. Spontaneous prefetch stays read-only, without receipt scans, model calls or semantic reconstruction. Refresh/migration belongs to explicit write/repair paths.

**Step 5:** Verify new and legacy receipt roundtrips, direct/packet MCP transport, real plugin prefetch, full tests, independent review and push. This slice does not add graph edges or backfill the whole memory.

## Slice 2: Annotate a small existing corpus without rewriting history

**Objective:** Existing useful mnions can acquire a meaningful entry without pretending they were originally written with one.

**Proposed new seams:** `src/mnion/annotations.py`, `tests/test_mnion_annotations.py`; integrate with `read_model.py` and one explicit agent-facing write affordance only after reviewing the existing lifecycle boundary.

**Step 1:** Select a small representative corpus via exact `get_item` routes. Do not inspect tables or bulk-load receipts into agent context. Read each selected body before authoring its claim.

**Step 2: RED — contract sketch**

```text
append claim annotation(exact_item_route, authored_claim)
-> original review receipt remains byte-identical
-> read-model and selected get_item expose the accepted claim
-> neighbouring packet items are unchanged
```

Test unknown routes, malformed IDs/claims, literal suffix preservation, repeated updates, stale projections and read-model failure. Receipt order/identity must define accepted update precedence rather than wall-clock guessing.

**Step 3:** Implement an append-only annotation receipt keyed to an exact item route. Use a governed core write path; do not bury new lifecycle logic in one host adapter or auto-clear a pending consolidation barrier. Keep this a separate bounded slice if lifecycle extraction is needed.

**Step 4:** Apply only agent-authored annotations to selected real items, then read back the exact routes. No automatic mass rewriting, synthetic production tags or invented dates/relations.

**Step 5:** Verify, review and push. Defer whole-memory backfill until the small real corpus demonstrates value.

## Slice 3: Controlled fresh-agent recall check

**Objective:** Distinguish a useful entry from an apparently fluent answer based only on a label.

**Proposed artifacts:** `docs/experiments/claim-recall-controlled/` containing the fixed questions, selected exact routes, expected supported facts, map variants and an executable host runner chosen from actually available tooling. Do not fabricate missing Claude probe files or model responses.

**Step 1:** Freeze one corpus and the same route coverage, ordering, bodies and get_item tools across A (route-only) and B (claims). No seven-versus-three visibility confound. Predeclare historical questions before writing reusable claims.

**Step 2:** Run fresh agents with no prior conversation history or write access. Record tool calls and raw results. If the required model/harness is unavailable, report that blocker rather than substituting invented outcomes.

**Step 3:** Score separately: correct route choice, successful exact retrieval, supported answer, unsupported attribution/details. Include the dictionary-gate correction and distinguish receipt time from occurrence time.

**Step 4:** Proceed only when failures are localized and the navigation layer works in a bounded real test. Pytest and schema checks are necessary but do not replace this semantic evaluation.

## Slice 4: Optional relations, then one long-term consolidation experiment

**Objective:** I can retrieve how one trace continued or corrected another without reconstructing previously authored topology from scratch.

**Files:** Choose a small `src/mnion/connections.py` core receipt/projection seam, `tests/test_mnion_connections.py`, and integration points in `micro_consolidation.py`, `read_model.py`, `mcp_server.py` after the prior slices. These are proposed files, not existing APIs.

**Step 1:** RED tests for an optional connection: exact source/target item routes, `continues | corrects | follows_from`, and authored `relation_summary`. Reject unknown/malformed/cross-packet targets before applying state. A missing relation must not break a usable claim.

**Step 2:** Expose only a bounded set of neighbouring route/claim entries during review, not the whole graph. Allow zero relations. Keep uncertain grounding in the explanation; `follows_from` is not automatically demonstrated causality. Raw capture `linked_ids` are not ready item routes.

**Step 3:** Persist the agent's selected topology and expose deliberate bounded neighbourhood retrieval. Traverse routes/kinds mechanically; do not make an agent rediscover stored edges on every lookup. Retrieval may later reveal an additional relation, but authoring it remains explicit.

**Step 4:** Extend the fixed recall evaluation with questions that require several memories and explanatory relationships, not only date ordering.

**Step 5:** Try agentic long-term consolidation of one selected arc: what began, changed, why, and remains. Preserve source routes, disagreements and uncertainty. A connected component is candidate material, not an automatic engram. Accept or decline one candidate explicitly before expanding the mechanism.

## Deliberately outside this plan's immediate implementation

- Standalone events field / addressable event ontology.
- Whole runtime-event import, automatic long-term memory promotion or semantic consolidation daemon.
- Numerical edge weights, usage reinforcement and a separate forgetting-policy project.
- Pulse/DefaultMode/Grow changes, speculative cooling bugs or unverified runtime-event counts.
- New word gates, compulsory graph-placement ceremonies or a database UI for the agent.

## Verification and landing rule

For each code slice: RED/GREEN, full `uv run --with pytest pytest -q -o addopts='' --tb=short`, compilation, diff checks, isolated real MCP transport/provider smoke, independent review, commit and push with remote read-back. Live mutations require bounded meaningful material and exact read-back; no diagnostic tag pollution. Keep implementation status, semantic experiment results and MCP reload status distinct.
