from types import SimpleNamespace

from districtpulse.emergency import EmergencyPriorityManager


class FakeVehicle:
    def getIDList(self):
        return ["ambulance_seed42"]

    def getTypeID(self, vehicle_id):
        return "emergency"

    def getNextTLS(self, vehicle_id):
        return [("tls0", 0, 40.0, "G")]


class FakeTrafficLight:
    def __init__(self):
        self.duration_calls = []

    def getProgram(self, tls_id):
        return "0"

    def getAllProgramLogics(self, tls_id):
        return [SimpleNamespace(programID="0", phases=[
            SimpleNamespace(state="Gr", duration=20),
            SimpleNamespace(state="yr", duration=3),
        ])]

    def getPhase(self, tls_id):
        return 0

    def getRedYellowGreenState(self, tls_id):
        return "Gr"

    def setPhaseDuration(self, tls_id, duration):
        self.duration_calls.append((tls_id, duration))


class FakeTraCI:
    def __init__(self):
        self.vehicle = FakeVehicle()
        self.trafficlight = FakeTrafficLight()


def test_ambulance_gets_extension_when_its_movement_is_green():
    traci = FakeTraCI()
    phase_started = {"tls0": 0}
    manager = EmergencyPriorityManager(traci, ["tls0"], phase_started,
                                       enabled=True, priority_green_s=20)
    manager.step(10)
    assert traci.trafficlight.duration_calls == [("tls0", 20.0)]
    assert any(event["event"] == "priority_green_granted" for event in manager.events)
