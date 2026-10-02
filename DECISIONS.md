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
