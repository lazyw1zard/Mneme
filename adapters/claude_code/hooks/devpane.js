// DEV ONLY — the receptor's debug window (/mneme). Remove this file together with the
// `history` writes and the Pane hook in receptor.js when the receptor is trusted.
//
// Draws from plain data; it never touches the mods API.

const WHY = {
  first: 'первый промпт сессии',
  changed: 'карта изменилась',
  compact: 'после сжатия контекста',
  clear: 'после /clear',
}

export const whyText = why => WHY[why] || why

const time = iso => (iso ? String(iso).slice(11, 19) : '—')

// view: { attended, surfaces, stateDir, status, shown, history, selected, onSelect }
export function renderDevPane(ui, view) {
  const { Box, Text, Button, Code } = ui
  const { status, history } = view
  const rows = []

  rows.push(Text({ bold: true, children: ['Mneme receptor · dev: что и когда приходит Клоду'] }))
  rows.push(Text({
    dimColor: true,
    children: [
      `экран: ${view.surfaces.join(', ') || 'нет (headless)'} · источник: ${status.state} · собрано ${time(status.at)} · тем: ${status.topics}`,
    ],
  }))
  rows.push(Text({ dimColor: true, wrap: 'truncate-middle', children: ['state dir: ' + view.stateDir] }))
  if (status.reason) rows.push(Text({ color: 'yellow', children: ['reason: ' + status.reason] }))
  if (status.error) rows.push(Text({ color: 'red', children: ['ошибка: ' + status.error] }))

  rows.push(Text({ children: [' '] }))
  rows.push(Text({
    bold: true,
    children: [view.shown ? 'Сейчас в контексте Клода: доставка #' + history.length : 'Сейчас карты в контексте Клода нет: придёт с ближайшим промптом'],
  }))

  rows.push(Text({ children: [' '] }))
  rows.push(Text({ bold: true, children: [`Доставки в этой сессии: ${history.length}`] }))
  if (!history.length) rows.push(Text({ dimColor: true, children: ['пока ни одной'] }))
  history.forEach((d, i) => rows.push(Button({
    key: 'delivery-' + i,
    label: `#${i + 1}  ${time(d.at)}  ${whyText(d.why)} · тем ${d.topics} · ${d.text.length} симв.`,
    plain: true,
    dimColor: i !== view.selected,
    onPress: () => view.onSelect(i),
  })))

  const chosen = history[view.selected]
  if (chosen) {
    rows.push(Text({ children: [' '] }))
    rows.push(Text({ bold: true, children: [`#${view.selected + 1} — дословно, как пришло Клоду рядом с промптом:`] }))
    rows.push(Code({ source: chosen.text.slice(0, 10000) }))
  }
  return Box({ flexDirection: 'column', children: rows })
}

// For a session nothing draws in (claude -p): the same facts as text.
export function devText(view) {
  const { status, history } = view
  const lines = [
    `receptor: ${view.attended === false ? 'молчит: у сессии нет экрана (headless)' : 'активен'} · состояние: ${status.state}` +
      (status.at ? ` · собрано ${time(status.at)}` : '') + ` · тем: ${status.topics}`,
    `state dir: ${view.stateDir}`,
  ]
  if (status.reason) lines.push('reason: ' + status.reason)
  if (status.error) lines.push('ошибка: ' + status.error)
  lines.push(`доставок в этой сессии: ${history.length}` + history.map((d, i) => `\n  #${i + 1} ${time(d.at)} ${whyText(d.why)}`).join(''))
  lines.push(view.shown ? 'в контексте агента сейчас:\n' + view.shown : 'в контексте агента карты сейчас нет')
  return lines.join('\n')
}
