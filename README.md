# DistrictPulse AI

### Emergency-Aware Adaptive Traffic Signal Control with Max-Pressure, SMDP Learning, and Spatio-Temporal Graph Forecasting

DistrictPulse AI is a SUMO/TraCI-based research project for
experimenting with adaptive traffic-signal control. It brings together
conventional and traffic-responsive baselines, variable-duration
Semi-Markov Decision Process (SMDP) learning, queue-pressure control,
emergency-vehicle priority, and a spatio-temporal graph neural network
(ST-GNN) workflow.

The goal is to evaluate these components under reproducible traffic
simulations, not to assume that a more complex controller is
automatically better.

> **Research integrity:** Report a feature as implemented only when its
> code path is present and tested in the checked-out version. Report
> model accuracy and traffic improvements only from saved, reproducible
> experiments. Keep baseline, ablation, and multi-seed results separate.

------------------------------------------------------------------------

## Highlights

-   **SUMO microscopic simulation + TraCI** for closed-loop signal
    control.
-   **Multiple controller baselines:** fixed-time, density-responsive,
    SMDP Q-learning, and Max-Pressure where registered in the current
    runner.
-   **Emergency-vehicle priority:** emergency route/approach detection,
    safe compatible phase selection, and restoration of normal control
    after the vehicle passes, when the emergency-control module is
    enabled.
-   **Variable-duration SMDP control:** duration-aware transitions and
    discounting.
-   **ST-GNN queue forecasting:** graph-based spatial aggregation and
    recurrent temporal modelling for future queue-pressure prediction.
-   **Forecast-aware pressure control:** an experimental extension that
    combines predicted traffic pressure with Max-Pressure, kept separate
    from emergency safety/priority logic.
-   **Experiment artifacts:** per-step state logs, trip information,
    metrics, and run manifests.
-   **Reproducible comparisons:** common traffic-demand seeds and
    multiple-seed summaries.

**Before publishing results:** verify that the controller names and
optional features below match the actual files and command-line options
in your checkout. Do not describe an optional component as active in an
experiment unless that run actually used it.

## Problem statement

Fixed-time traffic lights use a preset schedule even when traffic demand
changes. Local density-only decisions can react to nearby queues but may
overlook downstream blocking or wider network conditions. Learning-based
and forecast-informed approaches may improve decisions, but they also
introduce complexity and require careful validation.

DistrictPulse AI provides a simulation framework to compare these
approaches and investigate three related questions:

1.  Can traffic-responsive signal control reduce travel delay against a
    fixed-time baseline?
2.  Can Max-Pressure and variable-duration SMDP control manage queues
    effectively under changing demand?
3.  Can a validated graph-temporal queue forecast improve control
    decisions, while emergency priority remains safe and independently
    evaluated?

## Architecture

``` text
SUMO network + traffic demand
            |
            v
       SUMO / TraCI
            |
            v
   State and detector collection
            |
            +-------------------------------+
            |               |               |
            v               v               v
       Fixed-time       Density-based    SMDP Q-learning
                                            |
                                            v
                                     Variable green time

Queue state + road graph
            |
            v
       ST-GNN predictor
            |
            v
   Forecast queue pressure
            |
            v
 Forecast-aware Max-Pressure (experimental)

Emergency vehicle detection
            |
            v
 Safe phase compatibility / priority
            |
            v
 Resume ordinary controller after passage

All experiments -> metrics, state logs, tripinfo, manifests
```

Emergency priority is a safety-sensitive override. It should not bypass
SUMO's required yellow/all-red transitions or grant conflicting
movements simultaneously. Keep it as a distinct control layer so
ordinary traffic-policy performance can be evaluated separately.

## Controller descriptions

  -----------------------------------------------------------------------
  Controller                          Purpose
  ----------------------------------- -----------------------------------
  `fixed`                             Fixed-time signal schedule baseline

  `density`                           Responds to observed local traffic
                                      density

  `smdp`                              Duration-aware Q-learning baseline

  `pressure`                          Max-Pressure control based on
                                      upstream queues and downstream
                                      capacity/occupancy

  Forecast-aware pressure             Experimental pressure policy that
                                      uses validated predicted queue
                                      values

  Emergency priority                  Safety-constrained priority
                                      override for an approaching
                                      emergency vehicle
  -----------------------------------------------------------------------

