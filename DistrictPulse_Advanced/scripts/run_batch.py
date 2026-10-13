"""Run matched-seed controller comparisons without overwriting prior result folders."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="data/demo")
    parser.add_argument("--controllers", nargs="+",
                        choices=["fixed", "density", "smdp", "max-pressure", "forecast-pressure"],
                        default=["fixed", "density", "smdp", "max-pressure"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--emergency-priority", action="store_true")
    parser.add_argument("--forecast-model", default=None)
    parser.add_argument("--results-dir", default="results/batch")
    args = parser.parse_args()
    if "forecast-pressure" in args.controllers and not args.forecast_model:
        raise SystemExit("forecast-pressure requires --forecast-model models/stgnn.pt")
    root = Path(__file__).resolve().parents[1]
    for seed in args.seeds:
        for controller in args.controllers:
            command = [
                sys.executable, str(root / "scripts" / "run_experiment.py"),
                "--scenario", args.scenario, "--controller", controller,
                "--seed", str(seed), "--results-dir", args.results_dir,
            ]
            if args.end:
                command += ["--end", str(args.end)]
            if args.emergency_priority:
                command += ["--emergency-priority"]
            if args.forecast_model and controller == "forecast-pressure":
                command += ["--forecast-model", args.forecast_model]
            subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
