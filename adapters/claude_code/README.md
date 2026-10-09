# Mneme receptor for Claude Code

A Claude Code plugin (a mod: JavaScript hooks that run inside Claude Code) that puts the agent's
metamemory surface beside its prompt. Mneme core renders the surface (`MNEME_METAMEMORY_SURFACE`):
a route map — "I know that I know these areas", with `review_id` routes — not loaded memory.
The agent follows a route itself with the MCP tool `mcp__mneme__get_item` when it chooses to.

The Hermes counterpart is `adapters/hermes_memory_provider/` (`MemoryProvider.prefetch`).

## When the surface comes

- with the first prompt of a session;
- again when memory changed: the read model was rebuilt **and** the rendered surface differs;
- again after compaction or `/clear` (the context lost it).

Never on every turn: an unchanged surface is not repeated. The model sees it as additional
context of the prompt; the person does not. Headless runs (`claude -p`, scripts) get nothing,
unless `MNEME_RECEPTOR_HEADLESS=1` (used for live checks).

What was shown lives in the session's `$.state`: a reload of the mod does not deliver the surface
again, `/clear` does.

### Dev window (temporary)

`/mneme` opens a debug pane (`hooks/devpane.js`): every delivery of this session with its reason
(first prompt / surface changed / after compaction / after `/clear`), the exact block as it came to
the agent (select a delivery to open it), whether the context holds a surface now, the source state
and errors. In a session nothing draws in (`claude -p`) it answers in text.
`MNEME_RECEPTOR_DEV=0` turns the history and the window off. To remove it for good: delete
`hooks/devpane.js`, its import, the `history` state and the Pane hook in `receptor.js`.

## How it works

```text
prompt.submit
  -> stat <state>/mneme_read_model.sqlite3          (cheap, every prompt)
  -> unchanged since last build and already shown?  -> nothing
  -> python surface.py --state-dir <state>          (~0.3 s, only on change)
       Mneme core load_active_surface_from_read_model: read-only, timeout 0.05 s
  -> source ok, surface differs from what is shown? -> context += surface + one Claude Code line
```

Fail-open: a missing read model, a Python that does not start, a crash in `surface.py` —
the prompt goes on without a surface, and `/mneme` says why.

## Install

Load the plugin directory for one session:

```bash
claude --plugin-dir <Mneme>/adapters/claude_code
```

or for every session (the Desktop app too), in `~/.claude/settings.json`:

```json
{ "env": {
    "CLAUDE_CODE_PLUGIN_DIRS": "<Mneme>/adapters/claude_code",
    "MNEME_STATE_DIR": "<the same state dir the mneme MCP server uses>"
} }
```

Several plugin directories are separated by `;` on Windows and `:` elsewhere.
`MNEME_PYTHON` picks the interpreter (default `python`); `surface.py` needs only the standard
library and `src/` of this repo. Claude Code 2.1.287+ (mods on by default).

## Tests

```bash
cd adapters/claude_code && claude plugin validate . && claude plugin test   # the mod, 10 tests
python -m pytest tests/test_claude_code_surface.py                          # surface.py, 4 tests
```

## First live check (2026-10-06)

A real `claude -p` run with this plugin and the agent's real state: the model found the block in
its context and copied it verbatim; asked about the start of the Claude–Nira collaboration, it
picked a route from the surface, called `mcp__mneme__get_item` and answered from the item.

It picked the wrong route. All three routes sat under one topic (`Mneme residual /
uncategorized`) and differed only by id, so the choice was blind. The delivery works; what the
surface needs next is a one-line handle per route (the metapointer `claim`), not mnion bodies.