Controller identifiers are implementation-dependent. Confirm the names
supported by the local runner with
`python scripts\run_experiment.py --help`.

## Emergency-vehicle priority

The emergency-aware workflow should:

1.  Define a reproducible emergency vehicle type and route in the
    scenario-generation script.
2.  Detect the vehicle's route and approach to a controlled junction.
3.  Select a signal phase compatible with the emergency movement.
4.  Preserve SUMO's safe transition sequence, including yellow and
    all-red where configured.
5.  Track passage through the junction and release priority after the
    vehicle clears the conflict area.
6.  Return control to the normal controller without leaving a signal in
    an invalid or unsafe state.
7.  Log detection time, priority activation/release, emergency travel
    time, and delay.

Evaluate emergency response alongside ordinary traffic. Report emergency
delay and ordinary-vehicle delay separately, because priority may help
the emergency vehicle while increasing delay elsewhere.

Do not claim emergency support is active in a published build unless the
scenario generator, manager/controller integration, and tests are
present.

## Max-Pressure control

Max-Pressure selects a feasible signal phase using pressure across
movements. A typical movement pressure is derived from the upstream
queue and the downstream queue or capacity term. The phase score
aggregates pressure for movements served by that phase.

A practical implementation must map SUMO lanes and connections to signal
phases correctly, handle absent or invalid lane data, and choose only
phases that are compatible with the signal program. Pressure control
should be evaluated against fixed-time and density baselines under the
same demand seeds.

## ST-GNN queue forecasting

The graph-temporal model uses spatial relationships between
intersections and temporal history to predict future queue pressure. The
research workflow should include:

-   A stable intersection ordering and matching adjacency matrix.
-   Time-ordered state collection across multiple runs.
-   Chronological train, validation, and test partitions.
-   No future-data leakage through overlapping windows, normalization,
    or feature construction.
-   Persistence and moving-average baselines.
-   MAE and RMSE on held-out seeds/scenarios.
-   Saved model configuration, data split details, seed, and evaluation
    metrics.

A GCN-style graph aggregation layer with a GRU temporal encoder is one
possible model design. The trained predictor must beat simple baselines
on held-out data before its forecasts are used to influence signal
control.

## Forecast-aware Max-Pressure

Forecast-aware pressure is an experimental extension, not an assumed
default. It should use queue forecasts only after the ST-GNN has passed
held-out evaluation. Keep emergency priority and safety constraints
separate from the forecast score.

Recommended ablations:

1.  Fixed-time versus density-based control.
2.  Density-based versus Max-Pressure.
3.  Max-Pressure versus SMDP.
4.  Observed-state Max-Pressure versus forecast-aware Max-Pressure.
5.  Forecast-aware control with and without spatial graph information.
6.  Emergency priority enabled versus disabled, using the same demand
    seeds.

This structure helps identify whether a measured change comes from the
forecast, the controller, or emergency priority.

## Requirements

-   Windows 10/11 with VS Code PowerShell, or Linux.
-   SUMO installed with `sumo`, `netgenerate`, `netconvert`, and the
    SUMO `tools` directory.
-   Python version supported by the packages in `requirements.txt`
    (Python 3.10+ recommended).
-   Python packages from `requirements.txt`.

Official SUMO installation guide: https://sumo.dlr.de/docs/Installing/

## Windows setup

Run commands from the repository root.

### 1. Configure SUMO

Find the folder containing `bin\sumo.exe`. For this Windows setup, the
installation was found at:

``` powershell
$env:SUMO_HOME = "C:\Program Files (x86)\SUMO"
$env:Path = "$env:SUMO_HOME\bin;$env:Path"
$env:PYTHONPATH = "$env:SUMO_HOME\tools;$env:PYTHONPATH"
```

If SUMO is installed elsewhere, change the path. Verify:

``` powershell
& "$env:SUMO_HOME\bin\sumo.exe" --version
Test-Path "$env:SUMO_HOME\bin\netgenerate.exe"
python -c "import traci, sumolib; print('TraCI and sumolib imports successful')"
```

### 2. Create the Python environment

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the environment is already activated, use it instead of creating
another. Do not commit `.venv`, `venv`, caches, or generated simulation
outputs.

## Run the generated-grid experiment

First inspect the actual supported options:

``` powershell
python scripts\setup_demo.py --help
python scripts\run_experiment.py --help
```

Then generate the demo scenario and run baseline experiments using the
arguments supported by your checkout. The following commands reflect the
intended interface:

