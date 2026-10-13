"""Tabular semi-Markov Q-learning with duration-aware discounting."""
from dataclasses import dataclass
import random
from typing import Hashable

@dataclass
class Transition:
    state: Hashable
    action: int
    duration: int
    reward: float
    next_state: Hashable

class SMDPQLearner:
    def __init__(self, actions=(10, 15, 20, 25), alpha=0.15, gamma=0.97, epsilon=0.15, seed=42):
        self.actions = tuple(actions)
        self.alpha, self.gamma, self.epsilon = alpha, gamma, epsilon
        self.q = {}
        self.rng = random.Random(seed)

    def values(self, state):
        return self.q.setdefault(state, [0.0 for _ in self.actions])

    def choose(self, state, explore=True):
        values = self.values(state)
        if explore and self.rng.random() < self.epsilon:
            return self.rng.randrange(len(self.actions))
        best = max(values)
        return self.rng.choice([i for i, v in enumerate(values) if v == best])

    def update(self, transition: Transition):
        s, a, d, r, ns = transition.state, transition.action, transition.duration, transition.reward, transition.next_state
        q_s = self.values(s)
        target = float(r) + (self.gamma ** max(1, int(d))) * max(self.values(ns))
        q_s[int(a)] += self.alpha * (target - q_s[int(a)])
        return float(q_s[int(a)])
