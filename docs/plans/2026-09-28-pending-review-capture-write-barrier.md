# Pending Review Capture Write-Barrier Implementation Plan

> **For Hermes:** Use this as a bounded GrowCycle slice; implement directly with TDD and verify before commit.

**Goal:** Make Mneme review pressure intrusive enough that missed `MNEME_REVIEW_PRESSURE` cannot be silently bypassed by ordinary new captures.

**Architecture:** Add a compact persistent pending-review latch in the runtime state directory. `capture` persists the latch when pressure triggers; later ordinary `capture` checks the latch before appending a new `memory_tag` and redirects to the pending packet instead of writing. The latch is resolved lazily when review receipts cover its selected ids.

**Tech Stack:** Python dataclasses/JSON, existing MCP adapter tests, existing micro-consolidation receipt JSONL.

---

### Task 1: RED test for pending latch persistence

**Objective:** A high-valence pressure capture creates a compact pending-review artifact.

**Files:**
- Modify: `tests/test_mcp_adapter.py`
- Later create: `src/mnion/review_pressure_state.py`
- Later modify: `src/mnion/mcp_server.py`

**Steps:**
1. In `test_mcp_adapter.py`, call `create_server(..., pending_review_path=tmp_path / "pending_review.json")`.
2. Call `capture` with high valence.
3. Assert `pending_review.json` exists and contains `selected_ids`, `reasons`, `packet_limit`, `agent_ingress`, and `semantic_auto_consolidation=false`.
4. Run targeted test and confirm failure because `pending_review_path` does not exist yet.

### Task 2: RED test for pre-capture redirect barrier

**Objective:** A pending review blocks ordinary capture before seq/ledger mutation.

**Files:**
- Modify: `tests/test_mcp_adapter.py`

**Steps:**
1. After Task 1 high-valence capture, record ledger lines and `mneme_call_seq`.
2. Call `capture` with low valence and no override.
3. Assert `ok=false`, `action="redirected_to_pending_review"`, `agent_ingress.rendered` contains `MNEME_REVIEW_PRESSURE`, `proposed_capture` is present, and no new ledger line/seq increment occurred.

### Task 3: Implement pending-review state helpers

**Objective:** Keep latch logic small, inspectable, and storage-only.

**Files:**
- Create: `src/mnion/review_pressure_state.py`

**Implementation:**
- `pending_review_path_for_state_dir(state_dir)`
- `load_pending_review(path)`
- `write_pending_review(path, *, decision, review_request, ingress)` using atomic replace
- `pending_review_is_resolved(pending, receipts)` when all selected ids are reviewed/deferred by derived review state
- `clear_pending_review(path)`

### Task 4: Wire latch and redirect into MCP capture

**Objective:** Use barrier before `capture_memory_tag`, and persist latch after pressure.

**Files:**
- Modify: `src/mnion/mcp_server.py`
- Modify: `src/mnion/__init__.py` if exports are useful

**Implementation:**
1. Add optional `pending_review_path` parameter to `create_server`.
2. At start of `capture`, load receipts and pending latch.
3. If pending exists and is unresolved, return redirect without calling `capture_memory_tag`.
4. After normal capture, if pressure is needed and ingress exists, write pending latch.
5. If pending is resolved by receipts, clear it before allowing capture.

### Task 5: Test resolution after receipt coverage

**Objective:** Reviewed pending selected ids reopen ordinary capture.

**Files:**
- Modify: `tests/test_mcp_adapter.py`

**Steps:**
1. Create pending latch by high-valence capture.
2. Append a minimal receipt covering selected ids to `receipts_path`.
3. Call ordinary low-valence capture.
4. Assert it succeeds and pending latch is cleared/absent.

### Task 6: Verify and commit

**Commands:**
```bash
PYTHONPATH=src uv run --with pytest pytest tests/test_mcp_adapter.py tests/test_review_pressure_config.py -q
PYTHONPATH=src uv run --with pytest pytest -q
python -m py_compile src/mnion/mcp_server.py src/mnion/review_pressure.py src/mnion/review_pressure_state.py
git diff --check
git status --short --branch
```

**Commit:**
```bash
git add src/mnion tests docs/plans/2026-09-28-pending-review-capture-write-barrier.md
git commit -m "feat: add mneme pending review write barrier"
git push
```

## Guardrails

- No semantic auto-consolidation.
- No raw SQL/tables/receipt scans in tool output.
- Redirect response must include proposed capture so the agent can decide after review.
- Default to silence/blocking rather than silently writing more tags when latch state is ambiguous.
- Keep override/defer out of this first slice unless tests force it; a later slice can add reasoned overrides.
