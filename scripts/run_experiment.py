"""Run one reproducible DistrictPulse SUMO experiment.

Existing run folders are preserved by default. Use --overwrite to replace only
this controller/seed folder; no other experiment results are deleted.
"""
import argparse
import csv
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from districtpulse.controllers import (
    FixedController, DensityController, SMDPController,
    PressureController, ForecastPressureController,
)
from districtpulse.metrics import summarize_run


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a reproducible DistrictPulse SUMO traffic-control experiment."
    )
    parser.add_argument("--scenario", default="data/demo",
                        help="Scenario folder, network XML path, or network prefix (default: data/demo).")
    parser.add_argument("--controller",
                        choices=("fixed", "density", "smdp", "max-pressure", "forecast-pressure"),
                        default="smdp")
    parser.add_argument("--emergency-priority", action="store_true",
                        help="Enable route-aware ambulance priority on top of the selected controller.")
    parser.add_argument("--forecast-model", default=None,
                        help="Validated ST-GNN checkpoint; required for forecast-pressure.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--end", type=int, default=None,
                        help="Optional maximum simulation time in seconds.")
    parser.add_argument("--gui", action="store_true", help="Run with sumo-gui instead of sumo.")
    parser.add_argument("--no-explore", action="store_true",
                        help="Disable epsilon exploration for this SMDP run.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Delete and recreate only this run's output folder before running.")
    parser.add_argument("--results-dir", default="results",
                        help="Results directory, relative to project root unless absolute (default: results).")
    return parser.parse_args()


