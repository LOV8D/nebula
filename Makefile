# Market Wind Tunnel — demo actions
.PHONY: demo smoke panel report clean

demo:            ## full showcase: smoke + 3 wind-tunnel experiments + reports (~15s, offline)
	python3 -m runtime.cli demo

smoke:           ## one baseline run to check all five books trade
	python3 -m runtime.cli run -s scenarios/baseline.yaml --out runs/smoke

panel:           ## regenerate the 883-agent panel
	python3 -m runtime.cli panel

report:          ## rebuild comparison tables from existing runs
	python3 -m runtime.cli compare "runs/fee_demo/*" -o runs/fee_demo/report.md
	python3 -m runtime.cli compare "runs/news_demo/*" -o runs/news_demo/report.md
	python3 -m runtime.cli compare "runs/cb_demo/*"   -o runs/cb_demo/report.md

clean:           ## remove all run artifacts (keeps the curated runs/report.md? no — everything)
	rm -rf runs

brain-setup:     ## configure the REMOTE brain: copy .env.example -> .env, edit it
	cp -n .env.example .env 2>/dev/null; echo "edit .env: BRAIN_BASE_URL / BRAIN_API_KEY / BRAIN_MODEL"

brain-check:     ## preflight against the endpoint in .env: up? + one sample decision
	python3 -m runtime.cli brain

demo2:           ## real-brain showcase (news A/B) — needs .env pointing at the remote brain
	python3 -m runtime.cli demo2

fake-brain:      ## E2E test of the real-brain path via a local stub (not a model)
	python3 tests/fake_vllm.py --port 8000

ui:             ## cross-run dashboard (A/B curves, sensitivity, books, cards) -> docs/dashboard.html
	python3 -m runtime.cli ui
