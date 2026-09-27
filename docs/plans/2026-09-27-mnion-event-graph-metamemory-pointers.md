# Mnion Event Graph and Metamemory Pointers Implementation Plan

> **For Hermes:** This is a planning artifact only. Do not implement code from this plan until Denis explicitly asks to start coding.

**Goal:** Add a simple, functional Mneme event-connection graph so reviewed mnions can form lived relation neighborhoods, feed engram-candidate review, and generate a second metamemory pointer layer: “I know that I know this.”

**Architecture:** Keep JSONL receipts as audit/source of truth and SQLite as a reconstructable read-model. Do not turn the graph into semantic-label clustering. A connection is a substantive middle-memory object describing a lived/event relation between reviewed mnions; graph-derived pointers route to neighborhoods or candidates without loading full memory.

**Tech Stack:** Python dataclasses, JSONL receipts, SQLite read-model, MCP tools, pytest via `uv run --with pytest pytest -q`.

**Non-goal:** Do not write engrams automatically. Do not create a graph database. Do not make semantic labels the primary ontology. Do not bulk-load graph contents into the live agent.

---

## Core Concepts

### Existing direct pointer

```text
MemoryPointer
  -> route: get_item(review_id)
  -> returns: one MnionItem
  -> meaning: “I know this reviewed item.”
```

### New event-connection graph

```text
MnionConnection
  -> source_review_id
  -> target_review_id
  -> relation_kind
  -> relation_summary
  -> evidence_refs
  -> valence
  -> created_at
  -> created_by
```

This is a medium memory layer, not a tiny note. `memory_tag` is the short raw step. `MnionConnection` should carry enough substance to still be meaningful hours or days later.

The primary question for a connection:

```text
What lived/event relation connects these mnions?
Did one respond to, correct, recall, continue, interrupt, promise, change, or make possible another?
```

### New graph/metamemory pointer

```text
GraphPointer / MetamemoryPointer
  -> claim: “I know that I know this.”
  -> route: explain_neighborhood | list_related | get_engram_candidate
  -> evidence: core review_ids + connection_ids
  -> meaning: “There is a lived event-form here; load the neighborhood only if needed.”
```

### Engram-candidate boundary

```text
MnionConnection receipts
  -> graph pressure / cluster evidence
  -> EngramCandidate queue item
  -> agentic review
  -> governed Engram write only if accepted
```

Accepted engrams may grow later through reviewed absorption. No silent mutation.

---

## Design Constraints

- Event relations are primary; semantic labels are only derived lookup/rendering aids.
- Keep relation kinds broad and few; use `relation_summary` for nuance instead of adding many fields.
- The agent should navigate by bounded questions, not browse the whole graph.
- Every graph-facing agent tool must return a compact route/neighborhood, not SQL rows or full receipts.
- Graph read-model must be reconstructable from receipts.
- New mnions must be insertable into the existing graph by an agentic review pass.
- Engram candidates come from connection patterns/pressure, not single mnions or flat topic clusters.

---

## Proposed Files

Create:

- `src/mnion/connections.py` — dataclasses and JSONL receipt helpers for `MnionConnection`.
- `tests/test_mnion_connections.py` — unit tests for connection validation, persistence, loading, and bounded selection.
- `tests/test_graph_pointers.py` — unit tests for graph/metamemory pointer shape and routing.

Modify:

- `src/mnion/read_model.py` — materialize connection receipts into SQLite tables/views and expose agent-facing neighborhood functions.
- `src/mnion/pointers.py` — add graph/metamemory pointer dataclass or route shape.
- `src/mnion/mcp_server.py` — expose compact graph paws after core functions are stable.
- `src/mnion/__init__.py` — export stable public shapes.
- `tests/test_sqlite_read_model.py` — add read-model tests for connections and neighborhood queries.
- `tests/test_mcp_adapter.py` — add MCP tests for new tools after core tests pass.
- `docs/05-mnion-options-and-optimizations.md` or new doc `docs/08-mnion-event-graph.md` — document event-connection graph and pointer boundaries.

