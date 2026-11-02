"""Where things live on disk — the one place to change a default location.

    runs/evidence/   committed evidence packs (manifest, summary, report;
                     bulk JSONL is gitignored and rebuilt by `make demo`)
    runs/scratch/    throwaway output: smoke runs, live tests, video frames
    site/            generated pages: dashboard, investor survey
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs" / "evidence"
SCRATCH = ROOT / "runs" / "scratch"
SITE = ROOT / "site"
PANEL = ROOT / "personas" / "panel_v3.json"

# The flagship news-wording A/B on the real brain — every dashboard page
# reads this pair unless told otherwise.
FLAGSHIP = RUNS / "demo2" / "news_demo"
SENSITIVITY = RUNS / "sensitivity"

# Packages whose code decides what a run produces. recorder.code_hash digests
# all of them: prompts live in runtime/llm.py, seed offsets and scenario
# loading in experiments/, panel provenance in evidence/.
CODE_PACKAGES = ("runtime", "experiments", "evidence")
