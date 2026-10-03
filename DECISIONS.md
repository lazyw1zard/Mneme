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
