@echo off
REM Build Pose2Sim GUI exe on Windows 10/11 (run inside repo root)
REM Requires: Python 3.11-3.13, uv, ~20 GB free (full install ~14 GB)

uv venv .venv-gui --python 3.12
call .venv-gui\Scripts\activate
uv pip install -e .[gui] pyinstaller

pyinstaller packaging\pose2sim.spec --noconfirm --clean

echo.
echo EXE ready at dist\Pose2Sim\Pose2Sim.exe
echo Next: compile installer with Inno Setup:
echo   iscc packaging\windows_installer.iss
pause
