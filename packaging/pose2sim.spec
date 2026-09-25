# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Pose2Sim GUI (Windows exe + macOS app)."""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Heavy scientific stack: keep binaries, drop tests
hidden = collect_submodules("Pose2Sim") + collect_submodules("GUI") + [
    "rtoml", "opensim", "rtmlib", "scipy", "sklearn", "pandas",
]
datas = []
datas += collect_data_files("Pose2Sim", includes=["Demo_SinglePerson/**", "OpenSim_Setup/**", "MarkerAugmenter/**"])
datas += collect_data_files("opensim", includes=["**/*.xml", "**/*.osim", "**/Geometry/**"])

a = Analysis(
    ["../GUI/main.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    excludes=["tkinter", "matplotlib.tests", "scipy.tests", "pandas.tests"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="Pose2Sim",
    console=False,  # windowed GUI; set True for debug
    icon=None,
    upx=False,  # UPX breaks onnxruntime/scipy on Win
)
if sys.platform == "darwin":
    app = BUNDLE(exe, name="Pose2Sim.app", icon=None, bundle_identifier="com.pose2sim.gui")
