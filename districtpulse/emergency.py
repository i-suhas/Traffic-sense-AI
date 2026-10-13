"""Conservative emergency-vehicle priority for SUMO traffic-light programs.

The manager does not jump directly between arbitrary phases. It lets the existing
SUMO signal program perform its configured yellow/all-red transitions, shortens
non-target green phases only after the minimum-green constraint, and extends a
compatible green phase for the emergency movement.
"""
from collections import defaultdict


class EmergencyPriorityManager:
    def __init__(self, traci, tls_ids, phase_started, enabled=True,
                 vehicle_prefix="ambulance_", lookahead_m=250.0,
                 minimum_green_s=5.0, priority_green_s=20.0):
        self.traci = traci
        self.tls_ids = set(tls_ids)
        self.phase_started = phase_started
        self.enabled = enabled
        self.vehicle_prefix = vehicle_prefix
        self.lookahead_m = float(lookahead_m)
        self.minimum_green_s = float(minimum_green_s)
        self.priority_green_s = float(priority_green_s)
        self.events = []
        self._active = {}
        self._last_action = {}
        self._granted = set()
        self._seen_phases = {}

    def _is_emergency(self, vehicle_id):
        if vehicle_id.startswith(self.vehicle_prefix):
            return True
        try:
            return self.traci.vehicle.getTypeID(vehicle_id).lower() in {
                "emergency", "ambulance", "fire_engine", "fireengine"
            }
        except Exception:
            return False

    def _compatible_phases(self, tls_id, link_index):
        """Return green phase indexes whose state serves the emergency movement."""
        try:
            current_program = self.traci.trafficlight.getProgram(tls_id)
            logics = self.traci.trafficlight.getAllProgramLogics(tls_id)
        except Exception:
            return []
        phases = []
        for logic in logics:
            if getattr(logic, "programID", None) != current_program:
                continue
            for index, phase in enumerate(logic.phases):
                state = getattr(phase, "state", "")
                if link_index < len(state) and state[link_index] in ("G", "g"):
                    phases.append(index)
        return phases

    def _log(self, now, vehicle_id, tls_id, link_index, distance, event, phase=None):
        self.events.append({
            "time": float(now), "vehicle_id": vehicle_id, "tls_id": tls_id,
            "link_index": int(link_index), "distance_m": float(distance),
            "event": event, "phase": phase,
        })

    def step(self, now):
        if not self.enabled:
            return
        requests = defaultdict(list)
        try:
            vehicle_ids = list(self.traci.vehicle.getIDList())
        except Exception:
            return

        for vehicle_id in vehicle_ids:
            if not self._is_emergency(vehicle_id):
                continue
            try:
                next_tls = self.traci.vehicle.getNextTLS(vehicle_id)
            except Exception:
                continue
            # The first upcoming traffic light on the vehicle's route is the target.
            for item in next_tls or []:
                if len(item) < 4:
                    continue
                tls_id, link_index, distance, _state = item[:4]
                if tls_id in self.tls_ids and float(distance) <= self.lookahead_m:
                    requests[tls_id].append(
                        (float(distance), vehicle_id, int(link_index))
                    )
                    break

        # Drop requests that have passed or are no longer in the lookahead window.
        for tls_id in list(self._active):
            if tls_id not in requests:
                self._active.pop(tls_id, None)
                self._last_action.pop(tls_id, None)
                self._granted.discard(tls_id)

        for tls_id, candidates in requests.items():
            distance, vehicle_id, link_index = min(candidates)
            phases = self._compatible_phases(tls_id, link_index)
            if not phases:
                if self._active.get(tls_id) != (vehicle_id, link_index):
                    self._log(now, vehicle_id, tls_id, link_index, distance,
                              "no_compatible_green_phase")
                self._active[tls_id] = (vehicle_id, link_index)
                continue

            request = (vehicle_id, link_index)
            if self._active.get(tls_id) != request:
                self._active[tls_id] = request
                self._granted.discard(tls_id)
                self._last_action.pop(tls_id, None)
                self._log(now, vehicle_id, tls_id, link_index, distance,
                          "priority_requested")

            phase = self.traci.trafficlight.getPhase(tls_id)
            state = self.traci.trafficlight.getRedYellowGreenState(tls_id)
            phase_key = (tls_id, phase)
            if self._seen_phases.get(tls_id) != phase:
                self._seen_phases[tls_id] = phase
                self.phase_started[tls_id] = now

            target_green = link_index < len(state) and state[link_index] in ("G", "g")
            action_key = (phase, target_green)
            if target_green:
                if tls_id not in self._granted:
                    # Extend only the phase that already serves the emergency movement.
                    self.traci.trafficlight.setPhaseDuration(
                        tls_id, self.priority_green_s
                    )
                    self._granted.add(tls_id)
                    self._last_action[tls_id] = action_key
                    self._log(now, vehicle_id, tls_id, link_index, distance,
                              "priority_green_granted", phase)
            else:
                # Do not jump to an arbitrary phase. Let SUMO's programmed transition
                # sequence run, reducing a non-target green only after minimum green.
                has_green = ("G" in state or "g" in state)
                if has_green and self._last_action.get(tls_id) != action_key:
                    started = self.phase_started.get(tls_id, now)
                    elapsed = max(0.0, float(now) - float(started))
                    remaining = max(1.0, self.minimum_green_s - elapsed)
                    self.traci.trafficlight.setPhaseDuration(tls_id, remaining)
                    self._last_action[tls_id] = action_key
                    self._log(now, vehicle_id, tls_id, link_index, distance,
                              "non_target_green_shortened_safely", phase)
