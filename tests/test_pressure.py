from types import SimpleNamespace

from districtpulse.pressure import phase_pressures, safe_remaining_green


class FakeLane:
    def getLastStepHaltingNumber(self, lane):
        return {"in_a": 8, "in_b": 2}.get(lane, 0)

    def getLastStepVehicleNumber(self, lane):
        return {"out_a": 1, "out_b": 7}.get(lane, 0)


class FakeTrafficLight:
    def getProgram(self, tls):
        return "0"

    def getAllProgramLogics(self, tls):
        return [SimpleNamespace(programID="0", phases=[
            SimpleNamespace(state="Gr", duration=20),
            SimpleNamespace(state="yr", duration=3),
            SimpleNamespace(state="rG", duration=20),
        ])]

    def getControlledLinks(self, tls):
        return [[("in_a", "out_a", "")], [("in_b", "out_b", "")]]


class FakeTraCI:
    trafficlight = FakeTrafficLight()
    lane = FakeLane()


def test_phase_pressures_uses_upstream_minus_downstream():
    scores = phase_pressures(FakeTraCI(), "tls0")
    assert scores[0] == 7.0
    assert scores[2] == -5.0


def test_safe_remaining_green_respects_minimum_from_phase_start():
    assert safe_remaining_green(now=2, phase_started=0, minimum_green_s=5) == 3
    assert safe_remaining_green(now=9, phase_started=0, minimum_green_s=5) == 1
