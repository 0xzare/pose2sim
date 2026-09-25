# -*- coding: utf-8 -*-
"""QProcess-based pipeline runner (no QThread).

Pose2Sim uses matplotlib-Qt + Qt dialogs; those must live in the main
thread of their process. Running them in a QThread segfaults. So the GUI
spawns `python -u -m GUI.runner` as a child process and streams its output.
"""
import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from .translations import STEP_ORDER


class PipelineWorker(QObject):
    log_line = Signal(str)
    step_started = Signal(str, int, int)
    step_finished = Signal(str)
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str, str)
    stopped = Signal(str)

    def __init__(self):
        super().__init__()
        self._stop = False
        self.project_dir = ""
        self.steps = {}
        self.proc = None
        self._buf = ""
        self._errored = False
        self._last = "start"

    def configure(self, project_dir: str, steps: dict):
        self.project_dir = project_dir
        self.steps = dict(steps)
        self._stop = False
        self._errored = False
        self._last = "start"
        self._buf = ""

    def request_stop(self):
        self._stop = True
        self.log_line.emit("… stop requested, killing pipeline …")
        if self.proc is not None:
            try:
                self.proc.kill()
            except Exception:
                pass

    @staticmethod
    def check_deps() -> tuple[bool, str]:
        # Light import only; Pose2Sim.Pose2Sim top-level has no matplotlib.
        try:
            import Pose2Sim.Pose2Sim  # noqa
            return True, ""
        except Exception as e:
            return False, f"{e}"

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.NotRunning

    def start(self):
        selected = [s for s in STEP_ORDER if self.steps.get(s)]
        if not selected:
            self.error.emit("init", "no steps selected")
            return
        proj = Path(self.project_dir).expanduser()
        if not proj.is_dir():
            self.error.emit("init", f"project folder not found: {proj}")
            return
        from .config_io import _list_videos, validate_project
        check = validate_project(proj)
        # Only videos + config are hard requirements. Calibration may be
        # in checkerboard (calculate) mode with empty folders at this point;
        # the pipeline itself guides through it at run time.
        hard = [m for m in check["missing"] if m in ("config", "videos")]
        if hard:
            hint = ""
            if check["suggest_parent"]:
                hint = f" Did you pick the '{proj.name}' subfolder? Select the project root instead."
            self.error.emit("init", f"Invalid project folder ({', '.join(hard)} missing).{hint}")
            return

        repo_root = str(Path(__file__).resolve().parent.parent)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.setWorkingDirectory(repo_root)
        self.proc.readyReadStandardOutput.connect(self._on_output)
        self.proc.finished.connect(self._on_finished)
        self.proc.errorOccurred.connect(self._on_proc_error)
        self._total = len(selected)
        if getattr(sys, "frozen", False):
            prog, args = sys.executable, ["--project", str(proj.resolve()),
                                          "--steps", ",".join(selected)]
        else:
            prog, args = sys.executable, ["-u", "-m", "GUI.runner", "--project", str(proj.resolve()),
                                          "--steps", ",".join(selected)]
        env = self.proc.processEnvironment()
        self.proc.setProcessEnvironment(env)
        self.proc.start(prog, args)

    # ---- parsing ----
    def _on_output(self):
        chunk = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._buf += chunk
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._handle_line(line.rstrip("\r"))

    def _handle_line(self, line: str):
        if line.startswith("STEP-START:"):
            try:
                _, step, i, total = line.split(":")
                self.step_started.emit(step, int(i), int(total))
                self.progress.emit(int(100 * int(i) / int(total)))
            except ValueError:
                self.log_line.emit(line)
            return
        if line.startswith("STEP-DONE:"):
            step = line.split(":", 1)[1]
            self._last = step
            self.step_finished.emit(step)
            self.log_line.emit(f"✓ {step}")
            return
        if line.startswith("STEP-ERROR:"):
            step = line.split(":", 1)[1]
            self._errored = True
            self.error.emit(step, line)
            return
        if line.startswith("ALL-DONE:"):
            self.progress.emit(100)
            self.finished.emit(line.split(":", 1)[1])
            return
        if line.startswith("INIT-ERROR:"):
            self._errored = True
            self.error.emit("init", line[len("INIT-ERROR:"):].strip())
            return
        self.log_line.emit(line)

    def _on_proc_error(self, _err):
        if self._stop:
            return
        if not self._errored and not self.is_running():
            self._errored = True
            self.error.emit("init", "pipeline process failed to start")

    def _on_finished(self, _code, _status):
        if self._buf:
            self._handle_line(self._buf)
            self._buf = ""
        if self._stop:
            self.stopped.emit(self._last)
            self.proc = None
            return
        if self._errored:
            self.proc = None
            return
        # Non-zero exit without markers (traceback already streamed as log)
        if _code != 0:
            self.error.emit(self._last, f"pipeline exited with code {_code}")
        self.proc = None
