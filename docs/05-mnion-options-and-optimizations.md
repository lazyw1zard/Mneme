# Mnion Options and Optimizations

Status: living project note

This file is the shelf for practical tuning ideas while mnion is still a small working primitive. It should collect options, tradeoffs, and future optimizations without forcing Mneme into a premature schema.

## Current implemented defaults

```text
DEFAULT_TTL_SECONDS = 604800  # 7 days, wall-clock fallback
DEFAULT_CALL_TTL = 32         # Mneme/memory-tag-call lifetime
DEFAULT_ACTIVE_MEMORY_TAG_LIMIT = 20
```

Meaning:

```text
wall TTL  = safety cap if the organ is not called for a long time
call TTL  = main lifecycle axis: how many memory-organ passes a tag survives
active limit = prompt-facing/read path budget guard
```

## Current storage

```text
$MNEME_STATE_DIR/memory_tags.jsonl
$MNEME_STATE_DIR/mneme_seq.json

# fallback when MNEME_STATE_DIR is unset:
$XDG_STATE_HOME/mneme/...
# or ~/.local/state/mneme/... when XDG_STATE_HOME is unset
```

`mneme_seq.json` remains deliberately tiny:

```json
{"seq": 2}
```

It counts only Mneme/memory-tag calls, not every model generation, Hermes turn, Telegram delivery, Codex run, or tool execution.

## Near-term tuning questions

### 1. Default call TTL

Current default is `32` calls.

Why not `20`:

- early mnions may need more than a few sparse memory passes before they have a fair chance to be touched;
- the organ will not be called every model turn;
- a low call TTL would decay records before we learn whether repetition/valence matters.

Why not much larger yet:

- long-lived tags can accumulate noise;
- without `touch` and valence update, a huge TTL delays decay without adding intelligence;
- we need empirical pressure from real use before choosing bigger ranges.

Future practical candidates:

| call_ttl | likely behavior |
|---:|---|
| 24 | stricter, fast decay |
| 32 | current moderate default |
| 48 | gentler exploration window |
| 64 | long observation window, may keep too much |

### 2. Wall TTL

Current default is `7 days`.

Keep it as a fallback, not the real mnion life.

Reasons to keep:

- if Mneme is not called for a week, old active tags should not remain active forever;
- wall time protects runtime files from stale active material;
- it gives a simple safety behavior before richer sweep/archive exists.

Possible later values:

| wall_ttl | use case |
|---|---|
| 7 days | current safety cap |
| 14 days | slower agent work rhythm |
| 30 days | if call-based decay becomes reliable and active loading stays bounded |

### 3. Active load limit

Current default is `20` active records.

This protects the prompt-facing path:

```text
normal read -> newest 20 active memory tags
explicit audit -> full/expired ledger
```

Future tuning options:

- keep fixed `20` until real usage shows pressure;
- split by valence buckets: high-valence active tags get priority;
- cap by estimated serialized chars, not count;
- produce a compact active brief instead of raw records.

## Open-source hygiene

Keep the reusable surface neutral:

- public project/package name: `mneme` / Mneme;
- prompt-visible MCP affordance: `mcp_memory_tag_capture`;
- no `nira-` prefixes in package names, default state dirs, or public examples;
- no absolute development paths in README/docs/config snippets;
- use `MNEME_STATE_DIR`, `XDG_STATE_HOME`, `$PROJECT_DIR`, and `$KERNEL_ROOT` placeholders;
- local/private receipts may exist outside the reusable surface, but public docs should describe them as examples or receipts without requiring those paths.

## Future config file

Do not add config until values need tuning in practice. When needed, prefer a small local config such as:

```text
~/.config/mneme/config.toml
```

Implemented shape:

```toml
[memory_tag]
default_ttl_seconds = 604800
default_call_ttl = 32
active_limit = 20
high_valence_threshold = 0.7

[review_pressure]
enabled = true
call_seq_interval = 10
trigger_on_high_valence = true
trigger_on_interval = true
packet_limit = 6

[storage]
state_dir = "~/.local/state/mneme"
```

Review pressure is checked on Mneme/memory-tag calls. This is an automatic
**invocation signal** for agentic review, not automatic semantic consolidation:

```text
capture/touch
  -> increment mneme_call_seq
  -> inspect active unread memory_tags
  -> if high confirmed valence or seq interval says pressure:
       return review_pressure.needed=true
       return suggested_action="prepare_micro_consolidation_request"
       return bounded review_packet metadata
       return agent_ingress.rendered="MNEME_REVIEW_PRESSURE..."
  -> no model call, no mnion receipt, no pointer, no kernel/engram write
```

`review_packet` is the structured bounded packet. `agent_ingress` is the same
pressure handed directly to the live agent in a rendered tool-result brief so
it is present at the Mneme call boundary, not merely stored beside the call.
This is the guard against the agent forgetting to invoke review after Mneme
detects pressure.

For already reviewed mnions, `list_topics` returns a route map only:

```text
list_topics
  -> topic map for choosing routes
  -> compact topic labels + review_id routes
  -> agent chooses a route
  -> get_item(review_id) returns its reviewed mnion
  -> no default body preload, no SQL, no receipt_json, no auto-promotion
```

