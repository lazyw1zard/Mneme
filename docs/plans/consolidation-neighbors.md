# Consolidation neighbors — implementation plan

**Goal:** I can form memory with optional grounded relations to existing nearby mnions, without a second compulsory graph-placement pass.

**Authorship:** I implement the architectural passage myself; independent agents perform read-only specification and quality/security review, not implementation. This overrides generic subagent implementation handoff.

**Architecture:** Candidate acquisition is separate from review application. First source: bounded backward window by receipt `mneme_call_seq`, not topic-map popularity. Optional authored connections are stored with the new mnions in the same review receipt (one append), then projected into existing adjacency. No second semantic object tier or background model.

**Tech stack:** Python dataclasses, SQLite derived read model, JSONL append-only receipts, existing FastMCP tools.

## Scope / contract

- First level of work: preservation and consolidation. No cue, feedback weights, forgetting, artifact storage, persistent metapointer or semantic search.
- `[consolidation_neighbors]`: `enabled=true`, `lookback_calls=40`, `candidate_limit=4` configurable defaults. Strict bool/int validation; positive limit, nonnegative window. Do not modify production config before verification.
- Project receipt call sequence as nullable indexed metadata, not Mnion body. Missing/invalid legacy seq stays unknown/excluded, never coerced to zero. Equal seq allowed for distinct reviews. Keep original bytes and routes.
- Packet anchor is current seq at review opening. Query `[max(0, anchor-lookback), anchor]`, order seq descending then exact route ascending, fetch `limit+1` for truthful has_more. No corpus/body scan for acquisition, no LLM, no topic gate. Return routes+optional claims+seq+selection reason, never summary/rationale. Disabled/unavailable differs from no candidates; lack of candidates must not break legacy consolidation.
- Freeze bounded candidate surface in pending packet; retries see same candidates. Future pointer-derived candidates can use the same route/claim surface without changing semantic consolidation. No provider framework now.
- `consolidate_review` gets optional `relations` list. Each entry: `mnion_index` (1-based new group), `target_review_id` (literal candidate route), `relation_kind`, `relation_summary`. New source -> existing target. Zero links is normal. Agent opens selected originals via get_item before authorship. No automatic inference. At most existing MAX_CONNECTIONS per review; malformed/duplicate/unknown target/index rejects before receipt write.
- Same receipt contains mnions+resolved connection records+original relation intent. Projection failure keeps pending. Same-input retry reuses recorded receipt; changed retry is rejected. Capture-side lazy closure must verify combined item/connection projection, not erase unprojected relation intent.
- Later standalone connect_items continues to work and can reuse inline connection IDs; integrated edges are available to get_neighborhood and connected ingress after projection. Serial writer scope only; no claim of distributed transactions or multi-process concurrency safety.

## Tasks (RED -> GREEN -> verify each)

1. **Config and temporal projection** (`config.py`, `read_model.py`, tests/test_consolidation_neighbors.py): test default/custom/invalid config; legacy nullable seq; migration/rollback/freshness; indexed lower/upper boundary, ties, caps, unknown seq and missing read-only DB. Run isolated helper then implement smallest change.
2. **Packet exposure** (`neighbors.py`, `mcp_server.py`, `review_pressure_state.py`): test pressure opening exposes/fixes bounded candidates, redirect retains them, disabled/unavailable still permits old closure. Keep public ingress untouched.
3. **Integrated authorship** (`micro_consolidation.py`, `connections.py`, `mcp_server.py`): test zero links unchanged, multi-group source mapping, strict IDs/payloads no writes, one append for mnions+links, directed roundtrip and standalone compatibility. Avoid a two-ledger half-commit by embedding edges in receipt; existing connection ledger remains append-only.
4. **Recovery**: inject item/adjacency failures after append; pending retained; exact retry adds no receipt/edge, changed retry rejected; capture repairs/verifies before lazy clear. No-item packets cannot carry relations.
5. **Verification**: targeted tests, full Python suite, mocked Node host, actual isolated MCP stdio, original-byte guards, independent read-only SPEC then QUALITY/security. Parent reproduces/fixes blockers with RED tests and requests re-review.
6. **Land**: docs/readme/config example/current overview and Agentboard update, reviewed commit, fast-forward main/push/read remote. Fresh accepted-source read-only smoke; report deployment/reload boundary accurately. Production mutations limited to explicitly documented config change if necessary; no synthetic memory captures.

## Commands / evidence

All tests run with disposable HOME/XDG/HERMES/MNEME/config and subprocess propagation:

```bash
python3 /home/nira/archives/mneme/run-neighbor-tests.py --phase red tests/test_consolidation_neighbors.py
python3 /home/nira/archives/mneme/run-neighbor-tests.py --phase full
```

Helper hashes live Mneme state/config before and after. Baseline: 479 Python passed, live bytes unchanged. Exact RED/GREEN/full logs stay local/private, neutral product tests/docs only go public.

## Acceptance

A real isolated MCP flow exposes configured temporal candidates; chosen original opens; one review saves new mnion and optional authored edge; both reopen; old originals/counters stay unchanged by closure. Zero-link legacy flow still works. Candidate query work and output are bounded; snapshot is explicitly partial. Failure/retry cannot silently drop relations or duplicate already-recorded review. No claims of feedback efficacy or native Claude SDK validation.
