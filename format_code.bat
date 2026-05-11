@echo off
echo Formatting code with black...

REM Try different Python installations
echo Trying WinPython...
"C:\Users\sahoo\winpython\WPy64-31201b5\python-3.12.0.amd64\python.exe" -m black . 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Code formatted successfully with WinPython!
    goto :end
)

echo Trying system Python...
python -m black . 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Code formatted successfully with system Python!
    goto :end
)

echo Trying Python from AppData...
"C:\Users\sahoo\AppData\Local\Programs\Python\Python314\python.exe" -m black . 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Code formatted successfully with Python from AppData!
    goto :end
)

echo No Python installation found or black not available!
echo Please install black: pip install black

:end
pause
