param(
    [string]$Dataset = '',
    [string]$SourceFont = '',
    [string]$Python = '',
    [int]$Epochs = 30,
    [int]$Batch = 16
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Dataset) {
    Write-Host 'First export a labelled glyph dataset from http://127.0.0.1:5173/font and extract it.'
    $Dataset = Read-Host 'Extracted dataset directory (contains manifest.jsonl)'
}
$Dataset = $Dataset.Trim().Trim('"')
if (-not (Test-Path -LiteralPath (Join-Path $Dataset 'manifest.jsonl'))) { throw 'No manifest.jsonl found. Unlabelled seal crops cannot be used as character labels.' }
if (-not $SourceFont) {
    $SourceFont = if ($env:FONT_CONTENT_FONT) { $env:FONT_CONTENT_FONT } else { 'C:/Windows/Fonts/NotoSansSC-VF.ttf' }
}
if (-not (Test-Path -LiteralPath $SourceFont)) { throw 'Pass -SourceFont with an existing Chinese content font. Use the same FONT_CONTENT_FONT in the web backend.' }
$candidates = @()
if ($Python) { $candidates = @($Python) }
else {
    if ($env:YINMAI_TRAIN_PYTHON) { $candidates += $env:YINMAI_TRAIN_PYTHON }
    $candidates += (Join-Path $projectRoot '.venv-gpu/Scripts/python.exe')
    $candidates += (Join-Path $projectRoot '../../work/gpu-training/Scripts/python.exe')
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }
}
$selected = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    & $candidate -c 'import torch, PIL, numpy, fontTools; raise SystemExit(0 if torch.cuda.is_available() else 2)' 2>$null
    if ($LASTEXITCODE -eq 0) { $selected = $candidate; break }
}
if (-not $selected) { throw 'A CUDA PyTorch environment with Pillow, numpy and fontTools is required. Pass -Python explicitly.' }
$runName = 'glyph-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6)
$output = Join-Path $projectRoot ('models/font-generation/' + $runName)
$logDir = Join-Path $projectRoot ('evidence/font-runs/' + $runName)
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$env:PYTHONIOENCODING = 'utf-8'
& $selected -u (Join-Path $projectRoot 'backend/training/train_font.py') --dataset $Dataset --source-font $SourceFont --out $output --epochs $Epochs --batch $Batch 2>&1 | Tee-Object -FilePath (Join-Path $logDir 'console.log')
if ($LASTEXITCODE -ne 0) { throw 'Glyph style training failed. Review the dataset labels and log.' }
Write-Host "Model saved: $output"
Write-Host 'Refresh http://127.0.0.1:5173/font and select the newly trained style.'
