param([string]$Source='', [string]$Out='', [string]$Layout='auto', [string]$Polarity='auto', [string]$Python='', [int]$Workers=4)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
if(-not $Source){
    $sourceCandidates=@((Join-Path $projectRoot 'training-data/images'),(Join-Path $projectRoot '../yinmai-training-data/images'))
    if($env:FONT_MATERIALS_DIR){$sourceCandidates=@($env:FONT_MATERIALS_DIR)+$sourceCandidates}
    foreach($path in $sourceCandidates){if(Test-Path -LiteralPath $path -PathType Container){$Source=$path;break}}
}
if(-not $Source){$Source=Read-Host 'Original material directory'}
$Source=$Source.Trim().Trim('"')
if(-not (Test-Path -LiteralPath $Source -PathType Container)){throw 'Material directory not found'}
if(-not $Out){$Out=Join-Path (Split-Path -Parent $projectRoot) ('yinmai-segmentation-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,6))}
$candidates=@()
if($Python){$candidates=@($Python)}else{
    $candidates+=Join-Path $projectRoot '.venv/Scripts/python.exe'
    $candidates+=Join-Path $projectRoot '../../work/venv/Scripts/python.exe'
    $command=Get-Command python -ErrorAction SilentlyContinue
    if($command){$candidates+=$command.Source}
}
$selected=$null
foreach($candidate in ($candidates|Select-Object -Unique)){
    if(-not (Test-Path -LiteralPath $candidate -PathType Leaf)){continue}
    & $candidate -c 'import cv2, PIL, numpy, pydantic' 2>$null
    if($LASTEXITCODE -eq 0){$selected=$candidate;break}
}
if(-not $selected){throw 'Install backend/requirements.txt in your project environment or pass -Python. GPU is not required for segmentation.'}
$env:PYTHONIOENCODING='utf-8'
& $selected -u (Join-Path $projectRoot 'backend/training/segment_materials.py') --source $Source --out $Out --layout $Layout --polarity $Polarity --workers $Workers
if($LASTEXITCODE -ne 0){throw 'Segmentation failed; inspect the message above. Original images have not been modified.'}
Write-Host "Review results: $Out/index.html"
