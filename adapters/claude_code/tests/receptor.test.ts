import { expect, mock, test } from 'claude-code/testing'

const SURFACE_A = 'MNEME_METAMEMORY_SURFACE\ntopics:\n- Area A | routes=review_a'
const SURFACE_B = 'MNEME_METAMEMORY_SURFACE\ntopics:\n- Area A | routes=review_a\n- Area B | routes=review_b'

const PANE = {
  plugin: 'mneme-receptor',
  component: 'Pane',
  requestId: 'mneme-dev',
  viewport: { columns: 120, rows: 40 },
  props: { title: 'Mneme · dev', isFocused: true, bodyColumns: 100, placement: 'dock', scroll: { offset: 0, bodyRows: 30 }, view: {} },
} as const

// The receptor's world: a read model with an mtime, surface.py answering with a surface, and the
// surfaces the session draws on (`terminal` under the REPL, `desktop` when the app attached, none for -p).
function world(on: any, env: Record<string, string> = { MNEME_STATE_DIR: '/state' }, surfaces: string[] = ['terminal']) {
  const w = { mtime: 1000, surface: SURFACE_A, status: 'ok', runs: 0, opened: 0, fail: '' as string, statPaths: [] as string[], argv: [] as string[] }
  mock.env(on, env)
  on('session.surfaces', () => ({ value: surfaces }))
  on('fs.stat', ($: any, e: any) => {
    w.statPaths.push(e.path)
    return { value: { kind: 'file', size: 4096, mtimeMs: w.mtime } }
  })
  on('process.run', ($: any, e: any) => {
    w.runs += 1
    w.argv = e.argv
    if (w.fail === 'start') return { deny: 'cannot start python' }
    if (w.fail === 'exit') return { value: { exitCode: 1, stdout: '', stderr: 'Traceback\nImportError: no mnion' } }
    const payload = { source_status: w.status, reason: w.status === 'ok' ? null : 'missing_read_model', topics: 1, rendered: w.status === 'ok' ? w.surface : '' }
    return { value: { exitCode: 0, stdout: JSON.stringify(payload) + '\n', stderr: '' } }
  })
  on('command.register', () => ({ value: undefined }))
  on('ui.open', () => { w.opened += 1; return { value: { isPlaced: true } } })
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['drawn by Claude Code'] }))
  on('session.start', () => ({ cwd: '/work' }))
  on('prompt.submit', ($: any, e: any) => ({ text: e.text, context: e.context }))
  on('classic.SessionStart', () => ({}))
  return w
}

const prompt = ($: any, text = 'привет') => $.prompt.submit({ text, wait: false, origin: { kind: 'user' } } as any) as Promise<any>
const ctx = (entered: any) => (entered.context ?? []) as string[]
const pane = ($: any) => $.ui.mount({ ...PANE, surface: 'desktop' })
const label = async (ui: any, key: string) => (await ui.find({ key }))?.props.label as string | undefined

test('first prompt gets the surface; an unchanged memory is not repeated and costs no Python start', async ($, on) => {
  const w = world(on)
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })

  const first = await prompt($)
  expect(ctx(first).length).toBe(1)
  expect(ctx(first)[0]).toMatch(/^MNEME_METAMEMORY_SURFACE/)
  expect(ctx(first)[0]).toMatch(/mcp__mneme__get_item/)
  expect(w.statPaths[0].replace(/\\/g, '/')).toMatch(/\/state\/mneme_read_model\.sqlite3$/)   // the engine makes paths absolute
  expect(w.argv.slice(2)).toEqual(['--state-dir', '/state'])
  expect(w.argv[1]).toMatch(/surface\.py$/)

  expect(ctx(await prompt($, 'дальше'))).toEqual([])
  expect(ctx(await prompt($, 'ещё'))).toEqual([])
  expect(w.runs).toBe(1)
})

test('memory changes: a rebuilt read model with the same surface stays quiet, a new surface comes once', async ($, on) => {
  const w = world(on)
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  await prompt($)

  w.mtime = 2000                      // rebuilt, same content
  expect(ctx(await prompt($))).toEqual([])
  expect(w.runs).toBe(2)

  w.mtime = 3000                      // rebuilt with a new area
  w.surface = SURFACE_B
  const changed = await prompt($)
  expect(ctx(changed).length).toBe(1)
  expect(ctx(changed)[0]).toMatch(/Area B/)
  expect(ctx(await prompt($))).toEqual([])
})

test('after compaction or /clear the surface comes again with the next prompt', async ($, on) => {
  const w = world(on)
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  await prompt($)
  expect(ctx(await prompt($))).toEqual([])

  await $.classic.SessionStart({ source: 'compact' } as any)
  expect(ctx(await prompt($)).length).toBe(1)

  await $.classic.SessionStart({ source: 'clear' } as any)
  expect(ctx(await prompt($)).length).toBe(1)
  expect(w.runs).toBe(3)
})

