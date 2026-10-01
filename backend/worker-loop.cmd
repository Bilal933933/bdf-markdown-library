@echo off
REM DCE worker watchdog — restarts the worker whenever it exits.
:loop
uv run python -m app.worker
timeout /t 5 >nul
goto loop
