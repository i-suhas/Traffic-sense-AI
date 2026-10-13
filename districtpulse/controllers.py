"""Controller policies. Signal phase sequence is left to SUMO's TLS program."""
from districtpulse.smdp import SMDPQLearner, Transition
from districtpulse.state import collect_tls_state, discretize_state

class BaseController:
    def __init__(self, traci, tls_ids, seed=42):
        self.traci, self.tls_ids = traci, list(tls_ids)
        self.last_phase = {}
        self.last_decision = {}
        self.last_state = {}
        self.last_action = {}
        self.reward_acc = {}
        self.duration_acc = {}
        self.rows = []
        self.transitions = []
        self.sim_time = 0
        self.seed = seed

    def is_green_phase(self, tls_id):
        state = self.traci.trafficlight.getRedYellowGreenState(tls_id)
        return 'G' in state or 'g' in state

    def phase_index(self, tls_id):
        return self.traci.trafficlight.getPhase(tls_id)

    def state(self, tls_id):
        return collect_tls_state(self.traci, tls_id)

    def on_step(self, now):
        self.sim_time = now
        for tls in self.tls_ids:
            st = self.state(tls)
            phase = self.phase_index(tls)
            self.rows.append({"time": now, "tls_id": tls, "phase": phase, **st})
            # Negative operational cost, accumulated each simulation second between decisions.
            if tls in self.last_decision:
                self.reward_acc[tls] += -(st["waiting"] + 2.0 * st["halting"])
                self.duration_acc[tls] += 1
            # A decision occurs when a new green phase becomes active.
            if self.is_green_phase(tls) and self.last_phase.get(tls) != phase:
                self._decision(tls, st, phase, now)
            self.last_phase[tls] = phase

    def _decision(self, tls, st, phase, now):
        raise NotImplementedError

class FixedController(BaseController):
    def _decision(self, tls, st, phase, now):
        # Do not alter programmed green timing.
        return

class DensityController(BaseController):
    def _decision(self, tls, st, phase, now):
        # Simple local pressure-responsive extension; setPhaseDuration only changes the
        # remaining duration of the current phase, not the signal's phase order.
        duration = 10 if st['halting'] <= 2 else 15 if st['halting'] <= 6 else 20 if st['halting'] <= 12 else 25
        self.traci.trafficlight.setPhaseDuration(tls, duration)

class SMDPController(BaseController):
    def __init__(self, traci, tls_ids, seed=42, explore=True):
        super().__init__(traci, tls_ids, seed)
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
            self.transitions.append({"tls_id": tls, "decision_time": now, "state": repr(prev_state),
                "action_index": prev_action, "action_duration_s": duration, "accumulated_reward": reward,
                "next_state": repr(state), "discount_factor": self.agent.gamma ** duration})
        action_idx = self.agent.choose(state, explore=self.explore)
        duration = self.agent.actions[action_idx]
        self.traci.trafficlight.setPhaseDuration(tls, duration)
        self.last_decision[tls] = now
        self.last_state[tls] = state
        self.last_action[tls] = action_idx
        self.reward_acc[tls] = 0.0
        self.duration_acc[tls] = 0
