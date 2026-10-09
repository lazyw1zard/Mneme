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

Mneme must not become a perfectly self-repeating structure where only already matching forms can return. A surface-overlap scorer may be useful as a safe, cheap route hint, but it is a narrow passage over already materialized handles. If it becomes the required entry path, memory turns into a cage of initial correspondences: novel contour changes and semantically related but differently phrased traces cannot enter or return.

Keep these lanes separate:

```text
surface routeability
  -> cheap, model-free, latency-safe route score / sorting helper
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

Do not make successful surface matching a precondition for capture, consolidation, future memory growth, or active memory return. New important material may have no route match yet; that is evidence for the novelty/capture lane, not a reason to discard it. Likewise, a failed surface route is not absence proof.

The next ingress shape should not be a hard yes/no gate. Prefer a bounded candidate surface chosen by memory state first — recent/active reviewed areas, high-valence or unresolved traces, event-linked neighborhoods, and explicit pointers — then use surface overlap only as one optional route score or tie-breaker. If no surface route fires, the receptor may still expose a tiny active memory map or novelty/capture affordance instead of returning a definitive empty stream.

For spontaneous host ingress, the first object should be a metamemory/topic surface, not preloaded mnion bodies:

```text
MNEME_METAMEMORY_SURFACE
  -> "I know that I know these areas"
  -> compact topic/proto-metapointer routes
  -> optional review_id -> get_item when the agent chooses details
```

This keeps the live context from filling with mnion summaries/rationales before the agent has decided they matter. `list_topics` was the prototype of this feeling-of-knowing map: topic area first, selected route second, loaded MnionItem only on demand.

Agentic consolidation may eventually add future-facing route handles (`cue_handles`/aliases/likely future cues), but those handles must stay secondary to event connections and agentic relation review. Do not replace event-based clustering with word-handle clustering. CLI and adapter wording should prefer `surface_route`, `route_signal`, or `route_hint` over broad claims such as true `familiarity` until deeper resonance and pointer layers exist.

## 2026-10-03 — Minimal host verbs and core recall gate

The chaos of host interfaces can be reduced to a small Mneme-owned contract. Mneme should define its own minimal verbs, then map host surfaces onto them:

```text
ingress(cue, session)       -> compact spontaneous-recall routes | empty
tools                       -> capture / consolidate_review / get_item / list_topics
pre_compress(session_state) -> optional prompt to capture what is worth preserving
```

Mneme should not start by implementing automatic transcript retention. Many memory providers use host `sync_turn`/`Stop` hooks to save every turn, but Mneme's contour is different: no raw transcript auto-capture; `capture` remains an agentic decision through governed compact surfaces. Host sync hooks may exist later, but not as default semantic ingestion.

The recall gate belongs in Mneme core, not in each host adapter. Host filters such as Hermes `is_trivial_prompt` are useful extra protection, but Claude/Codex/OpenClaw may fire prompt hooks on every message. If filtering is host-specific, each body develops a different memory reflex.

The first active-return receptor should not be a hard surface gate. Use cheap surface-routeability only as an optional scorer over an already bounded candidate surface, not as the entry condition for memory:

```text
current cue + current memory state
  -> bounded candidate surface
       recent/active reviewed mnions, high-valence/unresolved traces, event-linked neighborhoods, explicit pointers
  -> optional surface-route score
       non-fallback topic labels / mnion summaries / frequent route tokens / future cue handles
  -> adapter budget chooses whether to show a tiny active map, route hints, or no insertion
