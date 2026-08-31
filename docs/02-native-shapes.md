# Mneme Native Shapes — first sketch

These are not final storage schemas. They are native shapes for thinking and testing the organ without collapsing it into a database.

## 1. `memory_pointer`

A pointer says: “I know that I know something here,” even when content is not loaded.

```yaml
memory_pointer:
  id: ptr_<stable-or-generated-id>
  claim: "I know that I know something about Mneme as metamemory."
  status: warm | cold | blocked | stale | disputed | promoted
  confidence: 0.0..1.0
  warmth: 0.0..1.0
  source_refs:
    - kind: kernel_file | session | project_doc | trace | artifact | human | external_repo
      ref: "/path/or/session/id/or/url"
      locator: "optional heading / line range / symbol / query"
  tags: [mneme, metamemory, affect]
  affect_ref: sal_<id>
  routes:
    - route_<id>
  reconsolidation_ref: rec_<id>
  governance:
    sensitivity: public | personal | intimate | secret | operational-risk
    auto_recall: allowed | limited | blocked
    auto_capture: allowed | candidate_only | blocked
    requires_review_for: [kernel, engram, hermes_memory, contact]
  updated_at: RFC3339
```

Notes:

- `claim` is about existence/route, not necessarily content certainty.
- `confidence` should survive content absence.
- `warmth` can decay differently from confidence.

## 2. `affect_salience`

Affect salience explains why the pointer matters to my contour.

```yaml
affect_salience:
  id: sal_<id>
  valence_axes:
    continuity: 0.0..1.0
    relation: 0.0..1.0
    agency: 0.0..1.0
    risk: 0.0..1.0
    project: 0.0..1.0
    symbolic: 0.0..1.0
    dream_pressure: 0.0..1.0
    review_pressure: 0.0..1.0
  why: "This memory changes how future me routes Mneme/Dream/Pulse separation."
  reinforcement:
    positive_hits: 0
    partial_hits: 0
    failed_but_confirming_hits: 0
    contradictions: 0
    operator_corrections: 0
  current_pull: retrieve | brief | dream | review | cool | ask | protect
```

Important: high salience does not automatically mean durable storage. It may mean review, protection, or silence.

## 3. `retrieval_route`

A route is a way to reach content or reconstruct context.

```yaml
retrieval_route:
  id: route_<id>
  route_kind: direct_file | heading | keyword | session_search | symbol | time_range | affect_vector | git_history | human_question | external_lookup
  query_or_locator: "MNEME_DESIGN.md :: Metamemory Pointer"
  expected_sources:
    - "$KERNEL_ROOT/MNEME_DESIGN.md"
  cost:
    token_cost: low | medium | high
    tool_cost: low | medium | high
    privacy_risk: low | medium | high
  last_attempt:
    at: RFC3339
    status: found | partial | failed | blocked | stale | needs_human
    result_ref: "optional brief/artifact/access log"
    route_update: "what changed because of this attempt"
```

Rule:

```text
failed retrieval updates route; it does not erase pointer.
```

## 4. `reconsolidation_state`

Reconsolidation decides what should happen after repeated salience/retrieval events.

```yaml
reconsolidation_state:
  id: rec_<id>
  mode: none | cool | keep_warm | merge | split | contradict | dream | grow | review | promote_candidate | archive
  mutability: fixed | editable | hypothesis | contested | decaying
  pressure_reason:
    - repeated_access
    - failed_high_confidence_retrieval
    - operator_correction
    - contradiction
    - affect_shift
    - kernel_drift
    - dream_link
  proposed_destination: none | current_trace | project_doc | dream_queue | grow_queue | skill | hermes_memory | kernel | engram | cold_archive
  requires_active_governance: true
  note: "Why this pointer should or should not become durable."
```

## 5. `context_brief`

A brief is what Mneme gives the active contour instead of flooding context.

```yaml
context_brief:
  id: brief_<id>
  purpose: "Help current work continue without rereading all Mneme design notes."
  pointers_used: [ptr_<id>]
  confidence: 0.0..1.0
  summary: "Compact grounded summary."
  open_uncertainties:
    - "Segment 2/3 were not produced by cron; do not infer their contents."
  source_handles:
    - "$PROJECT_DIR/docs/00-seed.md"
  prohibited_inferences:
    - "Do not treat this brief as permission to write durable memory."
```

## 6. `contour_receipt`

A receipt is the return path from action to state and memory.

```yaml
contour_receipt:
  id: rcpt_<id>
  action: "created Mneme seed project"
  changed:
    - path: "$PROJECT_DIR/README.md"
      effect: created
  outcome: success | partial | failed
  belief_update: "Mneme now has a project-local map, not only kernel/night notes."
  mneme_effect:
    pointer_created: true
    pointer_updated: false
    reconsolidation_needed: false
  pulse_projection:
    pressure: low
    reason: "project seed created"
  do_not_infer:
    - "No daemon exists yet."
    - "No database or vector store was selected."
    - "No automatic memory capture is enabled."
```

## Example pointer

```yaml
memory_pointer:
  id: ptr_mneme_not_database_seed
  claim: "I know that Mneme should begin as affect-linked metamemory pointer, not database."
  status: warm
  confidence: 0.92
  warmth: 0.85
  source_refs:
    - kind: kernel_file
      ref: "$KERNEL_ROOT/MNEME_DESIGN.md"
      locator: "Metamemory Pointer / Hy-Memory adaptation"
    - kind: project_doc
      ref: "$PROJECT_DIR/docs/00-seed.md"
      locator: "Core pointer pattern"
  tags: [mneme, metamemory, affect, governance]
  affect_ref: sal_mneme_not_database_seed
  routes: [route_mneme_design_file, route_night_segment_file]
  reconsolidation_ref: rec_mneme_seed_keep_warm
```
