@echo off
REM One-click NEPSE dataset update.
REM 1. Put new day files (named YYYY-MM-DD.csv) into backend\data\raw\
REM 2. Double-click this file (or run it from a terminal).
REM Rebuilds the parquet + market summary; the running app picks up the new data automatically.

cd /d "%~dp0backend"
python scripts\update_dataset.py %*

echo.
echo ============================================================
echo Update finished. You can close this window.
echo ============================================================
pause
