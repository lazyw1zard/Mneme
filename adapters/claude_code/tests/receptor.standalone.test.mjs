// Standalone regression tests: real receptor/devpane modules in a Node VM, with a minimal
// mocked Claude host API. This is NOT Claude Code's native SDK/mod test runner.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const source = await readFile(new URL('../hooks/receptor.js', import.meta.url), 'utf8')
const paneSource = await readFile(new URL('../hooks/devpane.js', import.meta.url), 'utf8')
const SURFACE_A = 'MNEME_METAMEMORY_SURFACE\nArea A | routes=review_a'
const SURFACE_B = SURFACE_A + '\nArea B | routes=review_b'

async function world({ surfaces = ['terminal'], env = {} } = {}) {
  const handlers = []
  const state = new Map()
  const w = { mtime: 1000, surface: SURFACE_A, failure: '', runs: 0, invalidations: 0, invalidateThrows: false }
  const context = vm.createContext({ Date })
  const api = new vm.SyntheticModule(['atom', 'read', 'update'], function () {
    this.setExport('atom', (id, initial) => ({ key: id.plugin + ':' + id.key, initial }))
    this.setExport('read', async ($, atom) => state.has(atom.key) ? state.get(atom.key) : atom.initial)
    this.setExport('update', async ($, atom, fn) => {
      state.set(atom.key, fn(state.has(atom.key) ? state.get(atom.key) : atom.initial))
    })
  }, { context })
  const pane = new vm.SourceTextModule(paneSource, { context })
  const receptor = new vm.SourceTextModule(source, { context })
  await receptor.link(specifier => {
    if (specifier === 'claude-code') return api
    if (specifier === './devpane.js') return pane
    throw new Error('Unexpected import: ' + specifier)
  })
  await receptor.evaluate()
  receptor.namespace.register((event, filter, handler) => {
    if (typeof filter === 'function') { handler = filter; filter = {} }
    handlers.push({ event, filter, handler })
  })
  const $ = {
    env: { get: async key => ({ MNEME_STATE_DIR: '/state', ...env })[key] },
    plugin: { root },
    fs: { stat: async () => ({ mtimeMs: w.mtime }) },
    process: { run: async () => {
      w.runs++
      if (w.failure === 'start') throw new Error('temporary process failure')
      if (w.failure === 'exit') return { exitCode: 1, stdout: '', stderr: 'temporary exit failure' }
      if (w.failure === 'json') return { exitCode: 0, stdout: '{invalid JSON', stderr: '' }
      const unavailable = w.failure === 'unavailable'
      return { exitCode: 0, stderr: '', stdout: JSON.stringify({
        source_status: unavailable ? 'unavailable' : 'ok',
        rendered: unavailable ? '' : w.surface,
        topics: w.surface ? 1 : 0,
        reason: unavailable ? 'locked_read_model' : null,
      }) }
    } },
    command: { register: async () => {} },
    session: { surfaces: async () => surfaces },
    ui: { invalidate: () => {
      w.invalidations++
      if (w.invalidateThrows) throw new Error('optional dev UI unavailable')
    } },
  }
  async function emit(event, value = {}) {
    const selected = handlers.filter(h => h.event === event && Object.entries(h.filter).every(
      ([key, expected]) => Array.isArray(expected) ? expected.includes(value[key]) : expected === value[key],
    ))
    let index = 0
    async function next(e) {
      const h = selected[index++]
      return h ? h.handler($, e, next) : e
    }
    return next(value)
  }
  await emit('session.start')
  return {
    w, emit,
    saved: key => state.get('mneme-receptor:' + key),
    prompt: () => emit('prompt.submit', { text: 'probe', context: ['existing context'] }),
  }
}

function assertDelivered(entered, surface) {
  assert.equal(entered.text, 'probe')
  assert.equal(entered.context.length, 2)
  assert.equal(entered.context[0], 'existing context')
  assert.ok(entered.context[1].startsWith(surface + '\n'))
  assert.match(entered.context[1], /mcp__mneme__get_item/)
}
function assertQuiet(entered) {
  assert.equal(entered.text, 'probe')
  assert.deepEqual(Array.from(entered.context), ['existing context'])
}

