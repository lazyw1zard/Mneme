# Micro-Consolidation Selection Read-Model Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace the provisional latest-active mnion selection with token-cheap unread-active coverage backed by an internal read model that can use SQLite without exposing SQL to agents.

**Status:** Tasks 1-3 completed: `MicroConsolidationSelection`, `ReviewState`, `derive_review_state()`, and `select_unread_active_mnions()` now exist. `MicroConsolidationRequest` uses unread-active coverage and carries compact selection metadata.

**Architecture:** Mnion records and review receipts remain inspectable append-only evidence. A derived read model, likely SQLite, indexes active/unread/deferred/needs-rereview state and prepares compact semantic packets for agent review. Agents never query tables; they use compact paws/tools that return bounded review packets and coverage summaries.

**Tech Stack:** Python stdlib, JSONL audit records, SQLite via `sqlite3` when materialized, pytest via `uv run --with pytest pytest`.

**Code-reading convention:** Main logical code blocks should carry short comments that explain the boundary or transition being performed: audit receipts -> read model, active pool -> review queue, packet_limit as queue step, compact agent packet vs hidden ledger/SQL. Avoid noisy line-by-line paraphrase.

---

## Architectural decisions

### Decision 1 — Agent is not a SQL client

Agents must not inspect tables, write SQL, or manually diff receipt ids against mnions. Core APIs/tools should do storage work and return compact semantic packets:

```text
prepare_micro_consolidation_request()
  -> MicroConsolidationRequest(
       mnions=[bounded selected MemoryTagRecord...],
       selection=MicroConsolidationSelection(...),
       prompt=compact review prompt,
     )
```

### Decision 2 — SQLite is an internal read model, not Mneme's ontology

Use SQLite when it reduces selection complexity, token load, and runtime cost. Keep the conceptual boundary:

```text
append-only events / receipts = audit evidence
SQLite read model           = fast working index / queue
agent-facing tools          = compact paws
```

If SQLite state is deleted, it should be reconstructable from memory tag records and review receipts.

### Decision 3 — Worker is model-free first

A future worker may maintain the SQLite index and queue, but must not call a model, create semantic proposals, send messages, or promote memory in the MVP.

Allowed early worker:

```text
JSONL/events -> SQLite read model -> pending review queue
```

Not allowed early worker:

```text
queue -> model call -> semantic consolidation -> pointer ingress
```

### Decision 4 — Token budget is an acceptance criterion

Review packets must be bounded by count and later by serialized character/token budget. The agent should review only what is semantically necessary:

```text
unread_active_count / selected_count / reason / compact mnion fields
```

not full ledgers, tables, or old receipts.

---

## Minimal slice sequence

### Task 1: Define selection state dataclasses

Status: completed.

**Objective:** Add typed shapes for selection metadata without changing behavior yet.

**Files:**
- Modify: `src/mnion/micro_consolidation.py`
- Test: `tests/test_micro_consolidation.py`

**Step 1: Write failing tests**

Add tests for:

```python
def test_selection_metadata_can_describe_unread_active_coverage():
    ...
```

Expected fields:

```text
strategy
reason
selected_ids
unread_active_count
reviewed_active_count
deferred_count
backend
```

`backend` should be a string such as `derived_jsonl` or `sqlite_read_model`, but it must not imply agent SQL access.

**Step 2: Implement minimal dataclass**

Add:

```python
@dataclass(frozen=True)
class MicroConsolidationSelection:
    strategy: str
    reason: str
    selected_ids: list[str]
    unread_active_count: int
    reviewed_active_count: int = 0
    deferred_count: int = 0
    backend: str = "derived_jsonl"
```

**Step 3: Verify**

Run:

```bash
uv run --with pytest pytest tests/test_micro_consolidation.py -q
```

Expected: pass.

### Task 2: Add review-state derivation over receipts

Status: completed.

**Objective:** Build the logical read/unread state without adding persistent SQLite yet.

**Files:**
- Modify: `src/mnion/micro_consolidation.py`
- Test: `tests/test_micro_consolidation.py`

**Step 1: Write failing tests**

Cases:

```text
no receipts -> mnion is unread
reviewed outcome -> reviewed
ungrouped outcome -> reviewed but no proposal
deferred outcome -> deferred and eligible when policy includes deferred
reinforced after review -> needs_rereview later (can be pending TODO if reinforcement events are not yet read here)
```

**Step 2: Implement minimal pure function**

