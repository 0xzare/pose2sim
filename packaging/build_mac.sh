#!/bin/bash
# Build Pose2Sim GUI app on macOS (Apple Silicon / Intel)
# Output: dist/Pose2Sim.app ; optional DMG
set -e
cd "$(dirname "$0")/.."

uv venv .venv-gui --python 3.12 || true
source .venv-gui/bin/activate
uv pip install -e .[gui] pyinstaller

pyinstaller packaging/pose2sim.spec --noconfirm --clean

echo "APP ready at dist/Pose2Sim.app"
# Optional DMG:
# hdiutil create -volname Pose2Sim -srcfolder dist/Pose2Sim.app -ov -format UDZO dist/Pose2Sim-mac.dmg
# echo "DMG at dist/Pose2Sim-mac.dmg"
