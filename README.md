# Nebula — by Asterium Labs

> behavioural A/B simulation for financial-market interventions.
> Formerly "Market Wind Tunnel"; the wind-tunnel metaphor survives in the docs.

US-market behavioral simulation & stress-testing demo: a trigger-driven, resident
agent-cluster runtime that snapshots real market data as its initial environment,
runs a multi-asset market (equities, rates; FX / commodity / crypto in v1), and
delivers **relative differences across intervention variants** — never point
predictions of price direction.

**Status: first end-to-end build runs (2026-10-16).** 883-agent panel, five
asset books (EQ, rates, FX, commodity, crypto), batch call auctions with a
persistent book, circuit breakers, attention gating, three-tier cognition,
per-decision provenance, deterministic runs. The Tier-A brain currently
defaults to the offline `mock` heuristic provider; pointing a scenario at a
vLLM endpoint is a one-line change (`config/models.yaml`). Plan of record:
[`docs/demo-plan-v2.html`](docs/demo-plan-v2.html) (rev 2.1). Latest demo
artifacts and honest caveats: [`runs/evidence/demo/report.md`](runs/evidence/demo/report.md).
The shared rules that govern all work here are in [`../AGENTS.md`](../AGENTS.md).

> **Current integrity state (2026-10-31).** The real-brain flagship was rerun
> after the gateway race fix and both same-seed pairs now pass pre-intervention
> parity. The older GLM/DeepSeek sensitivity matrix still fails parity and is
> not robustness evidence; it must be rerun before any sensitivity claim is
> quoted. Passing parity validates the A/B pipeline only — not market realism,
> behavioral validity or real-world effect sizes.

## Quickstart — the demo action

One command runs the whole showcase (panel check → smoke → three wind-tunnel
experiments × 5 seeds → comparison reports → headline summary), ~11 s offline:

```bash
make demo                     # or: python3 -m runtime.cli demo
```

Terminal output ends with the headline readout (direction & ranking only);
full write-up lands in `runs/evidence/demo/report.md`, per-group tables in
`runs/evidence/demo/{fee_demo,news_demo,cb_demo}/report.md`. Use `--seeds N` to change
replication (`make demo SEEDS=3` not wired — use the module form directly).

### Sensitivity, multi-day, and live snapshots (steps 1–3, 2026-10-21)

```bash
python3 -m runtime.cli snapshot --force      # real market levels -> config/snapshot.json (24h cache)
python3 -m runtime.cli sensitivity           # model x prompt matrix on the news A/B (BP red line)
python3 -m runtime.cli multiday --days 5 --seeds 3        # mock; add --real for the remote brain
```

- **snapshot**: `scenarios/*_live.yaml` carry `use_snapshot: true` — asset
  levels and vol come from real trigger-time data (SPY, EURUSD, gold, BTC,
  10Y via Yahoo's public endpoint, documented approximations in
  `config/snapshot.json` provenance). Fetch failure falls back to static
  levels so the demo stays runnable offline.
