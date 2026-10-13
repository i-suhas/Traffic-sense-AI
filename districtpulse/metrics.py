from pathlib import Path
import xml.etree.ElementTree as ET
import json
import pandas as pd

def summarize_run(run_dir):
    run_dir = Path(run_dir)
    states_path = run_dir / 'states.csv'
    result = {"run_dir": str(run_dir)}
    if states_path.exists():
        df = pd.read_csv(states_path)
        result["mean_halting_vehicles"] = float(df.halting.mean()) if len(df) else 0.0
        result["max_halting_vehicles"] = int(df.halting.max()) if len(df) else 0
        result["mean_lane_vehicles"] = float(df.vehicles.mean()) if len(df) else 0.0
        result["mean_observed_waiting_proxy"] = float(df.waiting.mean()) if len(df) else 0.0
    trips = run_dir / 'tripinfo.xml'
    durations, waits, delays = [], [], []
    if trips.exists():
        try:
            for _, elem in ET.iterparse(trips, events=('end',)):
                if elem.tag == 'tripinfo':
                    if elem.get('duration') is not None: durations.append(float(elem.get('duration')))
                    if elem.get('waitingTime') is not None: waits.append(float(elem.get('waitingTime')))
                    if elem.get('timeLoss') is not None: delays.append(float(elem.get('timeLoss')))
                    elem.clear()
        except ET.ParseError:
            result['tripinfo_parse_warning'] = 'Incomplete XML; check whether SUMO finished normally.'
    result['completed_trips'] = len(durations)
    result['mean_trip_duration_s'] = sum(durations)/len(durations) if durations else None
    result['mean_trip_waiting_s'] = sum(waits)/len(waits) if waits else None
    result['mean_trip_time_loss_s'] = sum(delays)/len(delays) if delays else None
    (run_dir / 'metrics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
