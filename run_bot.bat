@echo off
echo Starting Nico Robin Bot...
echo.

REM Try different Python installations
echo Trying WinPython...
"C:\Users\sahoo\winpython\WPy64-31201b5\python-3.12.0.amd64\python.exe" --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using WinPython installation
    "C:\Users\sahoo\winpython\WPy64-31201b5\python-3.12.0.amd64\python.exe" init_database.py
    if %ERRORLEVEL% EQU 0 (
        echo Database initialized successfully!
        "C:\Users\sahoo\winpython\WPy64-31201b5\python-3.12.0.amd64\python.exe" main.py
    ) else (
        echo Database initialization failed!
    )
    goto :end
)

echo Trying system Python...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using system Python
    python init_database.py
    if %ERRORLEVEL% EQU 0 (
        echo Database initialized successfully!
        python main.py
    ) else (
        echo Database initialization failed!
    )
    goto :end
)

echo Trying Python from AppData...
"C:\Users\sahoo\AppData\Local\Programs\Python\Python314\python.exe" --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using Python from AppData
    "C:\Users\sahoo\AppData\Local\Programs\Python\Python314\python.exe" init_database.py
    if %ERRORLEVEL% EQU 0 (
        echo Database initialized successfully!
        "C:\Users\sahoo\AppData\Local\Programs\Python\Python314\python.exe" main.py
    ) else (
        echo Database initialization failed!
    )
    goto :end
)

echo No Python installation found!
echo Please install Python 3.11+ and try again.

:end
pause
