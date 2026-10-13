"""Traffic-signal controllers used by DistrictPulse AI."""
from collections import defaultdict, deque

from districtpulse.smdp import SMDPQLearner, Transition
from districtpulse.state import collect_tls_state, discretize_state
from districtpulse.emergency import EmergencyPriorityManager
from districtpulse.pressure import phase_pressures, safe_remaining_green


class BaseController:
    def __init__(self, traci, tls_ids, seed=42, emergency_priority=False):
        self.traci, self.tls_ids = traci, list(tls_ids)
        self.last_phase = {}
        self.phase_started = {}
        self.last_decision = {}
        self.last_state = {}
        self.last_action = {}
        self.reward_acc = {}
        self.duration_acc = {}
        self.rows = []
        self.transitions = []
        self.sim_time = 0
        self.seed = seed
        self.latest_states = {}
        self.emergency = EmergencyPriorityManager(
            traci, tls_ids, self.phase_started, enabled=emergency_priority
        )

    def is_green_phase(self, tls_id):
        state = self.traci.trafficlight.getRedYellowGreenState(tls_id)
        return "G" in state or "g" in state

    def phase_index(self, tls_id):
        return self.traci.trafficlight.getPhase(tls_id)

    def state(self, tls_id):
        return collect_tls_state(self.traci, tls_id)

    def on_step(self, now):
        self.sim_time = now
        current_states = {}
        for tls in self.tls_ids:
            st = self.state(tls)
            current_states[tls] = st
            phase = self.phase_index(tls)
            if self.last_phase.get(tls) != phase:
                self.phase_started[tls] = now
            self.rows.append({"time": now, "tls_id": tls, "phase": phase, **st})
            if tls in self.last_decision:
                self.reward_acc[tls] += -(st["waiting"] + 2.0 * st["halting"])
                self.duration_acc[tls] += 1
            if self.is_green_phase(tls) and self.last_phase.get(tls) != phase:
                self._decision(tls, st, phase, now)
            self.last_phase[tls] = phase
        self.latest_states = current_states
        self.after_step(now, current_states)
        # Apply priority after the ordinary policy, so an emergency request takes precedence.
        self.emergency.step(now)

    def after_step(self, now, states):
        """Hook for forecasting controllers."""

    def _decision(self, tls, st, phase, now):
        raise NotImplementedError


class FixedController(BaseController):
    def _decision(self, tls, st, phase, now):
        # Preserve the SUMO program's configured green durations.
        return


class DensityController(BaseController):
    def _decision(self, tls, st, phase, now):
        duration = 10 if st["halting"] <= 2 else 15 if st["halting"] <= 6 else 20 if st["halting"] <= 12 else 25
        self.traci.trafficlight.setPhaseDuration(tls, duration)


class PressureController(BaseController):
    """Max-pressure-inspired controller respecting the existing SUMO phase sequence.

    It extends the highest-pressure currently active phase. If another programmed
    green phase has higher pressure, it allows the normal SUMO yellow/clearance
    sequence to proceed and minimizes the current green only after minimum green.
    This deliberately avoids jumping directly into a conflicting green phase.
    """
    def __init__(self, traci, tls_ids, seed=42, emergency_priority=False,
                 minimum_green_s=5.0, base_green_s=10.0, max_green_s=25.0):
        super().__init__(traci, tls_ids, seed, emergency_priority)
        self.minimum_green_s = float(minimum_green_s)
        self.base_green_s = float(base_green_s)
        self.max_green_s = float(max_green_s)
        self.pressure_rows = []

    def forecast_queue(self, tls_id, observed_queue):
        return float(observed_queue)

    def _decision(self, tls, st, phase, now):
        scores = phase_pressures(self.traci, tls)
        if not scores:
            duration = 10 if st["halting"] <= 2 else 15 if st["halting"] <= 6 else 20 if st["halting"] <= 12 else 25
            self.traci.trafficlight.setPhaseDuration(tls, duration)
            return
        best_phase = max(scores, key=scores.get)
        current_score = float(scores.get(phase, float("-inf")))
        self.pressure_rows.append({
            "time": now, "tls_id": tls, "phase": phase,
            "current_pressure": current_score, "selected_phase": best_phase,
            "selected_pressure": float(scores[best_phase]),
        })
        if phase == best_phase:
            forecast_queue = max(0.0, self.forecast_queue(tls, st["halting"]))
            extra = min(10.0, forecast_queue * 0.5)
            duration = min(self.max_green_s, self.base_green_s + extra)
            self.traci.trafficlight.setPhaseDuration(tls, duration)
        else:
            started = self.phase_started.get(tls, now)
            remaining = safe_remaining_green(now, started, self.minimum_green_s)
            self.traci.trafficlight.setPhaseDuration(tls, remaining)


class ForecastPressureController(PressureController):
    def __init__(self, traci, tls_ids, seed=42, emergency_priority=False,
                 forecast_model=None, **kwargs):
        if not forecast_model:
            raise ValueError("forecast-pressure requires --forecast-model CHECKPOINT")
        super().__init__(traci, tls_ids, seed, emergency_priority, **kwargs)
        from districtpulse.forecast import STGNNPredictor
        self.predictor = STGNNPredictor(forecast_model)
        self.history = {node: deque(maxlen=self.predictor.window)
                        for node in self.predictor.node_ids}
        self.latest_forecast = {}
        self.forecast_rows = []

    def after_step(self, now, states):
        for node in self.predictor.node_ids:
            st = states.get(node)
            if st is None:
                continue
            self.history[node].append([
                float(st["halting"]), float(st["vehicles"]),
                float(st["waiting"]), float(st["mean_speed"])
            ])
        prediction = self.predictor.predict(self.history)
        if prediction is not None:
            self.latest_forecast = prediction
            for node, queue in prediction.items():
                self.forecast_rows.append({
                    "time": now, "tls_id": node, "predicted_queue": queue,
                    "observed_queue": states.get(node, {}).get("halting"),
                })

    def forecast_queue(self, tls_id, observed_queue):
        return self.latest_forecast.get(tls_id, float(observed_queue))


class SMDPController(BaseController):
    def __init__(self, traci, tls_ids, seed=42, explore=True, emergency_priority=False):
        super().__init__(traci, tls_ids, seed, emergency_priority)
        self.agent = SMDPQLearner(seed=seed)
        self.explore = explore

    def _decision(self, tls, st, phase, now):
        state = discretize_state(st, phase)
        if tls in self.last_decision:
            prev_state = self.last_state[tls]
            prev_action = self.last_action[tls]
            duration = max(1, self.duration_acc.get(tls, 1))
            reward = self.reward_acc.get(tls, 0.0)
            transition = Transition(prev_state, prev_action, duration, reward, state)
            self.agent.update(transition)
            self.transitions.append({
                "tls_id": tls, "decision_time": now, "state": repr(prev_state),
                "action_index": prev_action, "action_duration_s": duration,
                "accumulated_reward": reward, "next_state": repr(state),
                "discount_factor": self.agent.gamma ** duration
            })
        action_idx = self.agent.choose(state, explore=self.explore)
        duration = self.agent.actions[action_idx]
        self.traci.trafficlight.setPhaseDuration(tls, duration)
        self.last_decision[tls] = now
        self.last_state[tls] = state
        self.last_action[tls] = action_idx
        self.reward_acc[tls] = 0.0
        self.duration_acc[tls] = 0
