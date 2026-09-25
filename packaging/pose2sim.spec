# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Pose2Sim GUI (Windows folder + macOS app, onedir).

Notes:
- onedir layout: dist/Pose2Sim/Pose2Sim(.exe). The Windows installer and
  the macOS .app both expect this layout.
- openvino is excluded: rtmlib only imports it inside the openvino-backend
  branch (default is onnxruntime), and its libtbb dylib breaks macOS
  ad-hoc codesigning ("internal error in Code Signing subsystem").
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hidden = collect_submodules("Pose2Sim") + collect_submodules("GUI") + [
    "rtoml", "opensim", "rtmlib",
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
    excludes=["tkinter", "matplotlib.tests", "scipy.tests", "pandas.tests",
              "openvino", "torch"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pose2Sim",
    console=False,  # windowed GUI; set True for debug
    icon=None,
    upx=False,  # UPX breaks onnxruntime/scipy
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="Pose2Sim",
)
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Pose2Sim.app", icon=None, bundle_identifier="com.pose2sim.gui")