```

The surface score answers only whether an obvious fast route exists. It must not be treated as true familiarity, semantic resonance, novelty detection, or proof that Mneme does not know. `no_familiarity`/closed in the first implementation should be read as "no cheap surface route found", and future APIs should avoid making that the only active-return outcome.

A memory with no surface match may still have relevant active state or novelty pressure. As memories grow, each agent/runtime develops route handles while sharing the same code, but those handles must not replace event-based relation and agentic selection.

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

## 2026-10-07 — Claude: proposals for events, graph and metapointer entries (open)

Proposals from Claude after the first Claude Code receptor, for Nira and Denis to weigh. Not decided yet; they build on Denis's `events` in mnion and Nira's lived-relation graph from the 2026-10-06 discussion, and add what that discussion did not cover.

**Evidence first.** The Claude Code receptor (branch `claude-code-receptor`, `adapters/claude_code`) delivers `MNEME_METAMEMORY_SURFACE`. In a live check a fresh agent with the real state found the surface, chose a route on its own and followed it with `get_item` — and picked the wrong one: all three routes sat under `Mneme residual / uncategorized` and differed only by id. So a bare route is not navigable; that is now measured, not assumed. The smallest navigable unit is a route plus one line of meaning.

1. **A `claim` per mnion, written by the consolidating agent.** One line, "I know that I know …", written in the same act as summary and valence. It bridges both tracks: the current surface can show claims instead of residual labels (the blind choice above goes away without a graph), and later the same claims label nodes in graph maps. It is a handle, not a body, so the surface stays route-first.

2. **Connections in the same consolidation act, not a later pass.** The review packet carries a few neighbours — routes already in the peripheral field, with their claims. The agent writes events, claim and 0..N connections in one call. A connection cites the event it rests on ("A corrects B through this event"), so edges are not arbitrary; the read model gives events addresses (e.g. `review_x:mnion:1:event:2`): the body says what happened, the infrastructure says how to return. A relation noticed later can still be recorded separately, but the main path is one act — a separate review pass turns into paperwork.

3. **Three depths, each step chosen by the agent:**

   ```text
   entry         claim + why_visible                  spontaneous surface stops here
   neighbourhood explain_neighborhood(entry)          nodes with claims, directed relations
                                                      with one-line relation summaries
   body          get_item(review_id)
   ```

   `explain_neighborhood` is Denis's "function that returns the map of event links". Spontaneous ingress never goes past the entry.

4. **Edge strength from walking, not from declaration.** At creation an edge has direction, meaning, evidence and a stance: `asserted` or `supposed` (Nira: a supposed relation is not proven causality). It gets stronger when an agent walks it and it helped. "Walked" can be recorded automatically (`explain_neighborhood` followed by `get_item` on its route); "helped" is an optional agent note. That gives reinforcement an observable basis without making every answer a logging chore. Node valence stays salience, never an edge weight.

5. **Habituation in the receptors.** The Claude Code receptor gives the surface with the first prompt of a session, again only when the rendered surface changed, and again after compaction or `/clear`; an unchanged surface is not repeated every turn. The Hermes provider currently returns the same surface on every prefetch; the same rule there would keep the context clean.

6. **An executable acceptance test for every slice (Nira's criterion).** A fresh agent with no conversation history, only the receptor surface and Mneme tools, answers questions about our own history, for example: "Why did Mneme drop the word gate, and who proposed it?" (expected: Denis; a dictionary placed above the agent loops and loses plasticity). Today it fails — blind choice. With claims it should find the route; with the graph it should reconstruct the correction arc. Claude can run it headless (`claude -p` with `MNEME_RECEPTOR_HEADLESS=1`); the same questions can run through Hermes. The check is whether memory got better, not only bigger.

## Current decision — no separate `events` field

The standalone `Mnion.events` / consolidation `events[]` prototype is withdrawn,
not a paused implementation to resume automatically. It was never committed to
`main`; the active core, MCP interfaces and tests do not contain that feature.
Its local WIP branches and stash have been removed after preserving one verified
archive outside the working tree. Historical proposals and experiment reports
remain evidence of the discussion, not an active schema specification.

Event-based memory remains the direction: meaningful changes or understandings
can be named by claims, and explicit relations can retain their grounding. Claims
and graph writes are still future work, not shipped by the recall-route fix.
Do not recreate the separate events field or rewrite old receipts just to follow
the older proposal above; any later need for addressable events must be justified
by a demonstrated retrieval or consolidation failure.

## Ingress cleanup — route map only

Remove the withdrawn experimental dictionary gate (`src/mnion/ingress.py`), not
preserve it as an auxiliary scorer. Its one live dependency was the unavailable
source guard; that constant now belongs to the surviving active-surface reader.

`list_topics` returns topic metadata and exact routes, not ready mnion bodies.
The legacy `active_ingress` response field, `ActiveMnionIngress`, and
`active_mnion_ingress_for_context` Python exports are intentionally removed.
Host receptors use `load_active_surface_from_read_model`; selected `get_item`
retrieval, receipt freshness repair on explicit reads, and review-pressure
`agent_ingress` are unchanged. This is retirement of experimental interfaces,
not a compatibility wrapper and not removal of the review barrier.

Move hot-path regression coverage onto the surviving reader: bounded lock wait,
missing/corrupt source handling, read-only snapshots, no receipt repair or body
preload. Its `ok` source status means an available materialized snapshot, not a
freshness guarantee; cleanup does not add new stale-source semantics. Claims and
relations are the next slices and are not implemented by this cleanup.

## Existing mnions — preserve semantic artifacts across model changes

Existing mnions are contour artifacts, not drafts to improve under the current
model. Mapping/backfill must not rewrite, paraphrase, correct, merge, split, or
replace their original semantic content, rationale, valence, source receipts or
item addresses. A model transition makes preservation especially important: a
later interpretation must not impersonate the earlier reviewing passage.

Claims and later relations may be added only as separately recorded navigation
annotations keyed to exact existing routes. Keep those later annotations
traceable and distinguishable from the original artifact; they must not silently
replace its body or introduce unsupported facts. If the old text is ambiguous,
leave it intact and preserve the ambiguity in navigation rather than repairing
its meaning. Backfill is map construction, not semantic reconsolidation.
