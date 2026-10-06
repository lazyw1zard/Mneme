// Mneme receptor for Claude Code: the agent's metamemory surface beside its prompt.
//
// Mneme core renders MNEME_METAMEMORY_SURFACE from the materialized read model (read-only,
// a route map, no mnion bodies, no surface gate). This mod only delivers it, as context the
// model reads and the person does not see:
//   - with the first prompt of a session,
//   - again when the memory changed (the read model was rebuilt and the surface differs),
//   - again after compaction or /clear, when the context lost it.
// Never on every turn: an unchanged surface is not repeated.
//
// The surface is built by surface.py next to this plugin (Python + Mneme core). Per prompt the
// mod only stats the read model, so the Python start (~0.3 s) is paid on change only.
// Headless runs (claude -p, scripts) get nothing unless MNEME_RECEPTOR_HEADLESS=1.

const SURFACE_TIMEOUT_MS = 3000
const READ_MODEL = 'mneme_read_model.sqlite3'
const CLAUDE_CODE_NOTE =
  'claude_code: get_item here is the tool mcp__mneme__get_item. This map comes with the first prompt ' +
  'and again only when memory changes; it is not repeated every turn.'

let active = true      // interactive session, or headless with MNEME_RECEPTOR_HEADLESS=1
let stateDir = ''
let python = ''
let shown = null       // the surface now in the context; null = the context does not have it
let builtMtime = null  // read model mtime the last build saw
let status = { state: 'нет данных', at: null, topics: 0, reason: null, error: null }

async function resolveConfig($, e) {
  const headless = await $.env.get('MNEME_RECEPTOR_HEADLESS')
  active = e.isInteractive !== false || headless === '1'
  const explicit = await $.env.get('MNEME_STATE_DIR')
  const xdg = await $.env.get('XDG_STATE_HOME')
  const home = (await $.env.get('HOME')) || (await $.env.get('USERPROFILE')) || ''
  stateDir = explicit || (xdg ? xdg + '/mneme' : home + '/.local/state/mneme')
  python = (await $.env.get('MNEME_PYTHON')) || 'python'
}

// Runs surface.py; returns its JSON, or null with status.error set.
async function buildSurface($) {
  const argv = [python, $.plugin.root + '/surface.py', '--state-dir', stateDir]
  let run
  try {
    run = await $.process.run(argv, { timeoutMs: SURFACE_TIMEOUT_MS })
  } catch (err) {
    status = { ...status, error: 'surface.py не запустился: ' + (err?.message || err) }
    return null
  }
  if (run.exitCode !== 0) {
    status = { ...status, error: 'surface.py: ' + String(run.stderr || '').trim().split('\n').pop() }
    return null
  }
  try {
    return JSON.parse(run.stdout)
  } catch {
    status = { ...status, error: 'surface.py: ответ не JSON' }
    return null
  }
}

// The block to put beside this prompt, or null when the context already has the current surface.
async function surfaceToShow($) {
  let mtime
  try {
    mtime = (await $.fs.stat(stateDir + '/' + READ_MODEL)).mtimeMs
  } catch {
    status = { ...status, state: 'read model не найден', error: stateDir + '/' + READ_MODEL }
    return null
  }
  if (shown !== null && mtime === builtMtime) return null
  builtMtime = mtime
  const surface = await buildSurface($)
  if (!surface) return null
  status = { state: surface.source_status, at: new Date().toISOString(), topics: surface.topics, reason: surface.reason, error: null }
  if (surface.source_status !== 'ok' || !surface.rendered) return null
  if (surface.rendered === shown) return null
  shown = surface.rendered
  return surface.rendered + '\n' + CLAUDE_CODE_NOTE
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    await resolveConfig($, e)
    await $.command.register({ name: 'mneme', description: 'Mneme: что receptor показывает агенту и когда', immediate: true })
    return next(e)
  })

  on('prompt.submit', async ($, e, next) => {
    if (!active) return next(e)
    const block = await surfaceToShow($)
    if (!block) return next(e)
    return next({ ...e, context: [...(e.context ?? []), block] })
  })

  // The context lost what was shown: show it again with the next prompt.
  on('classic.SessionStart', { source: ['compact', 'clear'] }, async ($, e, next) => {
    shown = null
    builtMtime = null
    return next(e)
  })

  on('command.run', { command: 'mneme' }, async () => {
    const lines = [
      `receptor: ${active ? 'активен' : 'выключен (headless)'} · состояние: ${status.state}` +
        (status.at ? ` · собрано ${status.at.slice(11, 19)}` : '') + ` · тем: ${status.topics}`,
      `state dir: ${stateDir}`,
    ]
    if (status.reason) lines.push('reason: ' + status.reason)
    if (status.error) lines.push('ошибка: ' + status.error)
    lines.push(shown ? 'в контексте агента сейчас:\n' + shown : 'в контексте агента карты сейчас нет')
    return { text: lines.join('\n') }
  })
}
