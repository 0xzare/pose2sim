# -*- coding: utf-8 -*-
"""Subprocess runner: executes the Pose2Sim pipeline in its own process.

Why a process and not a QThread: Pose2Sim imports matplotlib with the
'qtagg' backend and opens Qt dialogs (calibration clicking, sync GUI).
Qt widgets and matplotlib-Qt figures may only live in the main thread.
Creating them inside a QThread gives:
  UserWarning: Starting a Matplotlib GUI outside of the main thread...
followed by a segfault. A QProcess isolates all of that safely and
additionally gives us a reliable Stop (kill).
"""
import argparse
import logging
import os
import sys
import time
import traceback
from pathlib import Path


def build_pipeline(proj: Path):
    from Pose2Sim.Pose2Sim import Pose2SimPipeline

    # NOTE: ignore inner folders (videos, calibration, ...) — a stray
    # Config.toml in there must never turn a trial into a "batch session".
    SKIP = {"videos", "calibration", "calib"}
    is_batch_root = any(
        (proj / d).is_dir() and (proj / d / "Config.toml").is_file()
        and d.lower() not in SKIP and not d.startswith(".")
        for d in os.listdir(proj)
    )
    if is_batch_root:
        print("batch session detected: expanding all trials", flush=True)
        try:
            return Pose2SimPipeline(None)
        except KeyError as e:
            raise SystemExit(
                f"INIT-ERROR: Config.toml has no [project] section: {proj}/Config.toml ({e})"
            )
    try:
        return Pose2SimPipeline(str(proj / "Config.toml"))
    except KeyError as e:
        raise SystemExit(
            f"INIT-ERROR: Config.toml has no [project] section: {proj}/Config.toml. "
            f"If this is a batch trial, select the session root instead. ({e})"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--steps", required=True, help="comma separated step names")
    args = ap.parse_args()

    proj = Path(args.project).expanduser().resolve()
    if not proj.is_dir():
        print(f"INIT-ERROR: project folder not found: {proj}", flush=True)
        return 2
    from GUI.config_io import validate_project
    check = validate_project(proj)
    hard = [m for m in check["missing"] if m in ("config", "videos")]
    if hard:
        hint = ""
        if check["suggest_parent"]:
            hint = f" Did you pick the '{proj.name}' subfolder? Select the project root instead."
        print(f"INIT-ERROR: Invalid project folder ({', '.join(hard)} missing).{hint}", flush=True)
        return 2

    os.chdir(proj)
    print(f"working dir: {proj}", flush=True)
    logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stdout, force=True)

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    if not steps:
        print("INIT-ERROR: no steps selected", flush=True)
        return 2

    try:
        pipe = build_pipeline(proj)
    except SystemExit as e:
        print(str(e), flush=True)
        return 2
    except Exception:
        traceback.print_exc()
        return 2

    t0 = time.time()
    last = "start"
    for i, step in enumerate(steps):
        print(f"\n—— {step} [{i+1}/{len(steps)}] ——", flush=True)
        print(f"STEP-START:{step}:{i}:{len(steps)}", flush=True)
        try:
            getattr(pipe, step)()
        except Exception as e:
            if step == "calibration" and "No file with" in str(e):
                print("HINT: no calibration source file found. If a Calib*.toml "
                      "already exists, just uncheck/skip the calibration step.",
                      flush=True)
            traceback.print_exc()
            print(f"STEP-ERROR:{step}", flush=True)
            return 1
        last = step
        print(f"STEP-DONE:{step}", flush=True)
    el = time.time() - t0
    h, r = divmod(int(el), 3600)
    m, s = divmod(r, 60)
    estr = f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"
    print(f"ALL-DONE:{estr}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