- **sensitivity**: runs the A/B across models x {p1 neutral framing, p2 "behave
  like a real human"} and reports whether the qualitative ranking survives.
  GLM-only by default (user decision 2026-10-22; the deepseek legs were
  error-polluted and sign-unstable — see report footnote). Instability is a
  deliverable (BP red line), written up in `runs/evidence/sensitivity/report.md`.
  A row counts as stable only when **every seed** agrees in sign (a two-seed
  mean can hide a flipped seed); per-seed values and per-pair parity are in
  the report, `results.json` and `parity.json`.
- **multiday**: N-day A/B with per-day EQ returns and a behavioral-drift
  check (monotone wake/net-direction drift = persona identity failure,
  BP layer 2).

### Dashboard (the product view)

```bash
make ui                                        # -> site/dashboard.html, open in any browser
```

One self-contained page (no server, no network needed), assembled from
recorded runs — no simulation is re-executed. Four questions in reading
order, plus an appendix:

1. **Verdict** — how much did the wording change the market? Direction
   headline across seeds, A/B tiles, both wordings quoted, EQ paths for every
   seed plus seed means, and the **parity** status: an amber band marks where
   the arms already differ before the statement.
2. **Ripple** — who reacted first, and who pushed? The 883 agents as a grid
   replaying the recorded decisions round by round (A or B arm, play / scrub /
   jump to the intervention, hover for identity), a decisions-per-round
   timeline, the round's decision stream, net direction per class (A vs B),
   and the five books as small multiples on their own scales.
3. **Robustness** — does it hold across seeds, models, prompts? One dot per
   seed pair (row means are ticks, never instead of the dots), hollow dots
   for pairs that fail parity, non-GLM rows greyed per the 2026-10-22 decision.
4. **Performance** — the evaluation system and current-product assessment:
   eight independent gates, explicit evidence/limits/next tests, fair baseline
   arms and planned benchmark cases. There is deliberately no aggregate score.
5. **Evidence** (appendix) — panel provenance coverage, role-aware agent
   cards, red lines, reproducibility contract, data sources.

Sources are overridable: `--ab-root`, `--sensitivity`, `--replay-seed`, `-o`.
The page itself is hand-written in `ui/app/` (HTML/CSS/JS); `ui/collect.py`
gathers the data and `ui/bundle.py` inlines both into one file.

The same Performance assessment is available as machine-readable JSON:

```bash
make evaluate                                  # -> site/performance.json
```

The stable contract is `evaluation/benchmark_v0.json`; completed external
evaluations are appended to `evaluation/results.json`. An absent benchmark is
always `NOT RUN`, never silently counted as a pass. The current honest state is
**ENGINEERING-VERIFIED / MARKET-UNVALIDATED**: the clean flagship proves the
system can run and audit one comparison, while historical intervention,
human holdout, prospective and customer-utility benchmarks remain unrun.

### A/B parity

```bash
make parity                                    # flagship pairs; exit 1 on any failure
python3 -m runtime.cli parity runs/evidence/demo/news_demo
```

An A/B is only an A/B if both arms are identical until the intervention. For
every same-seed pair, `experiments/parity.py` compares each decision (agent,
asset, side, size, urgency) and each price before the first round at which the
arms' events differ, and names the first divergent round and the largest gap.
The demo report, the sensitivity report and the dashboard all show it; a
failing pair is flagged, never silently averaged in.

Individual pieces:

```bash
python3 -m runtime.cli panel                                   # regenerate the 883-agent panel
python3 -m runtime.cli run -s scenarios/baseline.yaml          # one run (offline, ~0.3 s/sim-day)
python3 -m runtime.cli run -s scenarios/fee_high.yaml --seeds 5 --out runs/scratch/fee
python3 -m runtime.cli compare "runs/scratch/fee/*" -o runs/scratch/fee/report.md
make smoke | make report | make test | make clean              # other actions (make help)
```

### Closed-value persona fields & the investor survey

The behavioural parameters are continuous; real people answer in words. This
layer adds the closed-value vocabulary a survey can map onto.

```bash
python3 -m runtime.cli fields                        # 16-field schema + panel consistency check
python3 -m runtime.cli survey                        # -> site/investor_survey.html (+ .json)
python3 -m runtime.cli ingest ANSWERS.json           # validate -> evidence patch (dry-run)
python3 -m runtime.cli ingest ANSWERS.json --apply   # patch without the .dryrun suffix
```

- **fields**: 5 groups / 16 closed fields (account, attention, behaviour,
  constraints, wealth band). Dependency rules reject only logically
  impossible combinations; rare-but-real combos are flagged, never deleted
  (BP principle). `synthesize` derives each retail agent's bands from its
  continuous parameters so the two layers can never disagree; the panel
  check fails the build on any violation.
- **survey**: a static consent-first questionnaire (closed answers only, no
  free text), printable as JSON for online survey platforms.
- **ingest**: validates answers against the closed sets and dependency
  rules, then writes an evidence patch (`self_report`, consent `granted`,
  split `calibration` — never train) under `personas/patches/`. Patches are
  the deliverable; wiring them into a panel is a separate explicit step.
  See `tests/survey_example_answers.json` for the four handled cases
  (clean / impossible / rare-but-real / no consent).


## demo2 — the real 8B brain

`demo2` is the same showcase with the cognitive tier pointed at the decided
brain (self-hosted 8B-class via vLLM) instead of the mock. It runs the
flagship news-wording A/B, writes `runs/evidence/demo2/` + its `report.md`,
and adds two things the mock path doesn't have:

- **preflight gate** — pings the endpoint first and tells you how to start it;
- **`llm_cache.json`** — raw model responses keyed by prompt hash. Real-model
  sampling (temperature > 0) is otherwise not replayable; with the cache,
  re-running the same seeds replays identical decisions, and prompts shared
  across seeds/scenarios are paid for once (cross-run amortization, plan §8);
- **concurrent dispatch** — all LLM decisions of a round fire in parallel
  through a bounded thread pool (`BRAIN_MAX_WORKERS` in `.env`, default 8).
  Every agent keeps its own RNG substream, so runs stay reproducible.
  Benchmarked against a latency-injected stub: 24 calls 19.6 s serial → 2.5 s
  at 8 workers (**7.8× linear**); with the real ~12 s/call endpoint, event
  rounds go from minutes to seconds.

The brain is **remote** — nothing is served from this machine:

```bash
make brain-setup        # creates .env from .env.example if missing
# edit .env:
#   BRAIN_BASE_URL=http://your-gpu-host:1526/v1
#   BRAIN_API_KEY=EMPTY-or-your-key
#   BRAIN_MODEL=Qwen/Qwen3-8B
make brain-check        # preflight + one sample persona decision
make demo2              # news A/B x 2 seeds -> runs/evidence/demo2/
python3 -m runtime.cli demo2 --seeds 3      # more replication
```

`.env` is the single place for credentials (kept out of search via
.zcodeignore); precedence: `--base-url` flag > `.env` > `config/models.yaml`
profile. One-off override: `python3 -m runtime.cli demo2 --base-url http://host:1526/v1`.
No GPU reachable? `make fake-brain` starts `tools/fake_vllm.py`, a stub
OpenAI-compatible server (keyword heuristics, NOT a model) that exercises the
entire real-brain code path end to end: `python3 -m runtime.cli demo2 --profile fake8b`.
Brains are configured in `config/models.yaml` (profiles: `vllm_qwen8b`,
`deepseek`, `fake8b`, `mock`); every run's manifest records which one was used.

**Reading demo2 results:** compare them against the mock run
(`python3 -m runtime.cli demo`) — where the two brains' qualitative rankings
diverge, that divergence is itself a deliverable (model sensitivity, BP red
line), not a nuisance.

## Opening this repo in VS Code

Terminal (one-liner, after VS Code's `code` command is installed — see below):

```bash
code "/Users/watson/Desktop/obsidian/AI for SS/wind_tunnel"
```

If `code` is not found: open VS Code once, press `Cmd+Shift+P`, run
**"Shell Command: Install 'code' command in PATH"**, then retry. No terminal?
In VS Code: `File → Open Folder…` (`Cmd+O`) and select the `wind_tunnel` folder.

The plan document is HTML — open it in any browser
(`open docs/demo-plan-v2.html`), or preview inside VS Code with an HTML
preview extension; charts are inline SVG rendered by a few lines of JS, so a
plain "open in browser" is the most reliable view.

## Which LLM is the agent brain?

- **Now:** the runtime is built and runs end to end — `make demo` (mock brain,
  offline) and `make demo2` (real remote brain via an OpenAI-compatible
  endpoint configured in `.env`). The plan of record's self-hosted 8B
  (Qwen via vLLM) remains the target deployment; any OpenAI-compatible
  endpoint works today. The gateway keeps the model AND prompt swappable per
  run (model/prompt sensitivity is a deliverable, not a nuisance).
- **After the build (how to check, three places):**
  1. `runs/evidence/<experiment>/<run_id>/manifest.json` — the five-tuple run manifest
     (population × intervention × mechanism × **model** × seed) records the
     exact model + prompt version for every run, plus `code_hash`, a digest of
     `runtime/`, `experiments/` and `evidence/` (the prompt templates live in `llm.py`, so the hash covers
     prompts as well — `runtime_version` alone cannot tell two builds apart);
  2. the gateway config (`config/models.yaml`) — what is currently routable
     (vLLM endpoint, API providers) and the routing thresholds;
  3. every recorded Intent row in the Parquet/Arrow logs carries
     `model_id` + `prompt_version` in its provenance — so you can audit which
     brain produced which order, per decision, post hoc.

## Read-only views (2026-10-22)

Three commands render what is already in the evidence pack. Nothing here
computes a new result; they exist so a reviewer can watch decisions arrive and
open any single agent.

```bash
python3 -m runtime.cli provenance                       # evidence coverage of the panel, per attribute
python3 -m runtime.cli telemetry runs/evidence/demo/news_demo/news_a_s0 --limit 40
python3 -m runtime.cli card runs/evidence/demo/news_demo/news_a_s0            # one card per role
python3 -m runtime.cli viewer runs/evidence/demo/news_demo/news_a_s0          # -> that run's viewer.html
```

- **provenance** — every persona attribute now carries its own evidence record
  (source, evidence kind, confidence, consent, split) instead of one template
  string per agent. Attributes a real-person source would fill and we have
  none for stay `None`, are listed in `unknown_fields`, and are counted here.
  Today the honest headline is **0% of attributes grounded in real people**;
  the command prints the twelve attributes that Phase-2 data would close.
- **telemetry** — the decision stream, `obs -> intent -> fill`, one line per
  recorded decision with the brain that produced it. No reward column: this
  runtime has no reward signal, and borrowing the word would be a lie.
- **card / viewer** — role-aware agent cards: investors get holdings, market
  makers get inventory, mandated vehicles get their rulebook, and event
  sources get the headlines they published. `viewer` writes a single
  self-contained HTML file next to the run: stream on the left, cards on the
  right, five-tuple in the header.
- Cards join a run to the panel on disk. A run records only its population
  *hash*, so the viewer compares hashes and prints a loud mismatch warning
  rather than rendering attributes that may belong to a different agent.

## Decisions log

| Date | Decision |
|---|---|
| 2026-10-31 | Product performance uses independent evidence gates, not a composite score. Engineering integrity cannot substitute for market, behavioral, prospective or decision-utility validity; unrun tests display as `NOT RUN` |
| 2026-10-29 | Repo split into `runtime/` (simulator core), `experiments/` (demo, sensitivity, multiday, parity), `evidence/` (provenance, fields) and `ui/` (viewer, dashboard data, hand-written app, bundler). Runs split into committed `runs/evidence/` and gitignored `runs/scratch/`; generated pages go to `site/`. Sensitivity run dirs use `__` instead of `|` |
| 2026-10-29 | Concurrent LLM dispatch resolves each memo key once per round, owned by the first job in order — never by thread timing. A same-seed A/B pair that is not identical before the intervention fails **parity** and is flagged everywhere it is reported |
| 2026-10-22 | `persona_id` carries the **full class name** (`retail_direct-0000`). The old 6-char prefix made `retail_direct` and `retail_advised` collide on 60 ids; accounts and RNG streams are keyed by that id, so the advised twin overwrote the direct one. Runs made before this fix have unreliable per-agent attribution for those 60 ids — aggregate flows still stand, single-agent cards from those runs do not. `write_panel` now refuses a panel with duplicate ids |
| 2026-10-22 | Persona provenance is **per attribute**, with closed vocabularies for evidence kind, confidence, consent and split; attributes without evidence stay unset and are counted rather than filled in |
| 2026-10-16 | Demo panel ≤ **1000** agents → **883** (715 LLM personas / 145 compiled policies / 15 rule / 8 meta); weights coarsely aligned to market shares |
| 2026-10-16 | Agent brain: **self-hosted 8B-class** (Qwen, vLLM, AWQ) |
| 2026-10-16 | Compute: **GPU** (loaded on trigger, not resident) |
| 2026-10-16 | Scope: **multi-asset, all five books live in v0** (EQ, IR, FX, CMD, CRYPTO) |
| 2026-10-16 | First headline scenario: **open** (fee change vs Fed-wording A/B vs circuit-breaker magnet) |
| 2026-10-16 | Phase-2 real-person data source: **not locked**; persona schema stays locale-agnostic |
| 2026-10-16 | Repo language: **English only** (v1 Chinese plan archived outside the repo) |

## Layout

```text
wind_tunnel/
├── README.md · Makefile · pyproject.toml   # `make help` lists every action
├── config/models.yaml        # LLM gateway profiles (mock / vllm_qwen8b / deepseek / fake8b)
├── runtime/                  # the simulator core
│   ├── engine.py             # world state, round loop, circuit breakers
│   ├── matching.py           # batch call auction + persistent book
│   ├── agents.py             # attention gate, Tier-B policies, Tier-C rules
│   ├── llm.py                # gateway: mock + OpenAI-compatible, memo, cache, metering
│   ├── personas.py           # archetypes -> weighted panel
│   ├── execution.py          # Intent -> legal Order + validators
│   ├── recorder.py           # JSONL evidence pack + five-tuple manifest + code hash
│   ├── metrics.py            # stylized facts, event windows, comparisons
│   ├── snapshot.py           # real market levels as the initial environment
│   ├── paths.py              # every default location on disk
│   └── cli.py                # all commands (`python3 -m runtime.cli --help`)
├── experiments/              # orchestration on top of runtime/
│   ├── demo.py               # mock showcase and demo2 (real brain)
│   ├── sensitivity.py        # model x prompt matrix
│   ├── multiday.py           # N-day A/B + drift checks
│   └── parity.py             # same-seed arms identical before the intervention?
├── evidence/                 # where persona data comes from
│   ├── provenance.py         # per-attribute evidence records + coverage
│   └── fields.py             # closed-value fields, survey, ingest
├── evaluation/               # benchmark contract, append-only results, scorecard
│   ├── benchmark_v0.json     # eight gates, baselines, fairness contract, planned cases
│   ├── results.json          # external evaluation registry (empty until actually run)
│   └── scorecard.py          # conservative assessment from recorded evidence
├── ui/                       # read-only views
│   ├── viewer.py             # per-run stream + role-aware agent cards
│   ├── collect.py            # dashboard data + derived evaluation status; no simulation
│   ├── app/                  # the dashboard itself: index.html, style.css, app.js
│   └── bundle.py             # data + app -> one self-contained file
├── personas/panel_v3.json    # the generated 883-agent panel
├── scenarios/*.yaml          # baseline, fee x2, news A/B, circuit-breaker on/off
├── runs/
│   ├── evidence/             # committed: demo, demo2, sensitivity, multiday, live_test,
│   │                         #   legacy_2026-10-19 (pre-id-fix runs, kept for history)
│   └── scratch/              # gitignored: smoke runs, video frames; `make clean`
├── site/                     # generated: dashboard.html, performance.json, survey artifacts
├── docs/                     # human-written: plan of record, MatrAIx study, explainer.mp4
├── tools/                    # make_video.py, fake_vllm.py (stub endpoint, not a model)
└── tests/                    # `make test`: gateway, parity, dashboard, evaluation, prompts
```

## Glossary

- **Daemon** — a long-lived background process that is not attached to any
  terminal session. It starts once, then waits for events (timers, webhooks,
  messages) instead of waiting for a user to type a command; think `nginx`,
  `sshd`, or the Docker daemon. In this project the *wind-tunnel daemon* is the
  resident runtime: it holds state and caches (personas, compiled policies),
  listens for triggers, and on trigger executes snapshot → compile → run →
  archive. Keeping it resident is what lets scenario variant #2 reuse variant
  #1's warm caches. It is CPU-only while idle; the GPU mounts only during runs.
- **Tier A / B / C** — the three cognition tiers: LLM persona / compiled
  policy / pure rule. See plan §3.2.
- **Intent** — the structured decision object an agent emits (asset,
  direction, size, urgency, rationale). Only the deterministic execution
  wrapper converts Intents into legal orders; the LLM never quotes prices.
- **Run manifest** — the five-tuple (population × intervention × mechanism ×
  model × seed) that uniquely identifies a trial; same tuple ⇒ reproducible run.

## Boundaries (inherited from the BP)

Model output is not evidence. No point prediction, no investment advice, no
execution. Multi-model × multi-prompt sensitivity is part of the deliverable.
Demo-stage market results are pipeline validation only.
