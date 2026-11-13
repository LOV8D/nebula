# Nebula — by Asterium Labs

> Test financial-market interventions before they reach the market.
> Formerly Market Wind Tunnel. Repository: [LOV8D/nebula](https://github.com/LOV8D/nebula).

Nebula compares simulated responses to market rules, fees, news and issuer
disclosures. It combines a five-book market engine (EQ, IR, FX, CMD, CRYPTO),
883 persona records (715 LLM-tier, 145 policy, 15 rule, 8 event-source roles),
scenario experiments, evidence records and an offline HTML dashboard.
LLM-tier agents use a model for novel situations and local policies for routine
rounds; 883 records does not mean 883 model calls per round.

**Current scope (2026-11-13):** a runnable research/product prototype operated
through Python commands, with a read-only replay dashboard. There is no deployed
web service, live order execution, always-on daemon or automatic GPU provisioning.
The UI selects between Fed statement and earnings disclosure cases; it does not
launch simulations. Human grounding remains **0%**. Simulated differences are
hypotheses, not estimates of real market impact or price predictions.

Start with [installation](#1-install-from-a-fresh-checkout) and the
[offline quickstart](#2-first-use-view-run-inspect). Continue to
[custom scenarios](#3-run-and-customize-scenarios),
[remote models](#4-configure-and-run-a-remote-model),
[views and exports](#5-rebuild-views-inspect-evidence-and-export-a-brief),
[evaluation](#6-evaluation-and-prospective-question-scoring),
[survey ingestion](#7-persona-fields-and-survey-ingestion) or
[troubleshooting](#8-tests-and-troubleshooting) as needed.

## 1. Install from a fresh checkout

Requirements: **Python 3.10+**, Git and a browser. GNU Make is optional; the core
workflows have Python command equivalents below. No local GPU, Node.js,
JavaScript build step or API key is needed for the offline path.
Installation needs internet access; the mock simulation runs offline afterwards.

```bash
git clone https://github.com/LOV8D/nebula.git
cd nebula
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pyyaml requests
python3 -m runtime.cli --help
```

These are the core dependencies declared in `pyproject.toml`. Run all commands
from the checkout root, with the virtual environment active. On Windows,
activate with `.venv\Scripts\Activate.ps1` in PowerShell and use `python`
instead of `python3` if that is your Python command. Python commands work
without Make. Optional video generation also needs Pillow, ffmpeg and the macOS
`say` voice used by `tools/make_video.py`; it is outside the quickstart.

## 2. First use: view, run, inspect

### View the supplied product demo (no model calls)

Open **`site/dashboard.html`** in your browser. On macOS:

```bash
open site/dashboard.html
```

On Windows/Linux, open the file from your file manager. It is a self-contained
recorded replay; optional Google Fonts fall back to system fonts offline.
If a browser requires HTTP, serve only the generated site directory:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Then visit <http://127.0.0.1:8000/dashboard.html>; stop the server with Ctrl+C.
Do not serve the checkout root, which can contain `.env` credentials.

Choose **Fed statement wording** or **Earnings-opening disclosure** in the case
selector, then use the pages:

| Page | What to do / what it shows |
|---|---|
| Verdict | Compare scenario inputs, per-seed outcomes and attribution limits. |
| Ripple | Switch A/B, play/pause, scrub rounds, jump to the intervention and hover agent cells. This replays recorded decisions. |
| Robustness | Inspect each seed's direction across prompts; earnings has no sensitivity matrix and shows not applicable. |
| Performance | Inspect separate evidence gates, missing tests and record classifications; there is no aggregate validity score. |
| Evidence | Inspect field provenance, missing human data, role-specific cards and source paths. |

The Fed case changes headline text **and the sentiment input**. The earnings
case additionally changes guidance content; its event lands at round 0, so there
is no measurable pre-intervention window. Neither case isolates pure tone.

### Run your first offline experiment

```bash
python3 -m runtime.cli demo --seeds 2 --out runs/scratch/first-demo
python3 -m runtime.cli parity runs/scratch/first-demo/news_demo
python3 -m runtime.cli telemetry runs/scratch/first-demo/news_demo/news_a_s0 --limit 20
python3 -m runtime.cli viewer runs/scratch/first-demo/news_demo/news_a_s0
```

This runs a five-book smoke gate followed by fee, news A/B, circuit-breaker
and earnings experiments, all with the **mock heuristic**. Inspect
`runs/scratch/first-demo/report.md` and open
`runs/scratch/first-demo/news_demo/news_a_s0/viewer.html` for decisions and cards.
`--seeds 2` produces two matched seeds (11 and 112). Runtime depends on hardware;
this is a small CPU workload. Mock results test the pipeline, not LLM behavior.

`make demo` is the standard five-seed variant and writes into
`runs/evidence/demo/`. It replaces matching run directories and reports; use
`--out runs/scratch/<name>` when exploring. Changing `make demo SEEDS=3` has no
effect: use `python3 -m runtime.cli demo --seeds 3`.

### Fresh-checkout data caveat

Git includes manifests, summaries, reports, evaluation records and the bundled
HTML. Bulk `events/intents/marks/trades/violations.jsonl` and real-model response
caches are **gitignored**. Consequently:

- Open the committed HTML immediately; it already embeds the recorded data.
- Rebuild mock logs offline using the commands above.
- Rebuilding real-model logs requires the remote model or an authorized copy of
  the original logs/cache. A new sampled run need not reproduce the old answers.
- `make ui` / `make evaluate` read local logs, not the embedded HTML. On a fresh
  clone they cannot restore full replay or verify missing-log parity. Keep the
  supplied HTML until you have the logs needed to regenerate it.

## 3. Run and customize scenarios

```bash
python3 -m runtime.cli run -s scenarios/baseline.yaml --out runs/scratch/baseline
python3 -m runtime.cli run -s scenarios/fee_high.yaml --seeds 5 --out runs/scratch/fee
python3 -m runtime.cli compare "runs/scratch/fee/*" -o runs/scratch/fee/report.md
```

Copy an existing YAML before editing it. Set `id`, `tag`, `days`,
`rounds_per_day`, `seed`, five `assets` starting values, `mechanism`, `model`
and the `events` list. Each event has a round `t`, headline, numeric sentiment,
reach (`impact`), assets and source. `model: {provider: mock,
model_id: mock-heuristic-v1}` keeps the scenario offline. `--seeds N` adds 101 to
the starting seed for each replication. `--compare-with` on `run` accepts
additional run directories; `compare` only reads existing summaries.

For matched arms, hold population, initialization, mechanism, model, prompt and
seed fixed except for explicitly declared interventions. Check parity before
interpreting differences; list numeric parameter changes as well as text.

Reproduce the earnings **mock** case (overwrites those mock run IDs):

```bash
python3 -m runtime.cli run -s scenarios/earnings_open_a.yaml --seeds 2 --out runs/evidence/earnings_demo
python3 -m runtime.cli run -s scenarios/earnings_open_b.yaml --seeds 2 --out runs/evidence/earnings_demo
python3 -m runtime.cli compare "runs/evidence/earnings_demo/*_s*" -o runs/evidence/earnings_demo/report.md
```

The case UI prefers the real run root if that directory exists. Running mock
arms does not replace the displayed real case automatically; see section 5.

### Real market initialization (optional network access)

```bash
python3 -m runtime.cli snapshot --force
```

This refreshes `config/snapshot.json` from delayed Yahoo data (24-hour cache):
SPY, EUR/USD, gold, BTC and a duration-based 10Y note approximation. It changes
initial levels/volatility only; subsequent prices are simulated. The snapshot
helper overlays scenarios with `use_snapshot: true` when called through the
experiment loader. **The generic `run` command currently loads YAML directly
and does not call that helper.** To run a snapshot-initialized baseline:

```bash
python3 - <<'PYCODE'
from experiments.demo import _load, _panel
from runtime.snapshot import apply_snapshot
from runtime.engine import run_scenario
sc = apply_snapshot(_load('scenarios/baseline_live.yaml'))
run_scenario(sc, _panel(), 'runs/scratch/live-baseline')
PYCODE
```

Fetch failure falls back to static YAML levels with a terminal notice. Inspect
snapshot provenance and the notice before describing a run as market-anchored.

## 4. Configure and run a remote model

Real-model commands make API requests and can incur provider charges. The
recorded production runs use GLM; the historical `vllm_qwen8b` profile name is
still the default, but `.env` can point it at any OpenAI-compatible remote
endpoint. No model is served or GPU started by Nebula.

```bash
make brain-setup
# Without Make: copy .env.example to .env if .env does not exist.
```

Edit **`.env`** locally (never commit a real key):

```dotenv
BRAIN_BASE_URL=https://your-provider.example/v1
BRAIN_API_KEY=your-provider-key
BRAIN_MODEL=your-provider-model-id
BRAIN_MAX_WORKERS=8
```

Use the exact base URL (including `/v1` where required) and model ID supported
by your provider. Existing shell environment variables override `.env`.
For `brain` and `demo2`, precedence is CLI `--base-url` > environment/`.env` >
`config/models.yaml` profile. `BRAIN_MAX_WORKERS` controls their concurrency;
sensitivity and real multiday currently hardcode eight workers.

```bash
python3 -m runtime.cli brain
python3 -m runtime.cli demo2 --seeds 2
python3 -m runtime.cli parity runs/evidence/demo2/news_demo
```

`brain` probes the endpoint and requests one persona decision. `demo2` runs
smoke + flagship news A/B and overwrites matching IDs in `runs/evidence/demo2/`.
Its `llm_cache.json` stores raw responses shared across arms. Preserve the cache
with the run if replay matters; do not publish it without reviewing its inputs.

Additional experiments:

```bash
python3 -m runtime.cli sensitivity --prompts p1 p2 --seeds 2
python3 -m runtime.cli multiday --days 5 --seeds 3
# Remote model (billable):
python3 -m runtime.cli multiday --days 5 --seeds 1 --real
```

Sensitivity defaults to `BRAIN_MODEL` (historically GLM-only); `--models` accepts
explicit model IDs. It replaces matching runs under `runs/evidence/sensitivity/`
and writes `results.json`, `parity.json`, `report.md`. Multiday replaces matching
runs under `runs/evidence/multiday/`; its default is mock. Neither CLI exposes
`--out`. Back up previous evidence before replacing it. `--real` needs all three
remote connection variables.

To rerun the **earnings** arms on the remote model (also billable), use the
orchestrator after a successful `brain` check:

```bash
python3 - <<'PYCODE'
from runtime.cli import _apply_env, _profile
from experiments.demo import run_demo
model = _apply_env(_profile('vllm_qwen8b'))
run_demo(seeds=2, out_root='runs/evidence/earnings_demo_real',
         model_override=model,
         experiments={'earnings_demo': ['earnings_open_a', 'earnings_open_b']})
PYCODE
```

This replaces matching runs under `runs/evidence/earnings_demo_real/earnings_demo/`,
the real root used by the case selector. `evaluation/earnings_real.py` only
compares existing summaries at its `MOCK`/`REAL` paths; it does not run a model.

### Test the API path without a model

In a separate checkout/terminal with no real brain credentials, start the stub:

```bash
python3 tools/fake_vllm.py --port 8000
```

In the second terminal, activate the environment and run:

```bash
BRAIN_BASE_URL=http://127.0.0.1:8000/v1 BRAIN_API_KEY=EMPTY BRAIN_MODEL=fake-qwen-8b python3 -m runtime.cli demo2 --profile fake8b
```

These POSIX inline environment assignments explicitly override `.env`; on
PowerShell set the three `$env:BRAIN_*` values first. The stub is a keyword
heuristic, **not an LLM**. It overwrites the default demo2 outputs: use a separate
checkout to preserve real evidence. Stop it with Ctrl+C.

## 5. Rebuild views, inspect evidence and export a brief

With the necessary recorded logs available:

```bash
make ui
make evaluate
python3 evaluation/decision_brief.py news_wording
python3 evaluation/decision_brief.py earnings_disclosure
```

Without Make, use `python3 -m runtime.cli ui` and
`python3 -m runtime.cli evaluate`. Outputs:

| Output | Purpose |
|---|---|
| `site/dashboard.html` | Self-contained case dashboard; replaces the previous bundle. |
| `site/dashboard.data.json` | Inspectable source payload (gitignored). |
| `site/performance.json` | Evidence-gate scorecard; regenerates from local evidence. |
| `runs/scratch/<case_id>/decision_brief.md` | Five-section brief from the same case object: question, input differences, per-seed results, limits, next test. |

Case IDs and run locations are defined in **`ui/cases.py`**. It selects the real
root when present, otherwise the mock root, by directory existence rather than
log completeness. Ensure both arms/seeds have matching bulk logs. To use other
run roots, edit the case configuration. **Known limitation:** `ui`/`evaluate`
accept `--ab-root` and `--sensitivity`, but current case collection uses the
paths in `ui/cases.py`; those flags do not reliably switch the default case.
`--replay-seed` is supported by `ui` (the selected seed must exist in each case).
`-o` sets the output path for either command.

Inspect one run without rebuilding the dashboard:

```bash
python3 -m runtime.cli provenance
python3 -m runtime.cli card runs/scratch/first-demo/news_demo/news_a_s0
python3 -m runtime.cli telemetry runs/scratch/first-demo/news_demo/news_a_s0 --agent retail_direct-0000 --show-pass
python3 -m runtime.cli viewer runs/scratch/first-demo/news_demo/news_a_s0
```

Every run records a five-tuple (population, intervention, mechanism, model,
seed), code hash and prompt hash in `manifest.json`; `summary.json` contains
metrics and usage. Intents are **JSONL**, with `provider`, `model`,
`prompt_version`, `prompt_sha8` — not Parquet/Arrow. Cards compare the run's
population hash with the current panel and warn on mismatch. They reconstruct
net fills, not a complete historical account statement.

Parity compares pre-intervention intents and prices. Missing logs mean
**unknown**; an event at `t=0` means **not measurable**, not a pass. A command's
exit code alone is insufficient: the parity CLI exits nonzero for explicit
failures but can exit zero on unknown. Read each verdict.

## 6. Evaluation and prospective question scoring

The evidence contract is `evaluation/benchmark_v0.json`; records live in
`evaluation/results.json`. Internal/synthetic checks are distinct from verified
external evaluations. Clean engineering checks cannot establish real-market
validity. The current GLM sensitivity rerun is clean but its direction is mixed
on p1 and inverted on p2; the old positive wording conclusion is not robust.
Historical intervention, human holdout and prospective evidence remain separate
gates. Use the current Performance page and records, not old report headlines.

Additional entry points (run from the checkout root):

| Command | Behavior |
|---|---|
| `python3 -m evaluation.market_realism` | Descriptive checks on local mock/flagship logs; no external validity claim. |
| `python3 -m evaluation.population_fidelity` | Compare synthetic priors with aggregate reference moments; not human grounding. |
| `python3 -m evaluation.tsp_sim_arm` | Rerun the ten-seed mock tick-grid mechanism comparison; writes under `runs/evidence/tsp_sim/`. |
| `python3 -m experiments.tick_size_pilot --dry-run` | Synthetic estimator/scoring check. Real historical data is a separate task. |

These evaluation modules default to no registry append; some still write run or
report artifacts. `--apply` on evaluation modules appends eligible records to
`evaluation/results.json`. Read the module before registering a result.
For historical sample requirements and real-data execution, read
[`docs/tick-size-pilot-plan.md`](docs/tick-size-pilot-plan.md).

For issuer question anticipation, first prepare local `case.json`,
`predictions.jsonl` and later `outcome.json` using the schemas in
[`docs/issuer-questions-protocol.md`](docs/issuer-questions-protocol.md):

```bash
python3 -m evaluation.issuer_questions freeze case.json predictions.jsonl freeze_manifest.json
python3 -m evaluation.issuer_questions score case.json freeze_manifest.json outcome.json predictions.jsonl
```

The freeze validates at most five ranked, sourced predictions (or abstentions)
and hashes the inputs/materials. Scoring verifies hashes and reports hit rate
and topic coverage. Missing outcome is pending. A local hash/timestamp is not
independent proof of pre-event existence; fixture results are not external
validation. Anticipating questions says nothing about market reactions.

## 7. Persona fields and survey ingestion

```bash
python3 -m runtime.cli fields
python3 -m runtime.cli survey
python3 -m runtime.cli ingest tests/survey_example_answers.json
```

`fields` prints the current 17-field schema and synthetic-panel consistency checks.
`survey` writes `site/investor_survey.html` and `.json` (v2: closed values,
branching, ordinal scales and optional separately stored “other” text).
The static HTML is a questionnaire template, not a hosted submission service.
The example answers are fixtures, not real respondents.

`ingest ANSWERS.json` validates consent and answers, then writes
`personas/patches/<stem>.patch.dryrun.json`. **Dry run still writes a patch file.**
`--apply` only removes `.dryrun` from its filename; neither mode updates the
panel. Accepted values carry `self_report`, granted consent and `calibration`
split, never training status. Wiring real responses into a panel is a separate
step. Keep private answers and patches out of Git; `personas/patches/` is not
blanket-ignored. `panel --out PATH` regenerates a panel; back up any custom panel
before using `make panel`, which overwrites `personas/panel_v3.json`.

## 8. Tests and troubleshooting

```bash
make test
make help
```

Without Make (POSIX shell):

```bash
for test_file in tests/test_*.py; do python3 "$test_file" || exit 1; done
```

Tests are offline; some artifact-dependent checks explicitly skip when logs
are absent. A passing/skipped suite does not recreate or validate missing data.

| Symptom | Action |
|---|---|
| `No module named yaml` / `requests` | Activate `.venv`, install the two dependencies using that interpreter. |
| `No module named runtime` | Change to the checkout root; this workflow uses local source and data paths. |
| `make` unavailable | Use the Python commands above. |
| Empty replay / parity unknown after cloning | Bulk JSONL is not in Git. View the committed HTML or regenerate/restore the relevant logs. |
| Model preflight fails / 401 / unknown model | Check base URL, key and model ID locally; `brain` makes a real chat probe. Do not paste credentials into issues. |
| 429, timeouts, fallback decisions | Inspect usage errors and per-intent provider; reduce `BRAIN_MAX_WORKERS` for demo2. A fallback-heavy run is not clean model evidence. Sensitivity/multiday concurrency needs a code change. |
| Unexpected model with `--profile fake8b` | Shell/`.env` settings override the profile; use the explicit stub environment shown above. |
| Old numbers after a rerun | Rebuild the dashboard after ensuring its case roots point to the new logs, then reopen/refresh the HTML. |
| Card population mismatch | Restore the matching panel or rerun; do not interpret current persona fields as belonging to an old run. |

`make clean` deletes **all `runs/scratch/`**, including local briefs and TSP data
cache. It keeps `runs/evidence/`, credentials and generated site files. Demo,
demo2, sensitivity and multiday replace matching run IDs; preserve any evidence
or response cache you need before rerunning. `make report` rebuilds only mock
per-group comparison tables, not every top-level report or the dashboard.

## 9. Source map

| Location | Responsibility |
|---|---|
| `runtime/` | World state, agents, LLM gateway, execution constraints, matching, recorder, metrics, snapshots and CLI. |
| `experiments/` | Demo, sensitivity, multiday, parity and historical Tick Size Pilot orchestration. |
| `evidence/` | Field-level provenance, survey schema and ingest. |
| `evaluation/` | Benchmark contract, records, direction semantics, scorecard, realism/population/tick checks, issuer questions and decision briefs. |
| `ui/cases.py` | Case definitions, attribution limits and run roots. |
| `ui/collect.py`, `ui/bundle.py`, `ui/app/` | Recorded-data collection and HTML/CSS/JS bundle. |
| `scenarios/`, `personas/`, `config/` | Experiment YAMLs, synthetic panel and model/snapshot configuration. |
| `runs/evidence/` | Versioned summaries/manifests/reports; local ignored bulk logs/cache. |
| `runs/scratch/` | Disposable local experiments and exports. |
| `site/` | Generated dashboard, survey and performance artifacts. |
| `docs/` | Design history and evaluation protocols; older plans may predate the build. |
| `tools/`, `tests/` | Stub endpoint, video generator and offline checks. |

Open this checkout with `code .` if VS Code's shell command is installed, or
use File → Open Folder. Shared strategy/collaboration notes live in the parent
Obsidian workspace and are not part of a standalone GitHub clone.

## Historical decisions

These retain the original design history. For current behavior and model
configuration, follow the operating instructions above.

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

## Boundaries

Model output and rationale text are audit material, not empirical evidence.
No point predictions, real-market effect sizes, investment advice or live
execution. Fair baselines and model/prompt/seed sensitivity remain required;
unknown, mixed and failed results must stay visible.
