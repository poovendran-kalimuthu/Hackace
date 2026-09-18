@echo off
echo Starting DocuCraft Pro Native Desktop GUI...
python run_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
