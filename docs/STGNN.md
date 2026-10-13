# ST-GNN queue forecasting

The project contains an experimental graph-aggregation + GRU model. It predicts the next queue count per signalized intersection from recent `halting`, `vehicles`, `waiting`, and `mean_speed` features.

## Dataset

Use `scripts/export_graph_dataset.py` to create windows from a `states.csv` run. Prefer `--network data/demo/demo.net.xml` so the TLS adjacency is derived from connected network edges. A supplied `--adjacency` CSV is supported only if its rows/columns match sorted TLS IDs exactly.

Each sample has:
- `X`: `[window, nodes, features]`
- `y`: `[nodes, 1]`, halting count at the configured forecast horizon
- `A`: adjacency matrix
- `target_times`: target simulation times for chronological ordering

## Training protocol

`scripts/train_stgnn.py` splits samples chronologically into train, validation, and test partitions. Feature normalization parameters are learned from training inputs only. It reports MAE and RMSE for the model, persistence, and moving-average baselines on validation and test windows, and saves the trained checkpoint plus a `.metrics.json` report.

Sliding windows overlap in their historical inputs by design. Targets are chronological and validation/test targets are not used for gradient updates. For stronger generalization evidence, evaluate the trained checkpoint on a different traffic seed or network, and report that result separately.

## Control integration

`--controller forecast-pressure --forecast-model models/stgnn.pt` loads the checkpoint and uses predicted intersection queue values to adjust the duration of a pressure-selected green phase. It does not replace the emergency manager, guarantee an optimal phase choice, or make the signal program safe by itself. The SUMO phase program remains responsible for the configured transition sequence.

Do not claim the ST-GNN improves control unless its test forecast error beats simple baselines and matched-seed traffic experiments show a benefit.
