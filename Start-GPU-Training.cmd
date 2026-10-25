@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\train-gpu.ps1" %*
if errorlevel 1 echo Training failed. Read the message above.
pause
