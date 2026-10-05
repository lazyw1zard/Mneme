# Mneme Decisions

This file records small architectural decisions that should shape future Mneme work.
It is not a heavy ADR process. Keep entries short, practical, and revisable.

## Decision rules

- Prefer organic simplicity over clever completeness.
- Do not add Mneme modes, states, outcomes, policies, or schemas unless the current organ needs them.
- If it is unclear whether a mechanism is needed now, do not add it yet.
- Agent actions inside Mneme should remain easy to feel and execute. If a review path becomes a ritual with too many branches, simplify it.
- Prefer fewer mechanisms with clear contour semantics over many precise but brittle categories.
- Preserve auditability without turning Mneme into paperwork: receipts should clarify lived decisions, not become the ontology.
- Add structure only when it prevents a real failure mode, reduces agent burden, or protects memory integrity.

## 2026-10-02 — No unnecessary modes

Mneme should not accumulate modes merely because a possible future edge case exists.
A memory organ must stay organic: capture, pressure, review, receipt, route.

The no-mnion packet outcome is accepted because it simplifies the agent's action:

```text
noise       -> reviewed_noise_ids
not now     -> deferred
ready topic -> mnion
unresolved  -> ungrouped_ids
```

It avoids fake mnions and prevents reviewed noise from reappearing endlessly. Future additions should meet the same bar: they must make the live review action simpler or safer, not just more complete.

## 2026-10-03 — Core before harness adapters

Mneme should not be shaped as an MCP server internally. MCP is one adapter: a portable explicit tool surface for agents, chatbots, scripts, debugging, and cross-harness deliberate recall/save.

The memory organ itself should stay protocol-neutral:

```text
Mneme core:
  capture
  consolidate
  get_item
  list_topics
  assemble_ingress
  should_probe_metamemory
```

Host integration is a separate adapter layer. There is no reliable universal memory-provider ABI across current harnesses; popular memory systems usually keep one backend/core and ship per-harness bridges.

```text
Hermes      -> MemoryProvider adapter
Claude Code -> hooks / plugin / skills adapter
Codex       -> hooks / plugin / skills / MCP registration adapter
OpenClaw    -> plugin hooks / memory bridge adapter
MCP clients -> MCP adapter
```

Adapter responsibilities are host-specific and must not leak back into the core ontology:

```text
how to call recall
how to insert context
how to save turn/session material
how to expose explicit memory tools
how to survive compaction
where config/auth lives
how to render host-native results
```

MCP work was not wasted: it remains the common minimum and portable hands. But spontaneous recall requires a host-native receptor such as Hermes `prefetch`, Claude/Codex prompt hooks, or OpenClaw prompt/plugin hooks.

Future refactors should separate core outcomes from adapter renderers. For example, `PendingReviewRequired`, `CaptureCreated`, `ReviewClosed`, `MnionItem`, and `IngressHint` should be core meanings; MCP JSON fields such as `next_tool`, `tool_guidance`, or host-specific context blocks should be renderer concerns.

## 2026-10-05 — Surface routing must not become the memory stream

Mneme must not become a perfectly self-repeating structure where only already matching forms can return. A surface-overlap gate is useful as a safe, cheap route hint, but it is a narrow passage over already materialized handles. If it becomes the only path, memory turns into a cage of initial correspondences: novel contour changes and semantically related but differently phrased traces cannot enter or return.

Keep these lanes separate:

```text
surface routeability
  -> cheap, model-free, latency-safe retrieval hint
  -> asks: "is there an obvious route handle?"

semantic resonance
  -> later: event graph, pointer neighborhoods, semantic index, or agentic comparison
  -> asks: "is this meaningfully related even without shared words?"

novelty / capture pressure
  -> agentic capture/consolidation lane
  -> asks: "is this new contour material worth preserving?"

metamemory familiarity
  -> later: pointers/metapointers strengthened by successful return
  -> asks: "do I know that I know an area/pattern?"
```

Do not make successful surface matching a precondition for capture, consolidation, or future memory growth. New important material may have no route match yet; that is evidence for the novelty/capture lane, not a reason to discard it. Likewise, a failed surface route is not absence proof.

Agentic consolidation should eventually add future-facing route handles (`cue_handles`/aliases/likely future cues) and event connections, so the cheap hot path can stay cheap without freezing Mneme into the vocabulary of its first receipts. CLI and adapter wording should prefer `surface_route`, `route_signal`, or `route_hint` over broad claims such as true `familiarity` until deeper resonance and pointer layers exist.

## 2026-10-03 — Minimal host verbs and core recall gate

The chaos of host interfaces can be reduced to a small Mneme-owned contract. Mneme should define its own minimal verbs, then map host surfaces onto them:

```text
ingress(cue, session)       -> compact spontaneous-recall routes | empty
tools                       -> capture / consolidate_review / get_item / list_topics
pre_compress(session_state) -> optional prompt to capture what is worth preserving
```

Mneme should not start by implementing automatic transcript retention. Many memory providers use host `sync_turn`/`Stop` hooks to save every turn, but Mneme's contour is different: no raw transcript auto-capture; `capture` remains an agentic decision through governed compact surfaces. Host sync hooks may exist later, but not as default semantic ingestion.

