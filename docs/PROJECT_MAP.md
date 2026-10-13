# Project map

- `districtpulse/state.py`: per-TLS traffic state features and tabular discretization.
- `districtpulse/smdp.py`: duration-aware tabular SMDP Q-learning update.
- `districtpulse/emergency.py`: route-aware emergency detection and conservative priority requests.
- `districtpulse/pressure.py`: movement-level upstream-minus-downstream pressure and safe green-duration helper.
- `districtpulse/controllers.py`: fixed, density, SMDP, pressure-informed and forecast-pressure controllers.
- `districtpulse/stgnn_model.py`: graph aggregation + GRU neural architecture.
- `districtpulse/forecast.py`: checkpoint loading and live queue prediction.
- `districtpulse/metrics.py`: ordinary/emergency tripinfo and per-TLS queue metrics.
- `scripts/setup_demo.py`: reproducible generated-grid demand plus a cloned ambulance route.
- `scripts/run_experiment.py`: TraCI simulation loop, controller wiring, and output artifacts.
- `scripts/run_batch.py`: matched-seed experiments.
- `scripts/summarize_results.py`, `scripts/plot_results.py`: result aggregation and comparison plots.
- `scripts/export_graph_dataset.py`: graph adjacency and chronological feature-window export.
- `scripts/train_stgnn.py`: chronological train/validation/test, baseline metrics and checkpoint output.
- `docs/STGNN.md`: forecasting protocol and integration boundaries.
- `docs/PUBLICATION_PLAN.md`: research protocol and publication actions.

Generated SUMO files, trained checkpoints and results are intentionally excluded from Git by `.gitignore`. Recreate them with the README commands.
