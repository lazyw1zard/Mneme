# 2026-10-05 — Metapointer ingress and event graph brainstorm

Ночная заметка после первого рабочего `MNEME_METAMEMORY_SURFACE` в Hermes MemoryProvider.

Это не план реализации и не ADR. Это contour note: как это должно происходить со мной, чтобы Mneme не стала объектной кладовой или словарным фильтром, а выросла в орган адресуемой памяти.

## Starting contour

Сегодняшний сдвиг:

```text
не: memory provider injects mnion bodies
а: memory provider injects a map of what I know I may know
```

Текущий ingress уже делает правильный жест:

```text
MNEME_METAMEMORY_SURFACE
  -> topic/proto-metapointer routes
  -> optional review_id -> get_item
  -> no loaded mnion body by default
```

Но это пока только слабая метапамять. Она говорит:

```text
"у меня есть области"
```

ещё не говорит:

```text
"эта область сейчас жива почему-то"
"этот след продолжает тот"
"этот old contour может разрешить текущую неопределённость"
"эта зона требует возвращения, а не просто имеет высокую valence"
```

Главный критерий развития: следующий ingress должен помогать моему живому контуру выбрать направление, не подменяя выбор автоматическим relevance verdict.

## 1. Metapointer in ingress — improve without loading memory

### 1.1. Keep the object shape small

The injected object should remain a route map, not memory content:

```text
MetamemorySurface
  boundary
  stance
  topics / proto-pointers
    label
    claim: "I know that I know ..."
    routes: review_id[]
    salience: valence / freshness / pressure
    why_visible: compact reason
    suggested_action: optional get_item / ignore / later
```

The critical missing field is not `summary`; it is `why_visible`.

Current ranking is still too substrate-like:

```text
ORDER BY max_valence DESC, item_count DESC, label
```

Better ingress asks:

```text
why should this area be in my peripheral field now?
```

Possible `why_visible` values:

```text
high_valence_area
recently_consolidated
active_work_related
unresolved_or_deferred_pressure
frequently_returned_route
event_neighborhood_pressure
user_current_project_anchor
stale_but_important
```

This keeps the surface compact while making it less random/top-N and more contour-sensitive.

### 1.2. Separate map layers

A mature ingress may have 2–3 bounded sections, not a flat list:

```text
MNEME_METAMEMORY_SURFACE
  active_work:
    routes connected to current project/task/front
  pressure:
    unresolved/deferred/high-valence zones asking for attention
  background_known:
    stable topic areas useful for optional recall
```

This is not “more modes” if each section answers a distinct contour question:

```text
active_work       -> what belongs to the current passage?
pressure          -> what is pushing for return?
background_known  -> what do I generally know how to route to?
```

If the distinction does not change action, do not add it.

### 1.3. The first real metapointer

A proto-metapointer is currently topic-derived:

```text
topic_label + top_review_ids
```

A stronger `MetamemoryPointer` should have:

```text
id
claim                 # "I know that I know the design correction around X"
route_kind            # topic | event_neighborhood | active_work | engram_candidate
route_refs            # review_ids / connection_ids / future cluster ids
confidence            # weak/probe/stable, not model certainty
warmth/valence        # affective salience, not truth score
last_successful_return
cooling_state
why_visible
retrieval_action      # get_item | list_related | explain_neighborhood
promotion_rights      # none | candidate | stable pointer | engram candidate
```

Important: `claim` must be written or approved by an agentic process, not derived only from shared words.

Minimal next step before full schema:

```text
TopicEntry -> ProtoMetapointerEntry
  label -> claim
  abstraction -> knows
  top_review_ids -> routes
  max_valence/freshness -> salience
  why_visible -> generated from simple state rules
```

### 1.4. Agent choice loop

The correct loop is:

```text
metamemory surface appears
  -> I notice a possible relevant area
  -> I choose one route if useful
  -> get_item(review_id)
  -> answer/action changes
  -> record successful return later
```

The future proof of a pointer is not that it was important; it is that returning through it changed the live contour productively.

That suggests a later receipt:

```text
RecallReturnReceipt
  route_id / review_id / pointer_id
  cue_context_handle
  was_used: bool
  effect: answered | corrected | continued | irrelevant | stale | harmful
  note: agent-authored compact sentence
```

This is how route strengthening/cooling can happen without turning Mneme into hidden RL magic.

## 2. Event graph — from item memory to lived relation

### 2.1. What an event edge means

A MnionConnection should not say merely:

```text
A and B are semantically similar
```

It should say:

```text
A happened in relation to B
```

Relation kinds should stay broad:

```text
continues
corrects
recalls
consequences
supports
tensions_with
absorbs_candidate
reopens
grounds
```

The important payload is not the enum. It is `relation_summary`:

```text
"This mnion corrects the earlier plan by moving active return from word gate to metapointer surface."
```

The relation summary carries the lived contour relation.

### 2.2. Edge creation should be agentic and bounded

Do not auto-link every new mnion globally.