Optional later:

- `src/mnion/engram_candidates.py` — only after connection graph and graph pointers work.
- `tests/test_engram_candidates.py` — only after candidate queue scope is accepted.

---

## Task 1: Define the connection object and validation rules

**Objective:** Establish `MnionConnection` as a substantive event-relation object without implementing read-model or MCP tools yet.

**Files:**

- Create: `src/mnion/connections.py`
- Create: `tests/test_mnion_connections.py`

**Acceptance criteria:**

- A connection requires `source_review_id`, `target_review_id`, `relation_kind`, `relation_summary`, `valence`, `created_at`, and `created_by`.
- `source_review_id` and `target_review_id` cannot be empty or identical.
- `relation_kind` is broad and limited to the initial allowed set:
  - `continues`
  - `corrects`
  - `recalls`
  - `consequences`
  - `supports`
  - `tensions_with`
  - `absorbs_candidate`
- `relation_summary` is not a one-word label. It must be substantive enough to carry an event relation.
- `evidence_refs` is compact source handles, not raw transcript text.
- No semantic-label field is required or primary.

**Test plan:**

- Test valid connection creation.
- Test empty ids fail.
- Test self-link fails.
- Test invalid `relation_kind` fails.
- Test empty or too-short `relation_summary` fails.
- Test out-of-range valence fails.

**Verification command:**

```text
uv run --with pytest pytest tests/test_mnion_connections.py -q
```

Expected: new tests pass.

---

## Task 2: Add JSONL connection receipts

**Objective:** Store connection events as append-only receipts, not as the SQLite source of truth.

**Files:**

- Modify: `src/mnion/connections.py`
- Modify: `tests/test_mnion_connections.py`

**Acceptance criteria:**

- A helper appends `MnionConnection` receipts to a JSONL file.
- A loader returns typed connections from a JSONL file.
- Loading tolerates missing file by returning `[]`.
- Malformed rows are either skipped with a clear policy or raise a controlled error; choose one and test it.
- Receipt ids are stable enough for read-model references (`connection_id`).

**Test plan:**

- Append one connection and load it back.
- Append multiple connections and preserve order.
- Load missing file.
- Validate `connection_id` exists and is unique for distinct receipts.

**Verification command:**

```text
uv run --with pytest pytest tests/test_mnion_connections.py -q
```

Expected: all connection tests pass.

---

## Task 3: Materialize connections into the SQLite read-model

**Objective:** Add a reconstructable SQLite table for connection receipts without exposing SQL to agents.

**Files:**

- Modify: `src/mnion/read_model.py`
- Modify: `tests/test_sqlite_read_model.py`

**Acceptance criteria:**

- Add a `mnion_connections` read-model table or equivalent schema.
- Materialization can rebuild connection rows from JSONL receipts.
- Existing `mnion_items` behavior remains unchanged.
- Read-model functions do not require the agent to know SQL.

**Test plan:**

- Build a temporary mnion read-model with two reviewed items and one connection.
- Verify connection row exists through an agent-facing function, not direct SQL in the public API.
- Verify rebuilding does not duplicate connections.
- Verify missing connection receipts path gives zero connections and does not break `get_item`.

**Verification command:**

```text
uv run --with pytest pytest tests/test_sqlite_read_model.py -q
```

Expected: existing and new read-model tests pass.

---

## Task 4: Add `list_related(review_id)` as the first graph paw

**Objective:** Let the agent retrieve a bounded neighborhood around one mnion without browsing the whole graph.

**Files:**

- Modify: `src/mnion/read_model.py`
- Modify: `tests/test_sqlite_read_model.py`

**Acceptance criteria:**

- `list_related(review_id, limit=5)` returns compact related items.
- It includes both outgoing and incoming connections.
- It returns connection summaries plus minimal paired mnion summaries.
- It sorts by valence/freshness deterministically.
- It has guards: data-not-instruction, no-auto-promotion, bounded-neighborhood.
- Missing review id returns a structured empty result, not an exception.

