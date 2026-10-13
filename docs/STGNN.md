# ST-GNN component: data contract and next integration step

## Model currently supplied
`SpatialTemporalNet` uses normalized one-hop graph aggregation, then a GRU over each node's historical queue-pressure series. It is a compact graph-temporal predictor suitable as a starting baseline, not a reproduction of every STGCN variant.

## Data contract
- `X`: `[samples, history_steps, intersections, features]`
- `y`: `[samples, intersections, 1]`, queue pressure at a future horizon
- `A`: `[intersections, intersections]`, adjacency aligned with `node_ids`
- `node_ids`: sorted TLS IDs used in each state log

The example adjacency file is illustrative only. Build a real adjacency matrix from network connectivity: two signalized intersections should be adjacent if a directed road/path connects them within the chosen neighborhood rule. Do not use the four-node example for Mysuru.

## Evaluation
Use chronological or scenario-level train/validation/test splits. Prefer holding out whole demand seeds and/or parts of the network to test generalization. Report MAE/RMSE against persistence and simple moving-average predictors. Normalize inputs using training data only. Include a leakage audit: no future features may enter a window.

## Integrating forecasts into control
Only after validation, load the checkpoint in the controller and append forecast queue pressure for the current and upstream intersections to the SMDP state. Compare:
1. local density controller;
2. local SMDP;
3. SMDP with neighbor state but no learned predictor;
4. ST-GNN forecast + SMDP.

This integration is intentionally separated so an untrained/random neural network never silently controls signals.