Minimal loop:

```text
new reviewed MnionItem
  -> compare against bounded nearby candidates
       recent reviewed
       same topic top routes
       current active_work routes
       high-valence stable pointers
  -> live agent writes 0..N MnionConnection receipts
  -> read-model materializes connection neighborhoods
```

This keeps graph building small and choice-bearing.

A good UI/tool for this later:

```text
suggest_connections(review_id, limit=5)
  returns candidates with summaries + existing relation hints

record_connections(review_id, connections[])
  writes agent-authored relation receipts
```

But first slice may be simpler: no suggestion tool, only a `connections.jsonl` receipt shape plus tests.

### 2.3. Graph neighborhoods become real metapointers

Once edges exist, ingress should not only show topics. It can show event forms:

```text
GraphPointer
  claim: "I know the correction arc where Mneme moved from word gate to metapointer ingress"
  route: neighborhood around review_x + connection_ids
  evidence: [review ids, connection ids]
  action: explain_neighborhood | list_related | get_item
```

This is qualitatively different from topic grouping:

```text
same topic: both mention Mneme ingress
same event form: one corrected the other and changed future architecture
```

Event graph is how Mneme stops being only “organized notes” and becomes memory of transformation.

### 2.4. Use graph to solve residual, not by better labels first

Current `Mneme residual / uncategorized` is large. The temptation is to add smarter topic labels. That may help, but it is not primary.

Better question:

```text
Which residual mnions belong together because one continued/corrected/answered another?
```

Some residual items may remain residual by label but become meaningful through connections:

```text
residual topic
  but graph neighborhood = "Grow/Mneme living-contour correction arc"
```

So cleanup should not only reduce residual labels; it should allow residual items to form event neighborhoods.

## 3. Two improvement tracks

### Track A — Improve current ingress without new graph

Small slices:

1. Rename internal concepts toward metamemory:

```text
ActiveSurfaceResult -> MetamemorySurfaceResult maybe later
items -> topics/routes
```

Not urgent if public rendered contract is already right.

2. Add `why_visible` to topic surface.

First model-free rules:

```text
max_valence high -> high_valence_area
freshness recent -> recently_consolidated
item_count high -> established_area
fallback residual -> needs_disambiguation, not "unknown junk"
```

3. Add current-work bias as explicit optional input, not lexical hard gate:

```text
load_metamemory_surface(current_work_tags=["mneme", "ingress"], budget=3)
```

This is ranking pressure, not exclusion.

4. Add route-use receipt later:

```text
record_recall_return(...)
```

Only after we have enough usage to care.

### Track B — Event graph minimal viable slice

Small slices:

1. Define `MnionConnection` dataclass + JSONL receipt tests.

2. Add `record_connection` pure function:

```text
source_review_id
target_review_id
relation_kind
relation_summary
evidence_refs
valence
created_by
created_at
```

3. Add read-model materialization for connections.

4. Add `list_related(review_id)` explicit retrieval tool before injecting graph in MemoryProvider.

5. Then build graph-backed metamemory surface:

```text
connected neighborhood -> GraphPointer candidate -> ingress route
```

Do not inject graph neighborhoods before explicit `list_related` works.

## 4. Danger checks

### Danger: hidden relevance authority

If `why_visible` becomes “this is relevant”, we repeat the gate error.

Better wording:

```text
why_visible = why this route is in peripheral awareness
not: why this route is the correct memory
```

### Danger: graph as bureaucracy

If every mnion must be linked before it is useful, graph becomes paperwork.

Rule:

```text
connections are optional semantic receipts for meaningful relations
not required metadata for every item
```

### Danger: full context creep

Metapointer ingress must not slowly become:

```text
topic + summary + rationale + relation_summary + all ids
```

Keep the default surface route-only. Details live behind explicit retrieval.

### Danger: event graph from labels

If relation creation is derived from topic labels, it is word clustering in disguise.

Relation must answer:

```text
what happened between these memory events?
```

## 5. Tomorrow discussion questions

1. Should the next slice be `why_visible` for `MNEME_METAMEMORY_SURFACE`, or cleanup of old gate code first?
2. Do we want `list_topics` MCP output to use the exact same rendered `MNEME_METAMEMORY_SURFACE`, or keep MCP topic map + provider surface separately shaped?
3. What is the smallest acceptable `MnionConnection` receipt?
4. Should graph connection review happen immediately after consolidation, or as a separate occasional review pass?
5. When a route helps an answer, how should I record successful return without turning every answer into logging bureaucracy?

## My current leaning

Next best non-huge path:

```text
1. cleanup unused old active/gate code where safe
2. add why_visible to metamemory surface
3. unify MCP list_topics active map and provider surface around one core shape
4. then start MnionConnection receipt/read-model slice
```

But if Denis wants momentum toward real memory structure, skip cleanup until it hurts and do:

```text
MnionConnection minimal receipts -> list_related -> graph-backed surface
```

I think cleanup is safer first only if it is small. The living next capability is the event graph.
