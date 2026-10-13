import json

from districtpulse.metrics import summarize_run


def test_metrics_separate_ambulance_and_ordinary_tripinfo(tmp_path):
    (tmp_path / "states.csv").write_text(
        "time,tls_id,phase,halting,vehicles,mean_speed,waiting,lane_count\n"
        "1,tls0,0,2,4,5.0,3.0,2\n", encoding="utf-8"
    )
    (tmp_path / "tripinfo.xml").write_text(
        '<tripinfos>'
        '<tripinfo id="car0" duration="30" waitingTime="5" timeLoss="8"/>'
        '<tripinfo id="ambulance_seed42" duration="20" waitingTime="1" timeLoss="2"/>'
        '</tripinfos>', encoding="utf-8"
    )
    result = summarize_run(tmp_path)
    assert result["completed_trips"] == 2
    assert result["completed_emergency_trips"] == 1
    assert result["completed_ordinary_trips"] == 1
    assert result["mean_emergency_trip_duration_s"] == 20.0
    assert result["mean_ordinary_trip_waiting_s"] == 5.0
    saved = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert saved["completed_emergency_trips"] == 1