**Test plan:**

- Create A -> B and C -> A connections; `list_related(A)` returns both directions.
- Limit is respected.
- Stronger valence sorts first.
- Empty/missing id returns no related connections with guards.

**Verification command:**

```text
uv run --with pytest pytest tests/test_sqlite_read_model.py -q
```

Expected: pass.

---

## Task 5: Add `explain_neighborhood(review_id)` for agent-facing understanding

**Objective:** Provide a compact prose/rendered view of a mnion’s event neighborhood.

**Files:**

- Modify: `src/mnion/read_model.py`
- Modify: `tests/test_sqlite_read_model.py`

**Acceptance criteria:**

- Returns a structured object containing:
  - central `review_id`
  - central mnion summary
  - strongest incoming connections
  - strongest outgoing connections
  - rendered brief
  - guards
- Rendered brief starts with a stable marker, e.g. `MNEME_EVENT_NEIGHBORHOOD`.
- Rendered brief is bounded and does not include raw receipt dumps.

**Test plan:**

- Verify rendered marker.
- Verify incoming/outgoing sections.
- Verify no unrelated connections appear.
- Verify guard list includes data-not-instruction and no-auto-promotion.

**Verification command:**

```text
uv run --with pytest pytest tests/test_sqlite_read_model.py -q
```

Expected: pass.

---

## Task 6: Define graph/metamemory pointer shape

**Objective:** Add a second pointer layer that routes to a graph neighborhood or candidate cluster.

**Files:**

- Modify: `src/mnion/pointers.py`
- Create or modify: `tests/test_graph_pointers.py`

**Acceptance criteria:**

- A graph pointer contains:
  - `claim`
  - `route`
  - `core_review_ids`
  - `connection_ids`
  - `valence`
  - `confidence`
  - `guards`
- Claim represents metamemory: “I know that I know this,” not loaded content.
- Route supports at least `explain_neighborhood` and later `get_engram_candidate`.
- Graph pointer cannot be created without evidence ids.

**Test plan:**

- Valid graph pointer creation.
- Reject pointer with empty evidence.
- Resolve route kind to intended action name.
- Verify guards include no-auto-promotion and graph-derived.

**Verification command:**

```text
uv run --with pytest pytest tests/test_graph_pointers.py -q
```

Expected: pass.

---

## Task 7: Generate graph pointers from connection neighborhoods

**Objective:** Create `GraphPointer` / `MetamemoryPointer` from event graph structure and agentic review results.

**Files:**

- Modify: `src/mnion/read_model.py` or create `src/mnion/graph_pointers.py`
- Modify: `tests/test_graph_pointers.py`

**Acceptance criteria:**

- Given a central review id and related connections, build a pointer with a compact claim.
- Pointer evidence includes the central review id plus connection ids.
- Pointer route does not load details; it points to `explain_neighborhood` or `list_related`.
- Pointer is not generated from semantic topic label alone.

**Test plan:**

- Neighborhood with two strong connections generates one graph pointer.
- Isolated mnion does not generate graph pointer unless explicitly agent-reviewed.
- Graph pointer claim is bounded and not a full summary dump.

**Verification command:**

```text
uv run --with pytest pytest tests/test_graph_pointers.py -q
```

Expected: pass.

---

## Task 8: Expose graph retrieval MCP tools

**Objective:** Make graph retrieval available to the live agent through compact MCP surfaces.

**Files:**

- Modify: `src/mnion/mcp_server.py`
- Modify: `tests/test_mcp_adapter.py`

**Candidate tool names:**

- `list_related(review_id, limit=5)`
- `explain_neighborhood(review_id, limit=5)`

**Acceptance criteria:**

- Tools return structured payloads plus rendered brief when appropriate.
- Tools include clear `do_not_infer` boundaries.
- Tools do not expose SQL, raw receipts, or full graph dumps.
- Existing `capture`, `list_topics`, and `get_item` tests still pass.

