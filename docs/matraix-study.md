# MatrAIx study — what to borrow, what not to (2026-10-22)

Companion deep-dive (Chinese, workspace root):
`../../05_MatrAIx对标与wind_tunnel进度对齐_2026-10-22.md` — their persona
pipelines, the four labelled human sources (Wikipedia biographical, Amazon
reviews behavioral, Stack Overflow technical, consented self-reported survey),
a live teardown of the playground UI, and the Codex code review that caught
this repo's p1/p2 prompt-selection bug (fixed 2026-10-21, matrix rerunning).
This file is the repo-side English summary; the borrow/reject verdicts agree.

Sources: [github.com/MatrAIx-ai](https://github.com/MatrAIx-ai) (3 repos),
[matraix.ai](https://matraix.ai/), [HF org MatrAIx2026](https://huggingface.co/MatrAIx2026),
[paper 2608.04205](https://arxiv.org/abs/2608.04205). Labels: 【fact】= stated
by them; 【claim】= company-reported, unverified; 【judgment】= ours.

## What MatrAIx actually is (facts first)

- **Not a model.** "MatrAIx-Persona-8B" (2.1k stars, MIT) is population-scale
  persona-driven **evaluation infrastructure**: simulated users as LLM agents
  (driven by external APIs) run against products in four environments —
  Survey, AI Chatbot, Web, OS/App. No checkpoint ships.【fact】
- **Persona data in three layers** 【fact】: *human* (grounded), *extracted*,
  *synthetic* attributes across "demographic, behavioral, professional,
  cognitive, contextual dimensions" — a shared schema of 1,290 categorical
  dimensions. Built with "dependency-aware synthetic generation +
  evidence-aware human grounding."
- **The numbers telescope** 【fact】: 8.3B = theoretical persona space (private,
  by request = lead-gen); Persona 1M = quality-filtered public coreset
  (599,847 human-grounded + 400,000 synthetic); ~200 personas ship in-repo.
- **AgentPersonaBench** 【fact】: 2,460 tasks, 867 traits, 3,865 checks across
  the four surfaces; 78.5% of checks deterministic (option IDs, DOM state,
  files on disk); 20 model arms from 8 vendors under one harness; tasks frozen
  with SHA-256 manifest. Headline findings: traits hold in surveys but drop
  when the model must *act* (gpt-5.6-luna: 85.7% survey → 37.9% across all
  surfaces); chat pressure is the hardest surface; multi-trait tasks trail
  single-trait by up to 31 points.
- **Marketing**: "Simulate before reality" (Matrix pun); WHO/WHERE/WHAT →
  evaluation-results framework diagram; four concrete scenario tiles; one
  customer testimonial on the homepage; a numbers band (8.3B corpus / 1,290
  attributes / 1,000+ applications); disclaimer framing simulation as
  "exploration, stress testing, hypothesis generation — not a replacement
  for evidence from real people."【fact/claim mix】
- Team is Harvard-led; community funnel = Discord + onboarding form + three
  contribution teams (Persona / Application / Environment).【fact】

## What to borrow — technical

1. **Provenance as a three-type label** (human / extracted / synthetic) on
   persona fields. Our cards already carry per-field source+confidence; typing
   the *layer* is a cleaner disclosure format and directly comparable to
   theirs. Cheap change, high auditability.【judgment】
2. **APB's survey-vs-action gap validates our behavior-calibration stance.**
   Their own benchmark shows persona traits survive questionnaires far better
   than they survive *doing things*. Our BP position — calibrate on account
   behavior (what people did), not on interviews (what people said) — is
   consistent with and now citable to their evidence.【judgment】
3. **Multi-attribute compounding difficulty (−31pp) is a design warning**:
   don't expect every persona dimension to steer every decision. Keep fields
   scenario-derived (BP principle), keep decision prompts focused on the few
   dimensions the intervention touches.【judgment】
4. **Per-task deterministic verifiers, one harness, N model arms, cost per
   task.** Our validators + sensitivity matrix are the same shape; concrete
   upgrades: (a) add a $/combo column to the sensitivity report from usage
   metering; (b) freeze scenario sets with checksums in the run manifest;
   (c) formalize "one verifier per scenario config" as the BP already
   specifies.【judgment】
5. **Telescoping numbers honestly**: "represents N people / M instances /
   K archetypes" instead of one flat agent count — same honesty structure as
   their 8.3B/1M/200 pyramid, applied to our weighted-panel design.【judgment】

## What to borrow — marketing / UI

1. **One product-level framework diagram**: WHO (population) × WHERE
   (environment) × WHAT (intervention) → relative risk differences. Our plan
   diagrams are engineering-layered; the demo report needs one
   decision-maker-facing page.【judgment】
2. **Concrete scenario copy instead of category names**: not "fee-change
   scenario" but "理财费率上调 30bps 上线前一天，先看哪些客户会走" — their
   four tiles all name the buyer's exact situation.【judgment】
3. **Numbers band**: 883 agents · 5 books · real trigger-time snapshot ·
   per-order provenance · bit-reproducible — our quantified trust anchors,
   arranged as one strip.【judgment】
4. **The disclaimer-as-positioning move**: they put "not a replacement for
   real people" on the README and homepage; our red lines are stricter and
   should be equally visible (they already are in reports — keep it).【fact→
   already aligned】
5. **Playground**: they ship a local GUI (localhost:5173) + job recipes
   alongside the CLI. Minimal-cost equivalent for us: after each demo run,
   auto-generate a static HTML dashboard (price paths, intent flow, cost
   meter) into the run dir — no server, openable anywhere.【judgment】
6. **Data as lead-gen/护城河**: Persona 8B is "available by request." Our
   future consented human-experiment data can use the same gated-access
   pattern.【judgment】

## What NOT to borrow

- **The 8.3B number as a headline.** It markets scale we deliberately reject:
  a weighted representative panel is the scientifically defensible design, and
  their own APB admits synthetic personas are "not statistical samples of
  real populations." Our moat claim is calibration + falsifiability, not
  headcount.【judgment】
- **1,290 universal dimensions.** Scenario-derived fields keep calibration
  tractable; their multi-attribute compounding loss is the cost of
  dimensionality.【judgment】
- **Stopping at the disclaimer.** They stop at "not a replacement"; we are
  built to be *tested against* real people (BP validation layers 3–6). That
  is the differentiation, not a gap to close.【judgment】

## Concrete actions for this repo (small, ordered)

| # | action | size |
|---|---|---|
| 1 | persona provenance: add `layer: human/extracted/synthetic` per field | XS |
| 2 | sensitivity report: $/combo column from usage metering | XS |
| 3 | run manifest: checksum of scenario yaml + panel | S |
| 4 | demo report: product-view one-pager + concrete scenario copy | S |
| 5 | post-run static HTML dashboard (Playground-lite) | M |
| 6 | BP: cite APB's survey-vs-action gap as evidence for behavior calibration | XS |
