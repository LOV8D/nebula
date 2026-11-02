"""TSP pipeline: the synthetic dry-run must recover every planted direction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.tick_size_pilot import dry_run  # noqa: E402


def main():
    out = dry_run()
    assert out["verdict"] == "REPLICATION HIT"
    assert len(out["results"]) == 3
    assert all(r["hit"] for r in out["results"])
    assert len(out["predictions_hash"]) == 16
    print("tick-size-pilot pipeline test: OK — planted spread/vol/"
          "inefficiency directions all recovered on synthetic data")


if __name__ == "__main__":
    main()