for (const failure of ['start', 'exit', 'json', 'unavailable']) {
  test(`after successful A, ${failure} failure retries B at unchanged mtime`, async () => {
    const t = await world()
    assertDelivered(await t.prompt(), SURFACE_A)
    t.w.mtime = 2000
    t.w.surface = SURFACE_B
    t.w.failure = failure
    assertQuiet(await t.prompt())
    assert.equal(t.saved('shown'), SURFACE_A)
    // The still-failing retry must run again without a new read-model mtime.
    assertQuiet(await t.prompt())
    assert.equal(t.w.runs, 3)
    t.w.failure = ''
    assertDelivered(await t.prompt(), SURFACE_B)
    assert.equal(t.saved('builtMtime'), 2000)
    assert.equal(t.saved('shown'), SURFACE_B)
    assertQuiet(await t.prompt())
    assert.equal(t.w.runs, 4)
  })

  test(`before first delivery, ${failure} failure retries at unchanged mtime`, async () => {
    const t = await world()
    t.w.failure = failure
    assertQuiet(await t.prompt())
    t.w.failure = ''
    assertDelivered(await t.prompt(), SURFACE_A)
    assertQuiet(await t.prompt())
    assert.equal(t.w.runs, 2)
  })
}

for (const surface of [SURFACE_A, '']) {
  test(`successful ${surface ? 'identical' : 'empty'} surface caches the new mtime`, async () => {
    const t = await world()
    assertDelivered(await t.prompt(), SURFACE_A)
    t.w.mtime = 2000
    t.w.surface = surface
    assertQuiet(await t.prompt())
    assert.equal(t.saved('builtMtime'), 2000)
    assert.equal(t.saved('shown'), SURFACE_A)
    assertQuiet(await t.prompt())
    assert.equal(t.w.runs, 2)
  })
}

test('throwing optional dev invalidation does not block prompt delivery or poison shown state', async () => {
  const t = await world()
  t.w.invalidateThrows = true
  assertDelivered(await t.prompt(), SURFACE_A)
  assert.equal(t.saved('shown'), SURFACE_A)
  assert.equal(t.saved('history').length, 1)
  assertQuiet(await t.prompt())
  t.w.mtime = 2000
  t.w.surface = SURFACE_B
  assertDelivered(await t.prompt(), SURFACE_B)
  assert.equal(t.saved('shown'), SURFACE_B)
  assert.equal(t.saved('history').length, 2)
  assertQuiet(await t.prompt())
  assert.equal(t.w.runs, 2)
  assert.equal(t.w.invalidations, 2)
})

test('compact and clear still reinject, while session reload stays deduplicated', async () => {
  const t = await world()
  assertDelivered(await t.prompt(), SURFACE_A)
  await t.emit('session.start')
  assertQuiet(await t.prompt())
  assert.equal(t.w.runs, 1)
  for (const reason of ['compact', 'clear']) {
    await t.emit('classic.SessionStart', { source: reason })
    assertDelivered(await t.prompt(), SURFACE_A)
    assertQuiet(await t.prompt())
    assert.equal(t.saved('history').at(-1).why, reason)
  }
  assert.equal(t.w.runs, 3)
})

test('headless still requires opt-in', async () => {
  const t = await world({ surfaces: [] })
  assertQuiet(await t.prompt())
  assert.equal(t.w.runs, 0)
  const optedIn = await world({ surfaces: [], env: { MNEME_RECEPTOR_HEADLESS: '1' } })
  assertDelivered(await optedIn.prompt(), SURFACE_A)
})

test('disabled dev UI still delivers without history or invalidation', async () => {
  const t = await world({ env: { MNEME_RECEPTOR_DEV: '0' } })
  t.w.invalidateThrows = true
  assertDelivered(await t.prompt(), SURFACE_A)
  assert.equal(t.saved('history'), undefined)
  assert.equal(t.w.invalidations, 0)
})
