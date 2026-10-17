# One-arc connected-entry pilot

## Question and intervention

Does an initial connected entrance add useful navigation beyond an existing
claims menu when the same deliberate relation tools are available?

This is a narrowed descriptive pilot of `NEXT_STEPS.md` item 1 / October Slice 4
Step 4. It is **not** a test of graph availability versus no graph, broad relation
efficacy, unprompted spontaneous recall or long-term consolidation.

Freeze: three real originals and their existing claims, two authored directed
relations, ordering, three relationship/negative-evidence questions and expected
facts. Expected facts remain evaluator-only. A receives the claims/routes menu;
B receives that same menu plus one existing `continues` edge preview and a route.
Both have identical `get_item` and frozen `get_neighborhood` tools (depth 1,
limit 4), instructions, model and budgets. Selected originals and neighborhoods
were retrieved from the accepted core and checked against disposable copies of
the sources; originals were not rewritten. Bodies returned by the experimental
item tool exclude navigation claims. Neighborhoods preserve recorded grounds,
direction and truthful `has_more` rather than inventing complete graph coverage.

The added preview also adds words; this design does not isolate topology from
extra preview text. It tests the combined initial-entry affordance.

## Execution

- Model: `gpt-6.1-sol`, provider `openai-codex`.
- One independent minimal model/tool-loop context per cell; three matched
  questions, six cells, no repeated sampling or selective answer retries.
- Order: A/B, B/A, A/B. First pair doubles as the real multi-round transport pilot.
- Per trial: explicitly 8 model calls and 12 tool attempts maximum, no provider
  retries; HTTP 20 s / client-close 25 s per call. Observed delta output 4096 bytes,
  completed output 16384 bytes, event/serialized-evidence bounds also enforced.
  These are client/observed safeguards, **not a server token or billing cap**.
- Fresh `-I -B` interpreter outside Git with disposable HOME/Hermes/XDG/Mneme
  paths; no prior chat, kernel, repository history, skills or automatic memory
  receptors. Evaluated loops receive only frozen explicit read-only tools.
- Tool returns are frozen real snapshots, not live MCP calls on every trial.
  The experiment is not native Hermes/Claude-agent validation.
- Preserved runner transport/resolver/replay/launcher safeguards unchanged;
  Hermes transport revision `2237be355906fbe6065ce1815711eee52b2d646e`,
  OpenAI SDK 2.24.0 / httpx 0.28.1. Product baseline `a5c9e13`.

## Observed results

All six planned trials were launched and recorded. Five completed; B on the
continuation question stopped at the preregistered observed-output limit after
successful retrieval. Its answer is censored, **not semantically incorrect**.
No complete answer or missing final-response usage is invented for it.

Reconciliation verified every one of 16 body returns and 8 neighborhood returns
against the frozen data, exact request continuations and initial requests.
There were no rejected tool calls. Both arms opened all question-specific
expected body routes in every trial, including the censored trial.

For the **two fully completed matched pairs only**:

- A: 5 body openings, 3 neighborhood calls, 10 model calls,
  **16,193 provider-reported tokens**.
- B: 5 body openings, 3 neighborhood calls, 10 model calls,
  **18,966 provider-reported tokens**.

The unfinished pair is excluded from that paired answer/usage comparison. Across
all launched cells A and B each made 8 body openings, 4 neighborhood calls and
15 model calls. B's all-launched usage is incomplete because its interrupted
response did not report usage. Raw edge-return counts are not unique-edge counts;
repeated records were deduplicated when measuring opened connection identities.

Parent and final independent raw/semantic review classify all five completed
answers as supported by the bodies and authored relation grounds actually
returned: declared dependency is not timestamp inference, consolidation time is
not occurrence time, limited authorship guidance is not a blanket delegation ban,
and a draft/connected view is not a confirmed persistent metapointer or automatic
engram. Independent review found 5 supported, 0 partial, 0 unsupported and 1
censored. It verified request/response continuations, all body/neighborhood returns,
and exact finals. Its source-fidelity boundary is the frozen corpus, not external
verification of the historical events or a fresh attestation of live-state hashes.

## Interpretation and decision

**No navigation advantage for the extra initial entrance was observed here.**
Both arms used deliberate tools and recovered the relationship grounds. In the
two completed pairs they took the same number of body/neighborhood/model calls;
the extra entrance did not reduce provider-reported token use either. This is
not a statistical estimate or proof the entrance is useless: tiny corpus,
explicit relationship questions and common tool guidance make a ceiling effect
plausible. One censored cell limits answer comparisons further.

Close this bounded pilot without adding ranking, relation kinds or memory layers,
without removing existing working ingress, and without rerunning until a favorable
answer appears. General availability/effectiveness of relations and a larger or
less explicitly cued setting remain open. One deliberate connected-form synthesis
and verified-return metapointer remain separate possible slices, not implemented
by this evaluation or auto-promoted from its answers.

## Verification and publication boundary

- Pre-inference independent SPEC and QUALITY/security review passed exact
  runner/input hashes, including disposable source/snapshot fidelity checks.
- Parent isolated private checkout suite: **431 passed, 7 subtests passed**;
  independent reviewer reran the seven new tests, preflight and censoring probes,
  not the entire suite. This is the experiment checkout's suite, not a new claim
  about product-main runtime code, which is unchanged by this report.
- All 14 protected live-memory/configuration/local-observer file hashes stayed
  unchanged across preparation and runs. No capture, review, relation authorship,
  engram write, host configuration change or gateway restart was needed.
- Full real-memory corpus, expected facts, raw model/tool traces and detailed
  reviews stay in a verified private destination. This public report contains
  methodology and aggregates, not personal memory bodies or exact source routes.

Frozen runner SHA-256:
`9c4e3d563370b9ba8142e94be09173c5dd3f0792a335d24fea0ac4b2a37994bd`.
