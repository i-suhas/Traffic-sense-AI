# Project map

- `districtpulse/smdp.py`: duration-aware tabular SMDP Q-learning update.
- `districtpulse/state.py`: state features and discretization.
- `districtpulse/controllers.py`: fixed, density-responsive and SMDP policies.
- `districtpulse/metrics.py`: tripinfo/state metrics.
- `scripts/setup_demo.py`: deterministic generated-grid scenario.
- `scripts/download_osm.py`, `build_osm_network.py`, `generate_osm_demand.py`: Mysuru OSM pipeline.
- `scripts/run_experiment.py`: TraCI simulation loop and outputs.
- `scripts/run_batch.py`: matched controller/seed runs.
- `scripts/export_graph_dataset.py`, `train_stgnn.py`: graph-temporal data/model scaffold.
- `docs/PUBLICATION_PLAN.md`: research protocol and publication actions.