test('a new session.start (a reload of the mod) does not deliver the surface again', async ($, on) => {
  const w = world(on)
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  expect(ctx(await prompt($)).length).toBe(1)

  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })   // fires again after a reload
  expect(ctx(await prompt($))).toEqual([])
  expect(w.runs).toBe(1)
})

test('dev window: every delivery with its reason, the exact block, and what the context holds now', async ($, on) => {
  const w = world(on, { MNEME_STATE_DIR: '/state' }, ['desktop'])
  await $.session.start({ surface: null, isInteractive: false, cwd: '/work' } as any)
  const first = ctx(await prompt($))[0]
  w.mtime = 2000
  w.surface = SURFACE_B
  await prompt($)
  await $.classic.SessionStart({ source: 'compact' } as any)
  await prompt($)

  expect(await $.command.run({ command: 'mneme', args: '' })).toEqual({})
  expect(w.opened).toBe(1)

  const ui = await pane($)
  expect(await ui.find({ type: 'Text', text: /^Доставки в этой сессии: 3$/ })).toBeDefined()
  expect(await label(ui, 'delivery-0')).toMatch(/^#1 .* первый промпт сессии · тем 1/)
  expect(await label(ui, 'delivery-1')).toMatch(/^#2 .* карта изменилась/)
  expect(await label(ui, 'delivery-2')).toMatch(/^#3 .* после сжатия контекста/)
  expect(await ui.find({ type: 'Text', text: 'Сейчас в контексте Клода: доставка #3' })).toBeDefined()
  expect((await ui.find({ type: 'Code' }))?.props.source).toMatch(/Area B/)   // the latest is open

  await ui.press({ key: 'delivery-0' })
  expect((await ui.find({ type: 'Code' }))?.props.source).toBe(first)        // exactly what came, word for word
  await ui.unmount()
})

test('dev window says why nothing comes: broken Python, unavailable read model', async ($, on) => {
  const w = world(on, { MNEME_STATE_DIR: '/state' }, ['desktop'])
  await $.session.start({ surface: null, isInteractive: false, cwd: '/work' } as any)

  w.fail = 'start'
  const entered = await prompt($, 'вопрос')
  expect(entered.text).toBe('вопрос')
  expect(ctx(entered)).toEqual([])
  let ui = await pane($)
  expect(await ui.find({ type: 'Text', text: /ошибка: surface\.py не запустился/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /карты в контексте Клода нет/ })).toBeDefined()
  await ui.unmount()

  w.fail = 'exit'
  w.mtime = 2000
  expect(ctx(await prompt($))).toEqual([])
  ui = await pane($)
  expect(await ui.find({ type: 'Text', text: /ImportError: no mnion/ })).toBeDefined()
  await ui.unmount()

  w.fail = ''
  w.status = 'unavailable'
  w.mtime = 3000
  expect(ctx(await prompt($))).toEqual([])
  ui = await pane($)
  expect(await ui.find({ type: 'Text', text: /источник: unavailable/ })).toBeDefined()
  await ui.unmount()

  w.status = 'ok'
  w.mtime = 4000
  expect(ctx(await prompt($)).length).toBe(1)
})

test('a plain -p run gets nothing, and /mneme answers in text there', async ($, on) => {
  const w = world(on, { MNEME_STATE_DIR: '/state' }, [])
  await $.session.start({ surface: null, isInteractive: false, cwd: '/work' } as any)
  expect(ctx(await prompt($))).toEqual([])
  expect(w.runs).toBe(0)
  const answer = await $.command.run({ command: 'mneme', args: '' })
  expect(answer.text).toMatch(/молчит: у сессии нет экрана/)
  expect(w.opened).toBe(0)
})

test('MNEME_RECEPTOR_HEADLESS=1 delivers even where nothing draws (for live checks)', async ($, on) => {
  world(on, { MNEME_STATE_DIR: '/state', MNEME_RECEPTOR_HEADLESS: '1' }, [])
  await $.session.start({ surface: null, isInteractive: false, cwd: '/work' } as any)
  expect(ctx(await prompt($)).length).toBe(1)
})

test('MNEME_RECEPTOR_DEV=0: no window, no history, delivery unchanged', async ($, on) => {
  const w = world(on, { MNEME_STATE_DIR: '/state', MNEME_RECEPTOR_DEV: '0' }, ['desktop'])
  await $.session.start({ surface: null, isInteractive: false, cwd: '/work' } as any)
  expect(ctx(await prompt($)).length).toBe(1)
  const answer = await $.command.run({ command: 'mneme', args: '' })
  expect(answer.text).toMatch(/доставок в этой сессии: 0/)
  expect(w.opened).toBe(0)
})

test('without MNEME_STATE_DIR the state dir is the core default under HOME', async ($, on) => {
  const w = world(on, { HOME: '/home/agent' })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  await prompt($)
  expect(w.statPaths[0].replace(/\\/g, '/')).toMatch(/\/home\/agent\/\.local\/state\/mneme\/mneme_read_model\.sqlite3$/)
})
