$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$localPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
$workspacePython = Join-Path $projectRoot '../../work/venv/Scripts/python.exe'
if (Test-Path -LiteralPath $localPython) { $pythonExe = $localPython }
elseif (Test-Path -LiteralPath $workspacePython) { $pythonExe = $workspacePython }
else { $pythonExe = (Get-Command python -ErrorAction Stop).Source }
& $pythonExe (Join-Path $PSScriptRoot 'dev.py') start
if ($LASTEXITCODE -ne 0) { throw 'Local startup failed. Read runtime logs or README.' }
