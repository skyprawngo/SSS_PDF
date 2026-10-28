@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 run.py %*
) else (
    python run.py %*
)
if errorlevel 1 pause
