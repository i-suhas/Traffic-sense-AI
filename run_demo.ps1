$ErrorActionPreference = "Stop"
if (-not $env:SUMO_HOME) { throw "Set SUMO_HOME to your SUMO installation directory first." }
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\setup_demo.py --seed 42
python scripts\run_experiment.py --scenario data\demo --controller fixed --seed 42
python scripts\run_experiment.py --scenario data\demo --controller density --seed 42
python scripts\run_experiment.py --scenario data\demo --controller smdp --seed 42
python scripts\summarize_results.py --results results
