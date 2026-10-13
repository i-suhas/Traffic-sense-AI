"""Movement-level pressure utilities for SUMO traffic-light programs."""
from __future__ import annotations


def _lane_halting(traci, lane_id):
    try:
        return float(traci.lane.getLastStepHaltingNumber(lane_id))
    except Exception:
        return 0.0


def _lane_vehicles(traci, lane_id):
    try:
        return float(traci.lane.getLastStepVehicleNumber(lane_id))
    except Exception:
        return 0.0


def phase_pressures(traci, tls_id):
    """Return {phase_index: pressure} for green phases in the active TLS program.

    Pressure is the sum over active movements of upstream queue minus downstream
    occupancy. Negative movement pressure is retained, following the usual
    max-pressure idea that sending vehicles into a full downstream lane is costly.
    """
    current_program = traci.trafficlight.getProgram(tls_id)
    logics = traci.trafficlight.getAllProgramLogics(tls_id)
    logic = next((item for item in logics
                  if getattr(item, "programID", None) == current_program), None)
    if logic is None:
        return {}

    controlled = traci.trafficlight.getControlledLinks(tls_id)
    scores = {}
    for phase_index, phase in enumerate(logic.phases):
        state = getattr(phase, "state", "")
        if not any(char in ("G", "g") for char in state):
            continue
        score = 0.0
        for link_index, signal in enumerate(state):
            if signal not in ("G", "g") or link_index >= len(controlled):
                continue
            movements = controlled[link_index] or []
            for movement in movements:
                if not movement or len(movement) < 2:
                    continue
                incoming_lane, outgoing_lane = movement[0], movement[1]
                score += (_lane_halting(traci, incoming_lane)
                          - _lane_vehicles(traci, outgoing_lane))
        scores[phase_index] = score
    return scores


def safe_remaining_green(now, phase_started, minimum_green_s=5.0):
    """Remaining seconds needed to honor a minimum green measured from phase start."""
    elapsed = max(0.0, float(now) - float(phase_started))
    return max(1.0, float(minimum_green_s) - elapsed)
