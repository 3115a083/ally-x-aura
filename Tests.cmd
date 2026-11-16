@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt -r requirements-test.txt
if errorlevel 1 exit /b 1
py -3 -m unittest discover -s tests -v
pause