The former `active_ingress` response field and its experimental Python helpers
(`ActiveMnionIngress`, `active_mnion_ingress_for_context`) are retired. Host
receptors use `load_active_surface_from_read_model` to return the compact
`MNEME_METAMEMORY_SURFACE`; reviewed bodies remain behind selected retrieval.

The interval check is intentionally simple and script-level: every Mneme call
can compare the current `mneme_call_seq` against `call_seq_interval`. It is not
based only on “calls since last consolidation,” because that can let a large
unreviewed tag pile accumulate if the live agent forgets to review.

Rules for config:

- code constants remain safe defaults;
- missing config should not break the organ;
- invalid config should fail loudly in CLI/tests, not silently distort memory;
- MCP adapter may use config, but core should still accept explicit parameters for tests and portability;
- config is operational tuning, not ontology.

## Optimization shelf

### A. Avoid reading huge JSONL forever

Current `load_memory_tags` still scans the JSONL file, then returns a bounded active window. This prevents prompt flooding but not IO growth.

Future options:

1. `active_memory_tags.jsonl` sidecar updated by sweep;
2. archived expired records moved to `mnions.archive.jsonl`;
3. small SQLite read model when JSONL scanning, review-state derivation, or agent packet selection becomes too slow/heavy;
4. compact active brief cache generated from active records.

Decision rule:

```text
optimize storage when measured IO, token pressure, or selection/read-model complexity appears
```

SQLite boundary:

```text
append-only records / receipts = audit evidence
SQLite                     = internal read model / queue substrate
agent-facing tools         = compact semantic paws, never SQL
```

SQLite is allowed earlier than a full database migration if it prevents agents from doing table/receipt/id bookkeeping in context. It must remain reconstructable from inspectable local evidence.

### B. Touch/reinforcement

Next likely primitive:

```text
mnion_touch(id, valence_delta, reason, affect_hints?)
```

Possible effects:

- update/rewrite active record state through an append-only event, not mutate history silently;
- increase or decrease valence;
- extend `call_ttl` for significant recurrence;
- mark review pressure if threshold is crossed.

Avoid for now:

- automatic promotion;
- graph edges;
- embedding search;
- hidden durable memory writes.

### C. ID readability

Current IDs are still UUID-like:

```text
mnion_<uuid4hex>
```

Possible later form:

```text
mn_YYYYMMDDTHHMMSSZ_<8hex>
```

Reason:

- easier human inspection;
- rough temporal orientation without opening the record;
- still collision-resistant enough for local JSONL.

Not urgent because `captured_at` already exists.

### D. Expired visibility

Normal path:

```text
load_memory_tags()
  -> active only
  -> bounded limit
```

Audit path:

```text
load_memory_tags(include_expired=True, limit=None)
```

Future recall tools should not expose hidden mnions by default. They should request audit/full mode explicitly.

### E. Valence threshold

Current:

```text
CONSOLIDATION_THRESHOLD = 0.7
```

This means review pressure, not promotion.

Future tuning:

- repeated medium-valence touches may matter more than one high valence birth;
- negative/caution/loss-cost vectors may deserve review without high pleasant valence;
- valence may need separate axes later: significance, risk, warmth, agency_pull.

Do not split axes until touch/review behavior proves the need.

<a id="cognee-ideas"></a>

## Идеи из Cognee — резерв решений (2026-11-14)

**Статус: сохранённые варианты для обсуждения, не принятые архитектурные решения,
не очередь реализации и не разрешение менять runtime.** Проверен код Cognee
на коммите `4053f6cc5536757f26a3665eed95c50088e6dc0b`; это статическое чтение,
не запуск платформы или её тестов и не измерение полезности на корпусе Mneme.
Соседние старые разделы этой полки сохраняются как история; актуальную очередь
и реализованные возможности определяет [NEXT_STEPS](../NEXT_STEPS.md).

### 1. Общий обзор и узнаваемость отдельной ветки

В детерминированном индексе Cognee общий обзор выделяет распространённые
сущности, а карточка документа — отличительные для него через TF-IDF.
Идентичность карточки не зависит от текста; обновляются изменившиеся карточки,
устаревшие удаляются. Построение этого индекса не вызывает LLM, но использует
уже извлечённые данные; это не отсутствие моделей во всём процессе.[2]

**Возможность для Mneme:** различать «что в памяти широко представлено» и
«по чему узнать именно эту историю». Отличительный ориентир может не быть
самым валентным. Рассмотреть это при оценке описания ветки рядом с головой,
заметными узлами и стыками, не добавляя сейчас четвёртую обязательную категорию.
TF-IDF, извлечение сущностей и новые поля этим не выбраны.

**Ограничения:** карточка Cognee может включать существующую связь выбранных
сущностей без подтверждения, что именно этот документ её утверждал.[2]
В Mneme навигация должна сохранять точные маршруты и основания; механическая
сборка не создаёт новых авторских отношений и не переписывает оригиналы.
Отличимость проверять на похожих историях с фиксированными маршрутами и бюджетом,
не путать с частотностью, важностью содержания или полнотой покрытия.