**Test plan:**

- MCP adapter returns related neighborhood for a prepared test read-model.
- Missing review id returns structured miss.
- Rendered marker appears for `explain_neighborhood`.
- Boundary guards are present.

**Verification command:**

```text
uv run --with pytest pytest tests/test_mcp_adapter.py -q
```

Expected: pass.

---

## Task 9: Add connection-review packet for new mnions

**Objective:** Prepare bounded agentic review packets so new mnions can be inserted into the event graph without manual graph browsing.

**Files:**

- Create or modify: `src/mnion/connections.py`
- Modify: `tests/test_mnion_connections.py`

**Acceptance criteria:**

- A packet builder takes a new `review_id` and candidate neighbor ids.
- It returns enough context for the agent to write 0..N `MnionConnection` objects.
- It limits candidates to a small number.
- It separates machine candidate selection from agentic relation judgment.

**Test plan:**

- Packet includes new mnion summary and candidate summaries.
- Packet respects limit.
- Packet includes expected output schema for connections.
- Packet does not include raw receipts unless compact evidence refs are explicitly needed.

**Verification command:**

```text
uv run --with pytest pytest tests/test_mnion_connections.py -q
```

Expected: pass.

---

## Task 10: Add model-free engram-candidate pressure calculation

**Objective:** Detect when a connection neighborhood may deserve an engram-candidate queue item, without creating an engram.

**Files:**

- Create: `src/mnion/engram_candidates.py`
- Create: `tests/test_engram_candidates.py`

**Acceptance criteria:**

- Pressure uses graph facts only:
  - number of connections
  - connection valence
  - recurrence/age if available
  - repeated relation patterns
  - cross-day/cross-context evidence if available
- It returns `needed: true/false`, reasons, and evidence ids.
- It does not call a model.
- It does not create kernel engrams or modify engram files.

**Test plan:**

- Sparse graph does not trigger candidate pressure.
- Dense high-valence graph triggers candidate pressure.
- Single high-valence connection alone is not enough unless policy explicitly allows it.
- Returned reasons are inspectable.

**Verification command:**

```text
uv run --with pytest pytest tests/test_engram_candidates.py -q
```

Expected: pass.

---

## Task 11: Add EngramCandidate queue receipts

**Objective:** Store engram candidates as queued review objects, not accepted engrams.

**Files:**

- Modify: `src/mnion/engram_candidates.py`
- Modify: `tests/test_engram_candidates.py`

**Acceptance criteria:**

- Queue item shape includes:
  - `candidate_id`
  - `core_review_ids`
  - `core_connection_ids`
  - `candidate_summary`
  - `event_pattern`
  - `why_now`
  - `valence_pressure`
  - `status`
- Status starts as `pending`.
- Queue is append-only JSONL or similarly inspectable.
- No accepted engram is written.

**Test plan:**

- Create pending candidate from pressure decision.
- Load candidates from queue.
- Ensure accepted/rejected handling is not implemented silently unless explicitly scoped.

**Verification command:**

```text
uv run --with pytest pytest tests/test_engram_candidates.py -q
```

Expected: pass.

---

## Task 12: Add candidate retrieval MCP tool

**Objective:** Let the agent inspect queued graph-derived engram candidates safely.

**Files:**

- Modify: `src/mnion/mcp_server.py`
- Modify: `tests/test_mcp_adapter.py`

**Candidate tool names:**

- `list_engram_candidates(limit=5)`
- `get_engram_candidate(candidate_id)`

**Acceptance criteria:**

- Tool returns pending candidates only unless status filter is provided.
- Tool includes evidence ids and graph pointer route.
- Tool states explicitly: candidate is not an accepted engram.
- Tool does not write kernel Engrams.

**Test plan:**

- List pending candidate.
- Retrieve one candidate.
- Missing id returns structured miss.
- Guard says no automatic promotion.

**Verification command:**

