# Market Wind Tunnel — demo actions. `make help` lists them.
.PHONY: help demo demo2 smoke panel report parity ui test clean brain-setup brain-check fake-brain

help:            ## list targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

demo:            ## mock-brain showcase: smoke + 3 experiments x 5 seeds + reports (~11 s, offline)
	python3 -m runtime.cli demo

demo2:           ## real-brain showcase (news A/B) — needs .env pointing at the remote brain
	python3 -m runtime.cli demo2

smoke:           ## one baseline run to check all five books trade
	python3 -m runtime.cli run -s scenarios/baseline.yaml --out runs/scratch/smoke

panel:           ## regenerate the 883-agent panel
	python3 -m runtime.cli panel

report:          ## rebuild the demo's comparison tables from existing runs
	for g in fee_demo news_demo cb_demo; do \
	  python3 -m runtime.cli compare "runs/evidence/demo/$$g/*" -o runs/evidence/demo/$$g/report.md; done

parity:          ## are the flagship A/B arms identical before the intervention?
	python3 -m runtime.cli parity runs/evidence/demo2/news_demo

ui:              ## dashboard -> site/dashboard.html (reads runs, re-executes nothing)
	python3 -m runtime.cli ui

test:            ## all tests (offline)
	@for t in tests/test_*.py; do python3 $$t || exit 1; done

clean:           ## remove scratch output only; committed evidence under runs/evidence stays
	rm -rf runs/scratch

brain-setup:     ## configure the REMOTE brain: copy .env.example -> .env, edit it
	cp -n .env.example .env 2>/dev/null; echo "edit .env: BRAIN_BASE_URL / BRAIN_API_KEY / BRAIN_MODEL"

brain-check:     ## preflight against the endpoint in .env: up? + one sample decision
	python3 -m runtime.cli brain

fake-brain:      ## E2E test of the real-brain path via a local stub (not a model)
	python3 tools/fake_vllm.py --port 8000