def resolve_scenario(value):
    scenario = Path(value)
    if not scenario.is_absolute():
        scenario = ROOT / scenario

    if str(scenario).endswith(".net.xml"):
        net = scenario
        prefix = Path(str(scenario)[:-8])
        routes = Path(str(prefix) + ".rou.xml")
    elif scenario.is_dir():
        net = scenario / "demo.net.xml"
        routes = scenario / "demo.rou.xml"
    else:
        prefix = scenario
        net = Path(str(prefix) + ".net.xml")
        routes = Path(str(prefix) + ".rou.xml")

    if not net.is_file():
        raise SystemExit(f"Network not found: {net}\nRun: python scripts/setup_demo.py")
    if not routes.is_file():
        raise SystemExit(f"Route file not found: {routes}\nGenerate demand before running the experiment.")
    return net.resolve(), routes.resolve()


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    if args.seed < 0:
        raise SystemExit("--seed must be non-negative.")
    if args.end is not None and args.end <= 0:
        raise SystemExit("--end must be a positive number of seconds.")
    if args.controller == "forecast-pressure" and not args.forecast_model:
        raise SystemExit("--controller forecast-pressure requires --forecast-model CHECKPOINT")

    net, routes = resolve_scenario(args.scenario)
    results_root = Path(args.results_dir)
    if not results_root.is_absolute():
        results_root = ROOT / results_root
    run_dir = results_root / f"{args.controller}_seed{args.seed}"

    if run_dir.exists():
        if not args.overwrite:
            raise SystemExit(
                f"Output folder already exists:\n  {run_dir}\n"
                "To preserve old results, choose another results directory.\n"
                "To replace only this run, add --overwrite."
            )
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)

    home = os.environ.get("SUMO_HOME")
    if home:
        tools_dir = str(Path(home) / "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = tools_dir + (os.pathsep + current_pythonpath if current_pythonpath else "")

    try:
        import traci
    except ImportError as exc:
        raise SystemExit(
            "Could not import TraCI. Install SUMO and set SUMO_HOME so that "
            "%SUMO_HOME%\\tools is available to Python."
        ) from exc

    tripinfo = run_dir / "tripinfo.xml"
    summary_xml = run_dir / "summary.xml"
    executable = "sumo-gui" if args.gui else "sumo"
    command = [
        executable, "-n", str(net), "-r", str(routes),
        "--seed", str(args.seed),
        "--no-step-log", "true",
        "--duration-log.disable", "true",
        "--tripinfo-output", str(tripinfo.resolve()),
        "--summary-output", str(summary_xml.resolve()),
        "--time-to-teleport", "-1",
    ]
    if args.end is not None:
        command += ["--end", str(args.end)]

    print(f"Controller : {args.controller}")
    print(f"Seed       : {args.seed}")
    print(f"Network    : {net}")
    print(f"Routes     : {routes}")
    print(f"Output     : {run_dir}")
    print("Launching SUMO...")

    started_at = time.time()
    controller = None
    natural_completion = False
    tls_ids = []
    try:
        # Keep the module-style TraCI API used by the controller classes.
        traci.start(command)
        conn = traci
        tls_ids = list(conn.trafficlight.getIDList())
        if not tls_ids:
            print("WARNING: this network has no traffic lights; controller actions will not be applied.")

        controller_class = {
            "fixed": FixedController,
            "density": DensityController,
            "smdp": SMDPController,
            "max-pressure": PressureController,
            "forecast-pressure": ForecastPressureController,
        }[args.controller]
        common = {"seed": args.seed, "emergency_priority": args.emergency_priority}
        if args.controller == "smdp":
            controller = controller_class(
                conn, tls_ids, **common, explore=not args.no_explore
            )
        elif args.controller == "forecast-pressure":
            controller = controller_class(
                conn, tls_ids, **common, forecast_model=args.forecast_model
            )
        else:
            controller = controller_class(conn, tls_ids, **common)

        while conn.simulation.getMinExpectedNumber() > 0:
            conn.simulationStep()
            now = conn.simulation.getTime()
            controller.on_step(now)
            if args.end is not None and now >= args.end:
                break

        natural_completion = conn.simulation.getMinExpectedNumber() <= 0
    finally:
        try:
            traci.close()
        except Exception:
            pass

    if controller is None:
        raise SystemExit("SUMO ended before the controller was initialized; inspect the SUMO error above.")

    state_fields = [
        "time", "tls_id", "phase", "halting", "vehicles",
        "mean_speed", "waiting", "lane_count",
    ]
    write_csv(run_dir / "states.csv", controller.rows, state_fields)
    write_csv(run_dir / "smdp_transitions.csv", controller.transitions)
    write_csv(run_dir / "emergency_events.csv", controller.emergency.events)
    if hasattr(controller, "pressure_rows"):
        write_csv(run_dir / "pressure_scores.csv", controller.pressure_rows)
    if hasattr(controller, "forecast_rows"):
        write_csv(run_dir / "forecast_predictions.csv", controller.forecast_rows)

    manifest = {
        "project": "DistrictPulse AI",
        "controller": args.controller,
        "seed": args.seed,
        "network": str(net),
        "routes": str(routes),
        "simulated_seconds": controller.sim_time,
        "wall_seconds": round(time.time() - started_at, 2),
        "tls_count": len(tls_ids),
        "completion_status": "natural_end" if natural_completion else "stopped_at_time_limit_or_early_exit",
        "sumo_command": command,
        "exploration_enabled": (not args.no_explore) if args.controller == "smdp" else None,
        "emergency_priority_enabled": args.emergency_priority,
        "forecast_model": args.forecast_model if args.controller == "forecast-pressure" else None,
        "demand_note": "RandomTrips-generated demand is synthetic unless calibrated against observations.",
        "model_note": (
            "Forecast-pressure uses the supplied ST-GNN checkpoint."
            if args.controller == "forecast-pressure"
            else "ST-GNN forecasts are not used by this controller."
        ),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    metrics = summarize_run(run_dir)
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("\nRun completed. Metrics:")
    print(json.dumps(metrics, indent=2))
    print(f"\nArtifacts saved to: {run_dir}")
    print("Note: an SMDP learner is initialized per run; this script does not train across separate episodes.")
    if args.emergency_priority:
        print(f"Emergency-priority events: {len(controller.emergency.events)}")


if __name__ == "__main__":
    main()
