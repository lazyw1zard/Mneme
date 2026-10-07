// Mneme receptor for Claude Code: the agent's metamemory surface beside its prompt.
//
// Mneme core renders MNEME_METAMEMORY_SURFACE from the materialized read model (read-only,
// a route map, no mnion bodies, no surface gate). This mod only delivers it, as context the
// model reads and the person does not see:
//   - with the first prompt of a session,
//   - again when the memory changed (the read model was rebuilt and the surface differs),
//   - again after compaction or /clear, when the context lost it.
// Never on every turn: an unchanged surface is not repeated, and a reload of the mod does not
// make it forget what it showed (that lives in $.state, which /clear resets).
//
// The surface is built by surface.py next to this plugin (Python + Mneme core). Per prompt the
// mod only stats the read model, so the Python start (~0.3 s) is paid on change only.
// Only sessions a person is at get it: the REPL, or an app attached to the session (the Desktop
// Code tab runs through the SDK, so isInteractive is false there, but it attaches as `desktop`).
// A plain `claude -p` run draws nowhere and gets nothing, unless MNEME_RECEPTOR_HEADLESS=1.
//
// DEV: /mneme opens a debug window (hooks/devpane.js) with every delivery of this session.
// MNEME_RECEPTOR_DEV=0 turns the history and the window off.

import { atom, read, update } from 'claude-code'
import { renderDevPane, devText } from './devpane.js'

const SURFACE_TIMEOUT_MS = 3000
const READ_MODEL = 'mneme_read_model.sqlite3'
const DEV_PANE = 'mneme-dev'
const MAX_HISTORY = 30
const CLAUDE_CODE_NOTE =
  'claude_code: get_item here is the tool mcp__mneme__get_item. This map comes with the first prompt ' +
  'and again only when memory changes; it is not repeated every turn.'

const shownAtom = atom({ plugin: 'mneme-receptor', key: 'shown' }, null)
const builtAtom = atom({ plugin: 'mneme-receptor', key: 'builtMtime' }, null)
const resetAtom = atom({ plugin: 'mneme-receptor', key: 'resetReason' }, null)
const statusAtom = atom({ plugin: 'mneme-receptor', key: 'status' },
  { state: 'нет данных', at: null, topics: 0, reason: null, error: null })
const historyAtom = atom({ plugin: 'mneme-receptor', key: 'history' }, [])

let headless = false   // MNEME_RECEPTOR_HEADLESS=1: deliver even where nothing draws (live checks)
let dev = true         // MNEME_RECEPTOR_DEV=0: no history, no debug window
let attended = null    // did the last prompt come with a person at some surface
let stateDir = ''
let python = ''
let selected = -1      // dev window: which delivery is open (-1: the latest)

async function resolveConfig($) {
  headless = (await $.env.get('MNEME_RECEPTOR_HEADLESS')) === '1'
  dev = (await $.env.get('MNEME_RECEPTOR_DEV')) !== '0'
  const explicit = await $.env.get('MNEME_STATE_DIR')
  const xdg = await $.env.get('XDG_STATE_HOME')
  const home = (await $.env.get('HOME')) || (await $.env.get('USERPROFILE')) || ''
  stateDir = explicit || (xdg ? xdg + '/mneme' : home + '/.local/state/mneme')
  python = (await $.env.get('MNEME_PYTHON')) || 'python'
}

async function setStatus($, patch) {
  await update($, statusAtom, s => ({ ...s, ...patch }))
}

// Runs surface.py; returns its JSON, or null with the error in the status.
async function buildSurface($) {
  const argv = [python, $.plugin.root + '/surface.py', '--state-dir', stateDir]
  let run
  try {
    run = await $.process.run(argv, { timeoutMs: SURFACE_TIMEOUT_MS })
  } catch (err) {
    await setStatus($, { error: 'surface.py не запустился: ' + (err?.message || err) })
    return null
  }
  if (run.exitCode !== 0) {
    await setStatus($, { error: 'surface.py: ' + String(run.stderr || '').trim().split('\n').pop() })
    return null
  }
  try {
    return JSON.parse(run.stdout)
  } catch {
    await setStatus($, { error: 'surface.py: ответ не JSON' })
    return null
  }
}

// The block to put beside this prompt, or null when the context already has the current surface.
async function surfaceToShow($) {
  let mtime
  try {
    mtime = (await $.fs.stat(stateDir + '/' + READ_MODEL)).mtimeMs
  } catch {
    await setStatus($, { state: 'read model не найден', error: stateDir + '/' + READ_MODEL })
    return null
  }
  const shown = await read($, shownAtom)
  if (shown !== null && mtime === (await read($, builtAtom))) return null
  await update($, builtAtom, () => mtime)
  const surface = await buildSurface($)
  if (!surface) return null
  await setStatus($, { state: surface.source_status, at: new Date().toISOString(), topics: surface.topics, reason: surface.reason, error: null })
  if (surface.source_status !== 'ok' || !surface.rendered) return null
  if (surface.rendered === shown) return null

  const block = surface.rendered + '\n' + CLAUDE_CODE_NOTE
  const reset = await read($, resetAtom)
  const why = reset || (shown === null && !(await read($, historyAtom)).length ? 'first' : 'changed')
  await update($, shownAtom, () => surface.rendered)
  await update($, resetAtom, () => null)
  if (dev) {
    await update($, historyAtom, h => [...h, { at: new Date().toISOString(), why, text: block, topics: surface.topics }].slice(-MAX_HISTORY))
    selected = -1
    $.ui.invalidate('ui.render')
  }
  return block
}

// What the dev window and the text fallback draw from.
async function devView($) {
  const history = await read($, historyAtom)
  return {
    attended,
    surfaces: [...(await $.session.surfaces())],
    stateDir,
    status: await read($, statusAtom),
    shown: await read($, shownAtom),
    history,
    selected: selected < 0 ? history.length - 1 : selected,
  }
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    await resolveConfig($)
    await $.command.register({ name: 'mneme', description: 'Mneme: что receptor показывает агенту и когда (dev-окно)', immediate: true })
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    // asked per prompt: an app may attach after the session started
    attended = headless || (await $.session.surfaces()).length > 0
    if (!attended) return next(e)
    const block = await surfaceToShow($)
    if (!block) return next(e)
    return next({ ...e, context: [...(e.context ?? []), block] })
  })

  // The context lost what was shown: show it again with the next prompt, and say why.
  on('classic.SessionStart', { source: ['compact', 'clear'] }, async ($, e, next) => {
    await update($, shownAtom, () => null)
    await update($, builtAtom, () => null)
    await update($, resetAtom, () => e.source)
    return next(e)
  })

  on('command.run', { command: 'mneme' }, async ($) => {
    if (dev && (await $.session.surfaces()).length) {
      await $.ui.open({ id: DEV_PANE, title: 'Mneme · dev', focus: true, closeOnEscape: true })
      return {}
    }
    return { text: devText(await devView($)) }
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== DEV_PANE) return next(e)
    const view = await devView($)
    view.onSelect = i => { selected = i; $.ui.invalidate('ui.render') }
    return renderDevPane($.ui.resolve(e), view)
  })
}