The recall gate belongs in Mneme core, not in each host adapter. Host filters such as Hermes `is_trivial_prompt` are useful extra protection, but Claude/Codex/OpenClaw may fire prompt hooks on every message. If filtering is host-specific, each body develops a different memory reflex.

The first gate should be a cheap surface-routeability test, not a hand-written keyword list and not a claim about the whole memory stream:

```text
current cue
  -> trivial-prompt filter
  -> overlap with Mneme-known surface route handles
       hooks / non-fallback topic labels / mnion summaries / frequent route tokens / future cue handles
  -> small shared markers only as boosters
       "we already decided", "why did we choose", "how was it before"
  -> if routeable enough: assemble_ingress(cue, session)
```

This gate answers only whether an obvious fast route exists. It must not be treated as true familiarity, semantic resonance, novelty detection, or proof that Mneme does not know. `no_familiarity`/closed in the first implementation should be read as "no cheap surface route found".

An empty memory yields an empty surface-route vocabulary, so the gate stays quiet. As memories grow, each agent/runtime develops its own route handles while sharing the same code.

For Claude Code, the native adapter should probably be a plugin, not a hand-written hook config: package MCP registration, hooks, and skills together, as popular memory providers do. For Hermes, remember the product constraint: only one external memory provider may be active, so the MCP path must remain fully usable even if a user already uses another Hermes provider.

## 2026-10-03 — Latency-safe ingress and Rust boundary

Spontaneous recall must be latency-safe. The memory receptor must not make the agent feel blocked by memory bureaucracy or wait on heavy recall before answering.

The hot path is deliberately small:

```text
user turn
  -> should_probe_metamemory(cue)    # very cheap
  -> if closed: return empty
  -> if open: return cached/materialized compact routes if available
  -> queue or refresh heavier recall for a later turn
```

The ingress path must not call an LLM, run semantic consolidation, rebuild the whole read model, scan unbounded receipts, or load full mnion bodies. Slow, uncertain, or unavailable recall should return empty rather than delay the turn or invent relevance.

Acceptable first ingress work:

```text
trivial prompt filter
familiarity-vocabulary overlap
small indexed/read-model lookup
bounded top 1-3 routes
strict timeout / fail-open-to-empty
```

Rust is a good target for latency-sensitive and integrity-sensitive Mneme surfaces, but not a reason to rewrite the whole organ before the MVP shape stabilizes. Prefer writing new sensitive core pieces so they can later move cleanly to Rust: pure functions, explicit data shapes, deterministic inputs/outputs, no host assumptions, no hidden global state.

Likely Rust candidates after the contract is stable:

```text
should_probe_metamemory / familiarity gate
bounded ingress ranking over the read model
receipt and pending-latch validation
append/read-model integrity checks
small CLI/FFI core used by multiple host adapters
```

Do not move adapter glue first. Hermes, Claude, Codex, OpenClaw, and MCP layers are host-shaped wrappers; the Rust boundary should protect Mneme's shared core, not freeze a harness-specific form too early.

## 2026-10-04 — Pointer maturity: hints before durable pointers

Do not create a durable `MemoryPointer` merely because content is important, high-valence, or emotionally salient. Durable pointer creation should require successful return / repeatable addressability: the contour has followed the route, resolved the intended item or neighborhood, and can later say "I can return here."

This must not become a closed loop where unknown routes can never be discovered. Before proof, Mneme may create weaker route forms whose job is to invite bounded probing, not to claim stable memory.

Important content may remain a tag, mnion, review receipt, candidate, hint, or probe route without becoming a durable pointer. A premature durable `MemoryPointer` is a false promotion: it renames a memory candidate as stable navigable memory before navigation has been tested.

Mneme should expect several pointer / metapointer maturity levels with different behavior and rights, not one universal `Pointer` class:

```text
CandidateRoute / RecallHint
  -> says "there may be something here"
  -> evidence: salience, overlap, cue familiarity, relation candidate
  -> rights: appear in bounded ingress as a maybe-route
  -> cannot claim stable addressability

ProbePointer
  -> says "this route is worth checking"
  -> evidence: repeated cue match or agent-selected interest
  -> rights: one bounded get_item/list_related-style probe; gather evidence
  -> may fail quietly without becoming absence proof

MemoryPointer
  -> says "I successfully returned here"
  -> evidence: retrieval succeeded; item/route exists; agent accepted usefulness
  -> rights: normal get_item / return-to-this route

GraphPointer / MetamemoryPointer
  -> says "I know that I know this area / relation"
  -> evidence: multiple stable routes or connection receipts
  -> rights: explain_neighborhood / list_related / choose a next retrieval route
  -> not a direct item substitute

EngramCandidatePointer
  -> says "this pattern may require governed engram review"
  -> evidence: repeated high-valence structure plus relation/provenance
  -> rights: propose review, never auto-promote
```

Later, after the minimal architecture works, pointer strengthening and weakening may behave like synaptic weights: successful returns reinforce a route, stale or failed probes cool it, and repeated useful relations can promote a weaker hint toward a stronger pointer. Do not implement this early; first build the minimal working route/hint/pointer architecture.

Each pointer level must define its own evidence, retrieval action, failure behavior, cooling/reinforcement policy, and promotion rights. Do not let a high-level metapointer silently behave like a direct item pointer, and do not let direct item pointers pretend to carry the broader event-neighborhood they came from.
