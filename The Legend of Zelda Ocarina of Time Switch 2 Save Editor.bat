@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw oot_save_editor.py & exit /b)
where pyw >nul 2>nul && (start "" pyw oot_save_editor.py & exit /b)
where python >nul 2>nul && (start "" python oot_save_editor.py & exit /b)
where py >nul 2>nul && (start "" py oot_save_editor.py & exit /b)
echo Python 3 is required. Download it from https://www.python.org/downloads/
pause