``` powershell
python scripts\setup_demo.py --seed 42

python scripts\run_experiment.py --scenario data\demo --controller fixed --seed 42
python scripts\run_experiment.py --scenario data\demo --controller density --seed 42
python scripts\run_experiment.py --scenario data\demo --controller smdp --seed 42
python scripts\run_experiment.py --scenario data\demo --controller pressure --seed 42

python scripts\summarize_results.py --results results
```

Run the pressure or emergency-enabled experiment only if that controller
is registered and the required scenario assets exist. Check `--help` if
the local CLI differs.

## Emergency scenario experiment

After confirming that emergency route generation and priority control
are implemented, generate the scenario using the project's setup script
and run the documented emergency-aware experiment. Record the exact
seed, emergency departure time, route, detection point, priority
activation/release times, and signal phase decisions.

Do not invent an emergency-controller command-line flag. Discover
supported flags using:

``` powershell
python scripts\setup_demo.py --help
python scripts\run_experiment.py --help
```

## Multi-seed evaluation

Use the same set of seeds and matching demand configurations for each
controller. If the batch runner supports the following interface:

``` powershell
python scripts\run_batch.py --scenario data\demo --controllers fixed density smdp pressure --seeds 11 22 33 44 55
python scripts\summarize_results.py --results results
```

Report mean and standard deviation, and preferably confidence intervals.
Include all seeds and document failed runs. A single seed is a smoke
test, not evidence of a general performance improvement.

## ST-GNN dataset and training

Check the repository-specific instructions first:

``` powershell
Get-Content docs\STGNN.md
python scripts\export_graph_dataset.py --help
python scripts\train_stgnn.py --help
```

An intended workflow may look like:

``` powershell
python scripts\export_graph_dataset.py --states results\smdp_seed42\states.csv --out data\graph_dataset.npz --adjacency configs\adjacency_example.csv
python scripts\train_stgnn.py --dataset data\graph_dataset.npz --epochs 40
```

Use these example arguments only if the local scripts support them. The
dataset should cover multiple runs and preserve a consistent node order.
Evaluate the trained model on held-out seeds/scenarios and compare
MAE/RMSE with persistence and moving-average baselines before connecting
it to forecast-aware pressure control.

## Metrics to report

  -----------------------------------------------------------------------
  Metric                              Why it matters
  ----------------------------------- -----------------------------------
  Mean trip duration                  Overall travel efficiency

  Mean waiting time                   Driver delay

  Time loss                           Delay relative to ideal travel

  Mean and maximum queues             Congestion by approach

  Halting vehicles                    Stopped traffic

  Throughput                          Completed trips over the evaluation
                                      window

  Emergency-vehicle delay             Response performance for emergency
                                      trips

  Ordinary-vehicle delay during       Traffic cost of emergency
  priority                            intervention

  Forecast MAE / RMSE                 ST-GNN predictive accuracy
  -----------------------------------------------------------------------

Use consistent warm-up periods, evaluation windows, demand seeds,
network configurations, and metric definitions.

## Output files and reproducibility

Depending on the selected controller and scripts, a run may produce:

-   `states.csv` for time-series traffic states.
-   `smdp_transitions.csv` for SMDP transition records.
-   `tripinfo.xml` for trip-level outcomes.
-   `metrics.json` for summarized metrics.
-   `manifest.json` for seed and configuration details.
-   ST-GNN dataset, checkpoint, and evaluation outputs.

The experiment runner may refuse to overwrite an existing
controller/seed directory. Inspect supported options with
`python scripts\run_experiment.py --help`. Prefer a new output directory
for revised experiments; use an overwrite option only if the current
runner supports it and replacing that run is intentional.

## Testing

Run the test suite from the repository root:

``` powershell
python -m pytest -q
```

Also perform simulation smoke tests for every registered controller. For
emergency priority, test detection, phase compatibility, passage
detection, release of priority, and restoration of ordinary control. For
ST-GNN, test split boundaries, tensor shapes, baseline calculations, and
evaluation on held-out data.


*Emergency-Aware Adaptive Traffic Signal Control with Max-Pressure,
Semi-Markov Learning, and Spatio-Temporal Graph Forecasting*



## Data attribution

For OSM-derived networks and data, follow OpenStreetMap attribution
requirements: https://www.openstreetmap.org/copyright