```python
def derive_review_state(review_receipts: list[dict]) -> dict[str, ReviewState]:
    ...
```

Keep it pure and JSON-compatible.

**Step 3: Verify**

Run targeted tests, then full suite:

```bash
uv run --with pytest pytest tests/test_micro_consolidation.py -q
uv run --with pytest pytest -q
```

### Task 3: Replace latest-active selection with unread-active coverage

Status: completed.

**Objective:** Prepare review packets from unread active memory tags, not newest active memory tags.

**Files:**
- Modify: `src/mnion/micro_consolidation.py`
- Test: `tests/test_micro_consolidation.py`

**Step 1: Write failing tests**

Test that:

```text
active reviewed mnions are skipped
active unread memory tags are selected
selection is bounded by packet_limit
oldest unread are selected first for fair coverage
high-valence unread can be priority-bumped if implemented in this slice
```

**Step 2: Implement selector**

```python
def select_unread_active_mnions(
    active_mnions: list[MemoryTagRecord],
    review_state: dict[str, ReviewState],
    *,
    packet_limit: int,
) -> MicroConsolidationSelectionPacket:
    ...
```

First implementation may be:

```text
high-valence unread first
then oldest unread
packet_limit by count
```

**Step 3: Preserve agent compactness**

`MicroConsolidationRequest` should include selection metadata and selected memory tags only. It should not include all receipts or full read-model state.

**Step 4: Verify**

Run:

```bash
uv run --with pytest pytest tests/test_micro_consolidation.py -q
uv run --with pytest pytest -q
```

### Task 4: Document SQLite read-model boundary before implementing SQLite

**Objective:** Make future SQLite addition obvious and prevent database-first drift.

**Files:**
- Modify: `docs/06-micro-consolidation.md`
- Modify: `docs/05-mnion-options-and-optimizations.md`
- Modify: `NEXT_STEPS.md`

**Step 1: Add storage boundary**

Document:

```text
SQLite may be introduced as internal read model / queue.
SQLite is not prompt-facing.
SQLite is reconstructable from audit events/receipts.
Agents use compact tools, not SQL.
```

**Step 2: Verify markdown fences**

Run:

```bash
python - <<'PY'
from pathlib import Path
fence = chr(96) * 3
for name in ('NEXT_STEPS.md','docs/05-mnion-options-and-optimizations.md','docs/06-micro-consolidation.md'):
    text = Path(name).read_text(encoding='utf-8')
    fences = text.count(fence)
    print(name, fences, fences % 2 == 0)
PY
```

Expected: all `True`.

### Task 5: Add SQLite adapter only when selector shape is stable

**Objective:** Materialize the read model in SQLite without changing the agent-facing API.

**Files:**
- Create or modify: `src/mnion/read_model.py`
- Test: `tests/test_read_model.py`

**Step 1: Write tests for reconstructability**

Test that JSONL/receipt fixtures rebuild the same read state into SQLite.

**Step 2: Implement schema**

Minimal tables:

```text
mnions
review_state
micro_consolidation_reviews
micro_consolidation_review_items
consolidation_queue
```

**Step 3: Keep direct SQL private**

No agent-facing function returns SQL rows. Public functions return dataclasses/dicts shaped for tools.

**Step 4: Verify**

Run:

```bash
uv run --with pytest pytest tests/test_read_model.py -q
uv run --with pytest pytest -q
```

### Task 6: Add model-free queue maintenance later

**Objective:** Prepare for a worker without adding semantic autonomy.

**Files:**
- Future: `src/mnion/queue.py`
- Future: `tests/test_consolidation_queue.py`

**Allowed behavior:**

```text
compute review_due
create/update pending queue item
cool stale queue items
prepare compact review packet artifact
```

**Forbidden behavior:**

```text
call model automatically
create proposals automatically
create pointers automatically
write kernel/engram memory
send outbound messages
```

---

## Acceptance criteria

- `latest active 10` is no longer the real selection policy; it remains only historical/probe wording.
- Every active mnion can receive at least one bounded consolidation review before expiry unless explicitly cooled/deferred.
- Agents receive compact semantic review packets, never SQL/tables/full ledgers.
- Review receipts remain inspectable.
- SQLite, if introduced, is an internal reconstructable read model and queue substrate.
- No background semantic worker runs without a separate governance decision.
- Tests pass with:

```bash
uv run --with pytest pytest -q
```
