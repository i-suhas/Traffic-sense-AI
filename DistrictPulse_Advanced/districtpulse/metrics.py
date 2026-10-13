"""Run metrics for ordinary traffic and emergency vehicles."""
from pathlib import Path
import xml.etree.ElementTree as ET
import json
import pandas as pd


def _mean(values):
    return sum(values) / len(values) if values else None


def summarize_run(run_dir):
    run_dir = Path(run_dir)
    states_path = run_dir / "states.csv"
    result = {"run_dir": str(run_dir)}
    if states_path.exists():
        df = pd.read_csv(states_path)
        result["mean_halting_vehicles"] = float(df.halting.mean()) if len(df) else 0.0
        result["max_halting_vehicles"] = int(df.halting.max()) if len(df) else 0
        result["mean_lane_vehicles"] = float(df.vehicles.mean()) if len(df) else 0.0
        result["mean_observed_waiting_proxy"] = float(df.waiting.mean()) if len(df) else 0.0
        result["mean_queue_proxy_by_tls"] = float(df.halting.mean()) if len(df) else 0.0

    trips_path = run_dir / "tripinfo.xml"
    groups = {"ordinary": {"duration": [], "waiting": [], "time_loss": []},
              "emergency": {"duration": [], "waiting": [], "time_loss": []}}
    if trips_path.exists():
        try:
            for _, elem in ET.iterparse(trips_path, events=("end",)):
                if elem.tag == "tripinfo":
                    vehicle_id = elem.get("id", "")
                    group = "emergency" if vehicle_id.startswith("ambulance_") else "ordinary"
                    for source, target in (
                        ("duration", "duration"),
                        ("waitingTime", "waiting"),
                        ("timeLoss", "time_loss"),
                    ):
                        if elem.get(source) is not None:
                            groups[group][target].append(float(elem.get(source)))
                    elem.clear()
        except ET.ParseError:
            result["tripinfo_parse_warning"] = "Incomplete XML; check whether SUMO finished normally."

    result["completed_trips"] = sum(len(groups[name]["duration"]) for name in groups)
    result["completed_emergency_trips"] = len(groups["emergency"]["duration"])
    result["completed_ordinary_trips"] = len(groups["ordinary"]["duration"])
    for group in ("ordinary", "emergency"):
        result[f"mean_{group}_trip_duration_s"] = _mean(groups[group]["duration"])
        result[f"mean_{group}_trip_waiting_s"] = _mean(groups[group]["waiting"])
        result[f"mean_{group}_trip_time_loss_s"] = _mean(groups[group]["time_loss"])
    # Backward-compatible overall metrics.
    all_durations = groups["ordinary"]["duration"] + groups["emergency"]["duration"]
    all_waits = groups["ordinary"]["waiting"] + groups["emergency"]["waiting"]
    all_losses = groups["ordinary"]["time_loss"] + groups["emergency"]["time_loss"]
    result["mean_trip_duration_s"] = _mean(all_durations)
    result["mean_trip_waiting_s"] = _mean(all_waits)
    result["mean_trip_time_loss_s"] = _mean(all_losses)

    (run_dir / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
