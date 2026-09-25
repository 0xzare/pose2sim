# -*- coding: utf-8 -*-
"""Main window: pick a project folder, tick steps, run, watch the log."""
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from .translations import STRINGS, STEP_ORDER
from .worker import PipelineWorker


def tr(lang, key, **kw):
    s = STRINGS[lang].get(key, key)
    return s.format(**kw) if kw else s


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "en"
        self.project_dir = ""
        self.worker = None
        self.step_boxes = {}
        self._build_ui()
        self.retranslate()
        self._refresh_status()

    # ---- UI ----
    def _build_ui(self):
        self.setWindowTitle("Pose2Sim GUI")
        self.resize(1080, 720)
        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setSpacing(10)
        lay.setContentsMargins(14, 14, 14, 14)

        # header
        head = QHBoxLayout()
        self.title_lbl = QLabel(objectName="TitleLabel")
        self.sub_lbl = QLabel(objectName="SubLabel")
        tbox = QVBoxLayout()
        tbox.addWidget(self.title_lbl)
        tbox.addWidget(self.sub_lbl)
        head.addLayout(tbox, 1)
        self.lang_lbl = QLabel()
        self.lang_box = QComboBox()
        self.lang_box.addItems(["English", "فارسی"])
        self.lang_box.currentIndexChanged.connect(self._on_lang)
        hlang = QHBoxLayout()
        hlang.addWidget(self.lang_lbl)
        hlang.addWidget(self.lang_box)
        head.addLayout(hlang)
        lay.addLayout(head)

        # project group
        self.proj_group = QGroupBox()
        pg = QGridLayout(self.proj_group)
        self.dir_lbl = QLabel()
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("…/Demo_SinglePerson")
        self.dir_edit.textChanged.connect(self._on_dir_changed)
        self.browse_btn = QPushButton()
        self.browse_btn.clicked.connect(self._pick_dir)
        self.open_btn = QPushButton()
        self.open_btn.clicked.connect(self._open_output)
        self.cfg_btn = QPushButton()
        self.cfg_btn.clicked.connect(self._open_config)
        pg.addWidget(self.dir_lbl, 0, 0)
        pg.addWidget(self.dir_edit, 0, 1)
        pg.addWidget(self.browse_btn, 0, 2)
        pg.addWidget(self.open_btn, 1, 1)
        pg.addWidget(self.cfg_btn, 1, 2)
        self.status_lbl = QLabel()
        self.status_lbl.setWordWrap(True)
        pg.addWidget(self.status_lbl, 2, 0, 1, 3)
        lay.addWidget(self.proj_group)

        # middle: steps + log
        mid = QHBoxLayout()

        self.pipe_group = QGroupBox()
        pv = QVBoxLayout(self.pipe_group)
        for step in STEP_ORDER:
            cb = QCheckBox()
            cb.setChecked(True)
            desc = QLabel(wordWrap=True, objectName="StepDesc")
            wrap = QVBoxLayout()
            wrap.setContentsMargins(0, 2, 0, 6)
            wrap.addWidget(cb)
            wrap.addWidget(desc)
            pv.addLayout(wrap)
            self.step_boxes[step] = (cb, desc)
        mid.addWidget(self.pipe_group, 1)

        self.log_group = QGroupBox()
        lv = QVBoxLayout(self.log_group)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("logs…")
        lv.addWidget(self.log, 1)
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.step_lbl = QLabel("—")
        lv.addWidget(self.step_lbl)
        lv.addWidget(self.prog)
        brow = QHBoxLayout()
        self.run_btn = QPushButton(objectName="PrimaryBtn")
        self.run_btn.clicked.connect(self._run)
        self.runall_btn = QPushButton()
        self.runall_btn.clicked.connect(self._run_all)
        self.stop_btn = QPushButton(objectName="DangerBtn")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(lambda: self.log.clear())
        self.save_btn = QPushButton()
        self.save_btn.clicked.connect(self._save_log)
        for b in (self.run_btn, self.runall_btn, self.stop_btn, self.clear_btn, self.save_btn):
            brow.addWidget(b)
        lv.addLayout(brow)
        mid.addWidget(self.log_group, 2)
        lay.addLayout(mid, 1)

    # ---- i18n ----
    def _on_lang(self, idx):
        self.lang = "fa" if idx == 1 else "en"
        self.retranslate()

    def retranslate(self):
        T = lambda k, **kw: tr(self.lang, k, **kw)
        self.setLayoutDirection(Qt.RightToLeft if self.lang == "fa" else Qt.LeftToRight)
        self.title_lbl.setText(T("app_title"))
        self.sub_lbl.setText(T("subtitle"))
        self.lang_lbl.setText(T("language"))
        self.proj_group.setTitle(T("project_group"))
        self.dir_lbl.setText(T("project_dir"))
        self.browse_btn.setText(T("browse"))
        self.open_btn.setText(T("open_folder"))
        self.cfg_btn.setText(T("open_config"))
        self.pipe_group.setTitle(T("pipeline_group"))
        self.log_group.setTitle(T("log_group"))
        self.run_btn.setText(T("run"))
        self.runall_btn.setText(T("run_all"))
        self.stop_btn.setText(T("stop"))
        self.clear_btn.setText(T("clear_log"))
        self.save_btn.setText(T("save_log"))
        for step, (cb, desc) in self.step_boxes.items():
            cb.setText(T(f"step_{step}"))
            desc.setText(T(f"desc_{step}"))
        if not self.log.toPlainText():
            self.log.setPlaceholderText(T("log_group"))
        self._refresh_status(empty_msg=T("ready"))

    # ---- project ----
    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr(self.lang, "project_dir"))
        if d:
            self.dir_edit.setText(d)

    def _on_dir_changed(self, txt):
        self.project_dir = txt.strip()
        self._refresh_status()

    def _refresh_status(self, empty_msg=""):
        T = lambda k, **kw: tr(self.lang, k, **kw)
        p = Path(self.project_dir) if self.project_dir else None
        if not p or not str(p).strip():
            self.status_lbl.setText(empty_msg or T("ready"))
            return
        if not p.exists():
            self.status_lbl.setText("✕ " + str(p))
            return
        cfg = p / "Config.toml"
        parts = []
        parts.append("✓ " + T("config_found") if cfg.is_file() else "✕ " + T("config_missing"))
        vids = list((p / "videos").glob("*.*")) if (p / "videos").is_dir() else []
        if not vids:
            n = sum(1 for t in p.glob("Trial_*/videos/*.*"))
            if n:
                vids = [None] * n
        parts.append("• " + T("videos_label", n=len(vids)))
        from .config_io import calibration_status
        cals = calibration_status(p)["ok"] or calibration_status(p.parent)["ok"]
        parts.append("• " + (T("calib_label") if cals else T("calib_missing")))
        self.status_lbl.setText("  ".join(parts))

    def _open_output(self):
        p = Path(self.project_dir) if self.project_dir else Path.cwd()
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            QMessageBox.warning(self, "Pose2Sim", str(e))

    def _open_config(self):
        p = Path(self.project_dir) / "Config.toml" if self.project_dir else Path("Config.toml")
        if not p.is_file():
            QMessageBox.information(self, "Pose2Sim", tr(self.lang, "config_missing"))
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["notepad", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            QMessageBox.warning(self, "Pose2Sim", str(e))

    def _save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, tr(self.lang, "save_log"), "pose2sim_log.txt")
        if path:
            Path(path).write_text(self.log.toPlainText(), encoding="utf-8")

    # ---- run ----
    def _selected(self):
        return {s: cb.isChecked() for s, (cb, _) in self.step_boxes.items()}

    def _run(self):
        self._start(self._selected())

    def _run_all(self):
        for _, (cb, _) in self.step_boxes.items():
            cb.setChecked(True)
        self._start(self._selected())

    def _start(self, steps):
        T = lambda k, **kw: tr(self.lang, k, **kw)
        if not self.project_dir:
            QMessageBox.information(self, "Pose2Sim", T("need_project"))
            return
        if not any(steps.values()):
            QMessageBox.information(self, "Pose2Sim", T("need_step"))
            return
        if self.worker is not None and self.worker.is_running():
            return
        ok, msg = PipelineWorker.check_deps()
        if not ok:
            QMessageBox.warning(self, "Pose2Sim", T("missing_deps") + f"\n{msg}")
            return
        self.run_btn.setEnabled(False)
        self.runall_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.prog.setValue(0)
        self.worker = PipelineWorker()
        self.worker.configure(self.project_dir, steps)
        self.worker.log_line.connect(self._append)
        self.worker.step_started.connect(self._on_step)
        self.worker.step_finished.connect(lambda s: self._append(f"✓ {s}"))
        self.worker.progress.connect(self.prog.setValue)
        self.worker.finished.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.stopped.connect(self._on_stop)
        self.worker.start()

    def _append(self, txt):
        self.log.appendPlainText(txt)

    def _on_step(self, step, i, total):
        self.step_lbl.setText(tr(self.lang, "running_step", step=f"{step} ({i+1}/{total})"))
        self._append(f"\n—— {step} [{i+1}/{total}] ——")

    def _on_done(self, el):
        self._append(tr(self.lang, "done", t=el))
        self.step_lbl.setText(tr(self.lang, "done", t=el))
        self._teardown()

    def _on_error(self, step, msg):
        self._append(tr(self.lang, "failed", step=step, err=msg))
        self.step_lbl.setText(tr(self.lang, "failed", step=step, err=msg.splitlines()[0] if msg else ""))
        QMessageBox.warning(self, "Pose2Sim", msg[:2000])
        self._teardown()

    def _on_stop(self, last):
        self._append(tr(self.lang, "stopped", step=last))
        self._teardown()

    def _stop(self):
        if self.worker:
            self.worker.request_stop()

    def _teardown(self):
        self.run_btn.setEnabled(True)
        self.runall_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, ev):
        if self.worker is not None and self.worker.is_running():
            self.worker.request_stop()
        super().closeEvent(ev)


def run_app():
    app = QApplication.instance() or QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()
