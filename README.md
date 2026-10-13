# DistrictPulse AI (Research MVP)

**Mysuru OSM + SUMO/TraCI + variable-duration SMDP control + spatial-temporal prediction scaffold**

This is an executable research MVP, not a claim that the proposed ST-GNN has already beaten baselines. It provides a reproducible SUMO experiment harness, fixed-time/density/SMDP controllers, SMDP transition logging with duration-aware discounting, a PyTorch graph-temporal model and training script, metrics, experiment manifest, and a publication checklist.

## What is implemented
- SUMO microscopic simulation controlled through TraCI.
- A small generated-grid scenario for smoke tests, plus an optional OSM-derived Mysuru pilot network.
- Three controllers: `fixed`, `density`, and `smdp`.
- Variable green extension decisions selected only while the active signal phase is green; SUMO's programmed yellow/all-red transitions remain in control.
- SMDP transition records include state, action duration, accumulated reward, next state, and `gamma ** duration` update.
- Network-level metrics from SUMO tripinfo and per-step detector/state logs.
- A graph-temporal neural predictor (GCN-style spatial aggregation + GRU temporal encoder) and a training script for predicting future queue pressure from collected state CSVs. The predictor is an optional research component and is **not automatically used as a trained model** until trained and evaluated.
- Run manifest with seed/configuration to aid reproducibility.

## What is not claimed
- OSM road geometry is not observed traffic volume. RandomTrips demand is synthetic until calibrated with counts.
- The ST-GNN is an architecture/training scaffold. Do not claim predictive accuracy before held-out evaluation.
- No result is guaranteed to improve waiting time. Run multiple seeds and compare baselines.
- A simulation experiment does not prove Nash-equilibrium convergence. Present that as a formal-theory claim only if you provide a valid proof under stated assumptions.

## Requirements
- Windows 10/11 + VS Code or Linux.
- SUMO installed, with `sumo`, `netgenerate`, `netconvert`, and SUMO tools available. Official docs: https://sumo.dlr.de/docs/Installing/ .
- Python 3.10+ recommended (Python 3.12 works with current compatible packages).

## Windows setup (PowerShell in VS Code)

1. Install SUMO. Locate its installation folder, commonly `C:\Program Files (x86)\Eclipse\Sumo` or `C:\Program Files\Eclipse\Sumo`.
2. Set paths for this terminal (change the path if yours differs):

```powershell
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
$env:Path += ";$env:SUMO_HOME\bin"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
sumo --version
netgenerate --help
```

If `sumo` is not recognized, find `sumo.exe` in your installation and correct `SUMO_HOME`/`Path`. SUMO tools are usually under `$env:SUMO_HOME\tools`.

3. Generate and smoke-test a deterministic 3x3 grid scenario:

```powershell
python scripts\setup_demo.py --seed 42
python scripts\run_experiment.py --scenario data\demo --controller fixed --seed 42
python scripts\run_experiment.py --scenario data\demo --controller density --seed 42
python scripts\run_experiment.py --scenario data\demo --controller smdp --seed 42
python scripts\summarize_results.py --results results
```

Each run writes to `results/<controller>_seed<seed>/`, including `states.csv`, `smdp_transitions.csv` (for SMDP), `tripinfo.xml`, `metrics.json`, and `manifest.json`.

4. Compare several seeds, not just one:

```powershell
python scripts\run_batch.py --scenario data\demo --controllers fixed density smdp --seeds 11 22 33 44 55
python scripts\summarize_results.py --results results
```

## Mysuru OSM pilot

The included bounding box is a **small pilot area in central Mysuru**, not the whole city. OSM is downloaded from the public Overpass API and can fail due to service limits/network conditions. Be respectful of OSM services.

```powershell
python scripts\download_osm.py --bbox 76.625,12.285,76.685,12.335
python scripts\build_osm_network.py --osm data\mysuru.osm.xml --out data\mysuru_pilot
python scripts\generate_osm_demand.py --net data\mysuru_pilot.net.xml --out data\mysuru_pilot --period 3.0 --end 1800
python scripts\run_experiment.py --scenario data\mysuru_pilot --controller smdp --seed 42 --end 1800
```

If `netconvert` fails, inspect `data/mysuru_pilot.netconvert.log`; OSM data may include unusual road attributes or incomplete junction geometry. First validate the generated-grid scenario before debugging OSM.

## Graph-temporal model

After a simulation run, collect multiple scenarios/seeds. The training utility converts time-ordered per-intersection queue-pressure data into windows. It needs a consistent intersection order and adjacency matrix. For the initial MVP, the script supports an adjacency CSV supplied by the user; see `docs/STGNN.md`.

```powershell
python scripts\export_graph_dataset.py --states results\smdp_seed42\states.csv --out data\graph_dataset.npz --adjacency configs\adjacency_example.csv
python scripts\train_stgnn.py --dataset data\graph_dataset.npz --epochs 40
```

A trained model must be tested on **held-out seeds/scenarios** before any forecast claim. Integration of the trained forecast into the control policy is a later ablation, not silently enabled in the baseline controller.

## Metrics and scientific protocol
- Primary: mean trip duration / travel time from `tripinfo.xml`; accumulated waiting time if supported by your SUMO version; mean/max queue proxy and halting counts from `states.csv`.
- Safety: phase-change validity (SUMO phase program preserved), max red time, emergency priority (not implemented in this MVP; future work), pedestrian delay (future work).
- Use paired seeds/demand scenarios across all controllers, report mean ± standard deviation and confidence intervals. Do not compare runs with different demand seeds.
- Baselines: fixed-time, density-responsive, SMDP without graph forecasting, full ST-GNN+SMDP after integration.
- Ablations: remove spatial aggregation; remove temporal encoder; fixed versus variable duration; local state versus upstream-neighbor state.

## Suggested paper framing
**Title:** *Anticipating Congestion Surges: A Spatio-Temporal Graph Neural Network and Semi-Markov Framework for Multi-Agent Traffic Signal Control*

At the current code stage, describe it as an empirical simulation study of variable-duration SMDP control, with a graph-temporal predictor under development. Do not report fabricated improvements or say the complete ST-GNN controller is implemented. The paper checklist is in `docs/PUBLICATION_PLAN.md`.

## Clean and repeatable experiment runs

The runner preserves existing output by default. Each controller/seed writes to
`results/<controller>_seed<seed>/`. If that exact folder already exists, the
runner stops instead of silently mixing or deleting results.

To replace only the SMDP seed-42 run:

```powershell
python scripts/run_experiment.py --scenario data/demo --controller smdp --seed 42 --overwrite
```

To keep old runs and write into a separate folder:

```powershell
python scripts/run_experiment.py --scenario data/demo --controller smdp --seed 42 --results-dir results/revised
```

A clean comparison workflow (after setting up the demo network) is:

```powershell
python scripts/run_experiment.py --scenario data/demo --controller fixed --seed 42
python scripts/run_experiment.py --scenario data/demo --controller density --seed 42
python scripts/run_experiment.py --scenario data/demo --controller smdp --seed 42
python scripts/summarize_results.py --results results
python scripts/plot_results.py
```

Use `--overwrite` only when you intentionally want to replace a specific
controller/seed folder. This runner does not delete the entire results directory.
