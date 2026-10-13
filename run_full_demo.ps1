$ErrorActionPreference = 'Stop'

# Run this script from the root of the upgraded DistrictPulse_Advanced project.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# This matches the SUMO installation path found on the user's Windows machine.
$env:SUMO_HOME = 'C:\Program Files (x86)\SUMO'
if (-not (Test-Path "$env:SUMO_HOME\bin\sumo.exe")) {
    throw "SUMO not found at $env:SUMO_HOME. Edit SUMO_HOME near the top of this script to match your installation."
}
if (-not (Test-Path "$env:SUMO_HOME\tools\randomTrips.py")) {
    throw "Cannot find tools\randomTrips.py under SUMO_HOME: $env:SUMO_HOME"
}
$env:Path = "$env:SUMO_HOME\bin;$env:Path"
$env:PYTHONPATH = "$env:SUMO_HOME\tools;$env:PYTHONPATH"

function Invoke-Python {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    Write-Host "`n>>> python $($Arguments -join ' ')" -ForegroundColor Cyan
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE. Fix the error above before continuing."
    }
}

Write-Host 'Checking SUMO and Python dependencies...' -ForegroundColor Yellow
& "$env:SUMO_HOME\bin\sumo.exe" --version
if ($LASTEXITCODE -ne 0) { throw 'SUMO version check failed.' }
& "$env:SUMO_HOME\bin\netgenerate.exe" --help *> $null
if ($LASTEXITCODE -ne 0) { throw 'netgenerate check failed.' }

Invoke-Python @('-c', 'import traci, sumolib; print("TraCI and sumolib OK")')
try {
    Invoke-Python @('-c', 'import numpy, pandas, matplotlib, pytest, torch; print("Dependencies OK; PyTorch", torch.__version__)')
} catch {
    Write-Host 'One or more project dependencies are missing. Installing requirements.txt...' -ForegroundColor Yellow
    Invoke-Python @('-m', 'pip', 'install', '-r', 'requirements.txt')
    Invoke-Python @('-c', 'import numpy, pandas, matplotlib, pytest, torch; print("Dependencies OK; PyTorch", torch.__version__)')
}

Invoke-Python @('-m', 'pytest', 'tests', '-q')
Invoke-Python @('-m', 'compileall', '-q', 'districtpulse', 'scripts')

$tag = Get-Date -Format 'yyyyMMdd_HHmmss'
$base = "results\demo_$tag"
$priority = "results\demo_priority_$tag"
$dataset = "data\graph_dataset_$tag.npz"
$model = "models\stgnn_$tag.pt"

Write-Host "`n[1/7] Generate the road network, synthetic traffic and ambulance route..." -ForegroundColor Green
Invoke-Python @('scripts\setup_demo.py', '--seed', '42', '--end', '1800')

Write-Host "`n[2/7] Run fixed-time, density, SMDP and Max-Pressure baselines..." -ForegroundColor Green
foreach ($controller in @('fixed', 'density', 'smdp', 'max-pressure')) {
    Invoke-Python @('scripts\run_experiment.py', '--scenario', 'data\demo', '--controller', $controller, '--seed', '42', '--end', '1800', '--results-dir', $base)
}

Write-Host "`n[3/7] Run every baseline with ambulance priority enabled..." -ForegroundColor Green
foreach ($controller in @('fixed', 'density', 'smdp', 'max-pressure')) {
    Invoke-Python @('scripts\run_experiment.py', '--scenario', 'data\demo', '--controller', $controller, '--seed', '42', '--end', '1800', '--emergency-priority', '--results-dir', $priority)
}

Write-Host "`n[4/7] Export graph-temporal training windows from the Max-Pressure state log..." -ForegroundColor Green
Invoke-Python @('scripts\export_graph_dataset.py', '--states', "$base\max-pressure_seed42\states.csv", '--network', 'data\demo\demo.net.xml', '--window', '12', '--horizon', '3', '--out', $dataset)

Write-Host "`n[5/7] Train ST-GNN and evaluate it against persistence/moving-average baselines..." -ForegroundColor Green
Invoke-Python @('scripts\train_stgnn.py', '--dataset', $dataset, '--epochs', '80', '--patience', '12', '--out', $model, '--seed', '42')

Write-Host "`n[6/7] Run forecast-aware pressure, with and without ambulance priority..." -ForegroundColor Green
Invoke-Python @('scripts\run_experiment.py', '--scenario', 'data\demo', '--controller', 'forecast-pressure', '--forecast-model', $model, '--seed', '42', '--end', '1800', '--results-dir', $base)
Invoke-Python @('scripts\run_experiment.py', '--scenario', 'data\demo', '--controller', 'forecast-pressure', '--forecast-model', $model, '--seed', '42', '--end', '1800', '--emergency-priority', '--results-dir', $priority)

Write-Host "`n[7/7] Build comparison tables and plots..." -ForegroundColor Green
Invoke-Python @('scripts\summarize_results.py', '--results', $base, '--out', "$base\comparison.csv")
Invoke-Python @('scripts\plot_results.py', '--csv', "$base\comparison.csv", '--out', "$base\comparison.png")
Invoke-Python @('scripts\summarize_results.py', '--results', $priority, '--out', "$priority\comparison.csv")
Invoke-Python @('scripts\plot_results.py', '--csv', "$priority\comparison.csv", '--out', "$priority\comparison.png")

Write-Host "`nDEMO RUNS COMPLETE" -ForegroundColor Green
Write-Host "Baseline comparison: $base\comparison.csv"
Write-Host "Baseline plot:       $base\comparison.png"
Write-Host "Priority comparison: $priority\comparison.csv"
Write-Host "ST-GNN metrics:      ${model}.metrics.json"
Write-Host "ST-GNN checkpoint:   $model"
Write-Host "`nNext: use the checkpoint path above to launch the visual SUMO-GUI demo with forecast-aware control + emergency priority."
