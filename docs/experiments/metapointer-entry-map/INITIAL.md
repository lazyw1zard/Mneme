# Entry-map exploratory probe — initial observations

Status: executable exploration of the existing graph, **not an implemented or
model-evaluated metapointer**. Entry labels are hand-authored neutral test sketches.
No production Python changed, no live captures/config/ingress writes occurred.

Continuation: [selected walk](WALK.md) adds a tested experimental expand/select
seam and a parent-chosen real-corpus MCP walk on disposable copied state. It does
not change these initial observations or establish automated recognition.

## Reproduction

From the project, with disposable HOME/XDG/MNEME_STATE_DIR/MNEME_CONFIG:

```sh
uv run --with pytest pytest tests/test_metapointer_entry_map_probe.py -q -s
```

The local verified run used an outside-repo isolation runner with source byte
hash guards: **4 passed** and `live_bytes_unchanged=True`.

## Observations

- A compact entry can be represented without node bodies or automatic expansion.
  This fixture fact does not prove learned recognition, automatic entrance
  construction or effective live agent selection.
- Explicit existing `get_neighborhood` expansion preserves two independently
  authored branches and returns route/claim nodes plus relations, not original
  bodies or a unified story. Source receipts remain byte-identical.
- Adding a continuation to one branch makes the new route reachable at depth 2
  from the same root. The compact entry itself was unchanged: structural expansion
  and semantic entrance revision need not be the same operation.
- **A single new `corrects` link can be omitted by the current oldest-first edge
  order at a small connection budget.** `has_more=true` reports truncation, but
  does not tell the agent that the omitted link is a correction. A larger explicit
  budget or the correcting node's exact route returns it. Neither alternative
  demonstrates that an uninformed agent would choose that path.

## Consequence for the next prototype

A freshness marker or change count alone is not a semantic completeness guarantee.
Do not simply replace traversal with newest-first or always-prioritize-corrections:
that policy could instead hide origins, branch grounds, or falsely privilege an
unverified authored correction. Compare choices on explicit scenarios before
choosing a new bounded traversal contract. No change to live traversal is made by
this probe; the observed limitation is not a declared specification bug.

The accepted target remains: a recognizable map entrance -> selected tracing ->
selected original access, not narrative synthesis, a replacement giant mnion,
automatic event grouping, or compulsory engram promotion.
