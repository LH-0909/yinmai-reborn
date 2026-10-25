@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\train-font.ps1" %*
pause