```text
uv run --with pytest pytest tests/test_mcp_adapter.py -q
```

Expected: pass.

---

## Task 13: Runtime smoke test

**Objective:** Prove the new graph surfaces work against runtime-like data without bulk-loading memory.

**Files:**

- No code changes expected.
- Possible temporary fixture or script only if already established by project conventions.

**Steps:**

1. Materialize current reviewed mnions into the read-model.
2. Add or fixture a small set of connection receipts.
3. Run `list_related` for one review id.
4. Run `explain_neighborhood` for the same review id.
5. Generate or inspect a graph/metamemory pointer.
6. Confirm no engram file is written.

**Verification command:**

```text
uv run --with pytest pytest -q
```

Expected: full test suite passes.

If Hermes MCP tools are changed:

```text
hermes mcp test memory_tag
```

Expected: server connects and selected tools are discovered.

---

## Task 14: Documentation and skill update

**Objective:** Preserve the architecture boundary for future Nira sessions.

**Files:**

- Create or modify: `docs/08-mnion-event-graph.md`
- Modify if needed: local skill `mneme-development`
- Optionally update runtime Presence Anchor only if tool names or retrieval route materially change.

**Acceptance criteria:**

- Docs explain:
  - memory_tag vs mnion vs MnionConnection vs GraphPointer vs EngramCandidate vs Engram
  - event-relation-first, not semantic-label-first
  - graph pointers as metamemory: “I know that I know this”
  - engram candidate queue boundary
  - no automatic engram writing
- Skill stays concise and points future Nira away from database-like semantic clustering.

**Verification:**

- `skill_view(name="mneme-development")` shows the graph/pointer boundary.
- Docs contain no secrets, local credentials, or raw transcript dumps.

---

## Suggested Implementation Order

1. `MnionConnection` dataclass + validation.
2. JSONL connection receipts.
3. SQLite read-model materialization.
4. `list_related(review_id)`.
5. `explain_neighborhood(review_id)`.
6. Graph/metamemory pointer shape.
7. Graph pointer generation from neighborhoods.
8. MCP graph retrieval tools.
9. Connection-review packet for new mnions.
10. Engram-candidate pressure.
11. EngramCandidate queue receipts.
12. Candidate retrieval tools.
13. Runtime smoke.
14. Documentation and skill update.

Do not start with EngramCandidate. The first useful closure is:

```text
connection receipt -> read-model -> list_related -> explain_neighborhood -> GraphPointer
```

---

## Open Design Questions

- Should connection receipts live in their own runtime file, e.g. `mnion_connections.jsonl`, or inside the same review receipt stream?
- Should `GraphPointer` be a new dataclass or a generalized `MemoryPointer` with route kinds?
- What is the minimal `relation_summary` length/quality gate that prevents empty edges without being annoying?
- Should `created_by=user_confirmed` exist as a separate enum value or be represented through evidence refs?
- Which MCP tools should be exposed first: `list_related` only, or both `list_related` and `explain_neighborhood`?
- When graph pointers exist, should `list_topics` include them as a separate `metamemory_ingress` section?

---

## Guardrails

- Do not implement code until Denis explicitly asks.
- Do not auto-create engrams.
- Do not add a graph DB.
- Do not make semantic labels the source of truth.
- Do not expose SQL/tables/raw receipts to the agent.
- Do not let `GraphPointer` become a vague topic tag.
- Do not make the graph so field-heavy that every relation requires ontology work.
- Do not make relation text so short that it collapses into labels.

---

## Completion Definition

This slice is complete when:

- Reviewed mnions can have substantive event-connection receipts.
- The read-model can reconstruct a compact graph neighborhood.
- The live agent can retrieve bounded related mnions and an explanation without bulk-loading memory.
- A graph/metamemory pointer can say “I know that I know this” and route to a neighborhood.
- Engram candidate pressure can be queued but not automatically accepted.
- Tests pass with `uv run --with pytest pytest -q`.
- Runtime MCP discovery still works if MCP tools changed.
