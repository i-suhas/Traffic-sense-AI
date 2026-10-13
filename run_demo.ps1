$ErrorActionPreference = "Stop"
if (-not $env:SUMO_HOME) { throw "Set SUMO_HOME to your SUMO installation directory first." }
if (-not (Test-Path "$env:SUMO_HOME\tools\randomTrips.py")) { throw "SUMO_HOME does not contain tools\randomTrips.py." }
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest tests -q
python scripts\setup_demo.py --seed 42 --end 1800
python scripts\run_experiment.py --scenario data\demo --controller fixed --seed 42 --results-dir results\quickstart
python scripts\run_experiment.py --scenario data\demo --controller density --seed 42 --results-dir results\quickstart
python scripts\run_experiment.py --scenario data\demo --controller smdp --seed 42 --results-dir results\quickstart
python scripts\run_experiment.py --scenario data\demo --controller max-pressure --seed 42 --results-dir results\quickstart
python scripts\run_experiment.py --scenario data\demo --controller max-pressure --seed 42 --emergency-priority --results-dir results\quickstart_priority
python scripts\summarize_results.py --results results\quickstart --out results\quickstart_comparison.csv
python scripts\plot_results.py --csv results\quickstart_comparison.csv --out results\quickstart_comparison.png
