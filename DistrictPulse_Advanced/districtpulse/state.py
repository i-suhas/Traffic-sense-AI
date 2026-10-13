"""Traffic state extraction and coarse state discretization."""

def collect_tls_state(traci, tls_id):
    controlled = traci.trafficlight.getControlledLanes(tls_id)
    lanes = sorted(set(controlled))
    halting = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in lanes)
    vehicles = sum(traci.lane.getLastStepVehicleNumber(lane) for lane in lanes)
    mean_speed = sum(traci.lane.getLastStepMeanSpeed(lane) for lane in lanes) / max(1, len(lanes))
    waiting = sum(traci.lane.getWaitingTime(lane) for lane in lanes)
    return {"halting": int(halting), "vehicles": int(vehicles), "mean_speed": float(mean_speed), "waiting": float(waiting), "lane_count": len(lanes)}

def pressure_bin(halting):
    if halting <= 2: return 0
    if halting <= 6: return 1
    if halting <= 12: return 2
    return 3

def discretize_state(state, phase_index):
    # Compact state for transparent tabular baseline; expand for publication experiments.
    return (pressure_bin(state["halting"]), min(3, state["vehicles"] // 5), int(phase_index) % 8)
