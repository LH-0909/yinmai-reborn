param(
    [string]$Python = '',
    [string]$DataDir = '',
    [int]$Epochs = 5,
    [int]$Steps = 0,
    [int]$Batch = 16,
    [int]$TrainImages = 2048,
    [int]$EvalImages = 128,
    [switch]$FullDataset,
    [switch]$Smoke
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$candidates = @()
if ($Python) { $candidates = @($Python) }
else {
    if ($env:YINMAI_TRAIN_PYTHON) { $candidates += $env:YINMAI_TRAIN_PYTHON }
    $candidates += (Join-Path $projectRoot '.venv-gpu/Scripts/python.exe')
    $candidates += (Join-Path $projectRoot '../../work/gpu-training/Scripts/python.exe')
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }
}
$selectedPython = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    & $candidate -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 2)' 2>$null
    if ($LASTEXITCODE -eq 0) { $selectedPython = $candidate; break }
}
if (-not $selectedPython) { throw 'No CUDA PyTorch environment found. Pass -Python to your CUDA Python executable. CPU fallback is disabled.' }
$launchArgs = @((Join-Path $projectRoot 'backend/training/launch_gpu.py'), '--epochs', "$Epochs", '--batch', "$Batch", '--train-images', "$TrainImages", '--eval-images', "$EvalImages")
if ($DataDir) { $launchArgs += @('--data', $DataDir) }
if ($Steps -gt 0) { $launchArgs += @('--steps', "$Steps") }
if ($FullDataset) { $launchArgs += '--full' }
if ($Smoke) { $launchArgs += '--smoke' }
& $selectedPython -u @launchArgs
if ($LASTEXITCODE -ne 0) { throw 'GPU training failed. See the run console.log and the message above.' }