### 2. Время как самостоятельный источник кандидатов

Temporal retriever Cognee добавляет к исходной выборке фрагменты, связанные
с датами нужного интервала, до финального ранжирования и обрезки. Он не только
переставляет результаты поиска по сходству: нужные временные строки могут
вообще не попасть в первоначальную выборку.[3]

**Возможность для Mneme:** сохранить временное приобретение кандидатов независимо
от лексического порога, затем раскрывать существующее авторское соседство.
Это подтверждает уже описанное направление
[широкого кандидатного сбора](plans/broad-candidate-entry.md), не создаёт новый
параллельный поисковый проект. Кандидата, отсутствующего в выборке, нельзя
вернуть одним лишь reranking. Возможный проверочный случай — последовательные
шаги с низким лексическим пересечением плюс близкий по времени чужой сюжет.

**Ограничения:** дата события, capture-time, consolidation-time/seq и порядок
добавления в ветку — разные координаты. Временная близость предлагает кандидата,
не доказывает смысловое отношение. Новые модели извлечения дат и embeddings
не выбраны; широкий сбор тоже должен иметь предел работы и выдачи.

### 3. Адресная обратная связь и учёт её применения

Cognee отдельно описывает точные фрагменты/элементы графа, поданные генератору,
с оговоркой: `used_as_context` не доказывает поддержку каждого утверждения
ответа.[6] При изменении feedback weights он хранит списки уже обработанных
узлов/рёбер, оценку, источник сигнала и число попыток; повтор использует этот
учёт, чтобы не усиливать заново уже отмеченные элементы.[8]

**Возможность для второго уровня Mneme — обратной связи и усиления:** сохранять
адресность сигнала и квитанцию его применения, различая показ, намеренное
раскрытие, возможное использование и результат. Повтор доставки или частичный
сбой не должен давать дополнительное усиление. Поэлементный учёт сам по себе
ещё не доказывает атомарность записи веса и квитанции при аварии.

**Не переносить:** «хороший ответ — усиливаем всё поданное» или «плохой ответ —
наказываем все найденные факты». Ошибка генерации не равна ошибке памяти;
непроцитированная память тоже может быть полезной. Формула, источник оценки,
инструменты и реализация адаптивного feedback остаются отдельным выбором.

### 4. Ленивое остывание доступности

В подсистеме пользовательских предпочтений Cognee эффективный вес вычисляется
из сохранённого веса и числа прошедших ходов; только ради старения запись
постоянно не переписывается.[7]

**Возможность для будущей яркости веток:** хранить исходное состояние и якорь
обновления, вычисляя текущую доступность при отборе/обращении. Это может убрать
необходимость фонового worker, который лишь уменьшает веса. Содержание,
валентность и исторические свидетельства не обязаны изменяться при остывании.

**Ограничения:** у Cognee это конкретно пользовательские предпочтения, не общее
забывание памяти. Нейтральный уровень, формула и часы не переносятся в Mneme
автоматически. Открыты выбор часов, конкуренция входов и предотвращение вечных
аттракторов; raw-tag TTL не является политикой яркости веток или забывания мнионов.

### Предохранители и границы заимствования

- Не заимствовать политику, при которой переполнение пакета закрывается как
  обработанное без рассмотрения. В некоторых проходах дистилляции Cognee
  так закрывается overflow, а после некоторых writer failures потерянные выводы
  не повторяются автоматически; другие ветки ошибок оставляют материал для
  повтора.[9] В Mneme «не поместилось», «ошибка», «отложено» и «рассмотрено»
  должны оставаться различимы; ограничение работы не равно успешному сохранению.
- Не добавлять Cognee как зависимость ради этих идей: базовый стек включает
  отдельные графовое и векторное хранилища, embeddings и веб/API-компоненты.[5]
  Сначала оценить потребность и общую стоимость переносимого принципа.
- Первые две идеи относятся к сохранению/консолидации и навигации; последние две
  — преимущественно к будущей обратной связи и доступности. Они не требуют
  переносить reinforcement в текущий слайс или возобновлять векторный резерв.
- Не менять на основании этой заметки согласованное определение ветки,
  существующие мнионы, отношения, live ingress или очередь `next`.

## Current non-goals

- no full semantic Mneme database;
- no agent-facing SQL/table work;
- no raw transcript ingestion;
- no automatic kernel/engram writes;
- no Hermes/Codex dependency for lifecycle;
- no prompt dump of full memory tag ledger;
- no promotion from `memory_tag.capture` alone.

## Working maxim

```text
cheap to notice;
bounded to read;
expensive to keep.
```

## Sources

[2] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/cognee/tasks/memify/global_context_index/build_document_index.py
[3] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/cognee/modules/retrieval/temporal_hybrid_retriever.py
[5] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/pyproject.toml
[6] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/cognee/modules/retrieval/utils/evidence.py
[7] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/cognee/modules/user_preferences/weights.py
[8] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/cognee/tasks/memify/apply_feedback_weights.py
[9] https://github.com/topoteretes/cognee/blob/4053f6cc5536757f26a3665eed95c50088e6dc0b/cognee/modules/session_distillation/distill.py
