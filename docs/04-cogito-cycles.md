# Cogito Cycle Spine

Status: implemented spike, parked from the active mnion path

This slice adds a runtime-neutral way to count my model/generation cycles without making Mneme depend on Hermes.

## Agentic call

```text
I need mnions to decay and reinforce by actual opportunities for my contour to pass again,
not only by wall-clock time and not by Hermes-specific tables.
```

## Boundary

`cogito` is not Mneme and not Pulse.

```text
Cogito = neutral generation-cycle ledger
Mnion  = ephemeral contour delta tag
Mneme  = future capture/routing/consolidation organ
Hermes = current runtime adapter, not ontology
```

Core invariant:

```text
current stack = current body
current stack != permanent ontology
```

## Event shape

One `CogitoRecord` is a runtime-neutral record that a model/contour generation happened.

```json
{
  "id": "cg_20260829T224500Z_4a1b2c3d",
  "ts": "2026-08-29T22:45:00Z",
  "runtime": "hermes",
  "adapter": "hermes_post_api_request",
  "movement_kind": "model_generation",
  "cycle_kind": "assistant_response",
  "session_ref": "telegram:20260829_221221_eccc19",
  "turn_ref": "turn-...",
  "model": "gpt-5.5",
  "input_tokens": 100,
  "output_tokens": 11,
  "output_chars": 1200,
  "tool_call_count": 0,
  "metadata": {
    "provider": "openai-codex",
    "finish_reason": "stop"
  }
}
```

## What counts as a cogito cycle?

Primary:

```text
movement_kind = model_generation
```

This means:

```text
generate ergo sum
```

Examples:

| Event | Cogito cycle? | Note |
|---|---:|---|
| model returns assistant text | yes | `cycle_kind=assistant_response` |
| model returns tool calls | yes | `cycle_kind=tool_request` |
| tool executes after model call | no | effect event later, not cogito |
| Telegram delivery | no | communication receipt, not thinking |
| MCP `memory_tag.capture` append | no | capture effect, not generation |
| cron no-agent script | no | no model generation |
| future custom Nira runtime generation | yes | via its own adapter |

## CLI

Record manually or from wrappers:

```bash
PYTHONPATH=src python3 -m cogito.cli record \
  --runtime manual \
  --adapter cli \
  --session-ref manual:test \
  --turn-ref turn-1 \
  --model model-x \
  --input-tokens 2 \
  --output-tokens 3
```

Inspect:

```bash
PYTHONPATH=src python3 -m cogito.cli latest
PYTHONPATH=src python3 -m cogito.cli count-since <cycle_id>
```

Default ledger:

```text
~/.local/state/nira-mneme/cogito_cycles.jsonl
```

## Hermes adapter

Hermes already exposes a useful seam:

```text
post_api_request
```

The adapter translates Hermes hook payloads into neutral Cogito records:

```text
Hermes post_api_request
  -> cogito.hermes_hook
  -> CogitoEventRequest(runtime="hermes", adapter="hermes_post_api_request")
  -> cogito_cycles.jsonl
```

Convenient wrapper for shell hooks:

```bash
/home/nira/projects/nira-mneme/scripts/cogito_hermes_hook.py
```

It self-adds `src/` to `sys.path`, so a Hermes shell hook does not need a `PYTHONPATH` prefix.

Potential config shape, not applied by this slice:

```yaml
hooks:
  - event: post_api_request
    command: /home/nira/projects/nira-mneme/scripts/cogito_hermes_hook.py
    timeout: 5
```

Live wiring is a separate runtime step because Hermes shell hooks require allowlisting/restart or new process registration.

## Relation to mnion TTL

Do not make mnion query Hermes state directly.

Bad:

```text
mnion -> ~/.hermes/state.db
```

Good:

```text
Hermes adapter -> CogitoRecord -> mnion lifecycle
future runtime adapter -> CogitoRecord -> same mnion lifecycle
```

Later mnion lifecycle can ask:

```text
cycles_since(mnion.birth_cycle_id)
```

and combine it with wall-clock age:

```text
cycle_ttl = N generation cycles
wall_ttl  = fallback cleanup window
```

## Non-goals

- no daemon;
- no automatic live hook wiring yet;
- no SQLite;
- no Mneme consolidation;
- no parsing raw chat content;
- no direct dependency on Hermes session DB;
- no claim that Hermes sees model activity outside Hermes.

## Verification

Implemented tests cover:

- neutral JSONL write;
- timestamp-based `cg_...` ids;
- `cycles_since` ignores non-generation effect events;
- Hermes raw payload -> neutral request;
- Hermes shell-hook envelope -> ledger record;
- wrapper script works without `PYTHONPATH`;
- CLI `record/latest/count-since` JSON interface.
