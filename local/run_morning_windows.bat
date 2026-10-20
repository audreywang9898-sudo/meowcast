@echo off
cd /d "%~dp0.."
set CITY=taipei
set MEOWCAST_PERIOD=morning
where python >nul 2>&1 || (echo Please install Python 3.12 and add it to PATH.& pause & exit /b 1)
where ffmpeg >nul 2>&1 || (echo Please install FFmpeg and add it to PATH.& pause & exit /b 1)
python -c "import PIL, requests, lunar_python" >nul 2>&1 || (echo Installing Python dependencies... & python -m pip install -r requirements.txt)
python render.py
if errorlevel 1 (echo Generation failed. See errors above.& pause & exit /b 1)
echo READY: output\meowcast.mp4 and output\caption.txt
explorer output
pause
