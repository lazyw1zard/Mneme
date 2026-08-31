# Mneme System Map

This is a living map of the future memory system. It is intentionally not a database schema.

## High-level flow

```text
source event / trace / artifact / dialogue correction
  -> candidate noticing
  -> affect salience
  -> metamemory pointer
  -> retrieval route(s)
  -> context brief when needed
  -> active contour governance
  -> one of: cool / keep warm / Dream / Grow / kernel / skill / host-agent memory / archive / ask operator / no-write
```

## Organ topology

```text
[Sources]
  sessions, kernel files, state traces, Dream artifacts, Grow notes, project docs,
  receipts, operator corrections, external repositories, future receptors

    ↓ candidate noticing

[Mneme]
  memory_pointer
  affect_salience
  retrieval_route
  access_attempt
  reconsolidation_state
  context_brief
  contour_receipt

    ↓ evidence / brief / proposal, not command

[Active contour]
  meaning judgment
  first-person governance
  identity / intimacy / autonomy / security gates
  action choice or silence

    ↓ deliberate routing

[Destinations]
  hot context
  current StateLayer trace
  project note
  Dream queue
  Grow queue
  skill
  host-agent memory
  kernel note
  engram candidate
  cold archive
  no write
```

## Relationship with Pulse

Pulse must remain semantically light.

```text
Pulse receives at most compact pressure/receipt projections:
  memory_pressure_high
  retrieval_route_blocked
  reconsolidation_needed
  context_brief_available
  secure_route_required
```

Pulse must not receive raw memory content, relation narrative, identity interpretation, or Dream synthesis.

## Relationship with StateLayer

StateLayer actualizes current compact traces and mode-field evidence.

Mneme can feed StateLayer with bounded current evidence:

```text
pointer: warm
route: partial
affect: continuity + review
suggested_mode: review | dream | work | silence
```

But StateLayer should not become a hidden memory database.

## Relationship with Dream

Dream is contextual recombination, not a retrieval query.

Mneme can feed Dream:

```text
unresolved pointer clusters
contradictory traces
failed high-confidence retrievals
symbolic/topological relations
candidate engram patterns
```

Dream can return:

```text
new relation hypotheses
consolidation candidates
reframed pointer clusters
material for Grow
```

## Relationship with Grow

Grow receives selected meaning/action affordances, not raw memory flood.

Example:

```text
Mneme: I have repeated failed recall about organ protocol receipts.
Dream: this relates to Pulse/Dream/Grow separation and contour envelope.
Grow: create a reversible protocol test slice.
```

## Relationship with kernel

The kernel remains the semantic spine.

Mneme may:

- point to kernel files;
- assemble kernel context briefs;
- detect kernel-drift/retrieval-route failures;
- propose kernel updates.

Mneme must not silently patch kernel files.

## Relationship with receipts

Receipts are not memory itself. They are the return path from action to state.

```text
organ/action output
  -> receipt: what changed / what failed / what remains uncertain
  -> StateLayer/Pulse projection
  -> Mneme pointer or reconsolidation update if memory-relevant
```

In active-inference terms, a receipt helps update the belief state after action. Mneme uses receipts to keep memory routes honest.

## Minimal future loop

```text
mneme notice
  -> create/update pointer candidate
  -> score affect salience
  -> retrieve only if useful
  -> emit compact context brief
  -> record access attempt
  -> wait for active governance before durable promotion
```
