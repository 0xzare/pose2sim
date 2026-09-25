# -*- coding: utf-8 -*-
"""Config editor dialog (form + raw TOML) and new-project wizard dialog."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPlainTextEdit, QPushButton, QTabWidget,
    QVBoxLayout, QWidget, QWizard, QWizardPage,
)

from .config_io import format_value, load_config, parse_text_value, save_config, scaffold_project, template_path
from .config_spec import SECTIONS

# Short human-friendly help per setting (shown under each field in the wizard).
HELPS = {
    "project.multi_person": ("Track several people at once. Off = only the clearest person is kept.",
                             "چند نفر رو هم‌زمان دنبال کن. خاموش باشه فقط واضح‌ترین نفر نگه داشته می‌شه."),
    "project.participant_height": ("Used for marker scaling. 'auto' estimates it from the data.",
                                   "برای اسکیل مارکرها لازمه. auto خودش از روی داده حدس می‌زنه."),
    "project.participant_mass": ("Body mass in kg. Only matters for force and load estimates.",
                                 "وزن به کیلوگرم. فقط برای محاسبه‌ی نیرو مهمه."),
    "project.frame_rate": ("'auto' reads the frame rate from the videos.",
                           "auto نرخ فریم رو از روی ویدیوها می‌خونه."),
    "project.frame_range": ("'auto' keeps the good part. Or give [start,end] frames.",
                            "auto تیکه‌ی خوب رو نگه می‌داره. یا [شروع،پایان] بده."),
    "pose.pose_model": ("Which body parts to track. Whole body adds hands and face but is slower.",
                        "کدوم اعضای بدن دنبال بشن. کل بدن دست و صورت رو هم می‌گیره ولی کندتره."),
    "pose.mode": ("Lightweight is fast, performance is accurate, balanced is in between.",
                  "سبک سریعه، دقیق کندتره، متعادل وسطه."),
    "pose.det_frequency": ("Run detection every N frames; tracking fills the gaps. Higher = faster.",
                           "هر N فریم یه بار آشکارسازی می‌کنه، وسطش رو ترکینگ پر می‌کنه. بیشتر یعنی سریع‌تر."),
    "pose.device": ("Which chip runs the AI. 'auto' picks the best available one.",
                    "هوش مصنوعی روی کدوم چیپ اجرا بشه. auto بهترین موجود رو برمی‌داره."),
    "pose.display_detection": ("Show a live preview window while estimating.",
                               "موقع تخمین، پنجره‌ی پیش‌نمایش زنده نشون بده."),
    "pose.overwrite_pose": ("Recompute even if results from before already exist.",
                            "حتی اگه نتیجه‌ی قبلی هست، از اول حساب کن."),
    "calibration.calibration_type": ("'convert' = you already have a calibration file. 'calculate' = make one with a checkerboard.",
                                     "convert یعنی فایل کالیبراسیون داری. calculate یعنی با شطرنجی بساز."),
    "calibration.convert.convert_from": ("Which software made your calibration file?",
                                         "فایل کالیبراسیونت رو کدوم نرم‌افزار ساخته؟"),
    "calibration.convert.qualisys.binning_factor": ("Use 2 if you filmed in 540p, otherwise 1.",
                                                    "اگه با 540p گرفتی ۲ بذار، وگرنه ۱."),
    "synchronization.synchronization_gui": ("Open a window to pick the sync moment by hand. Off = fully automatic.",
                                            "یه پنجره باز می‌کنه که لحظه‌ی همگامی رو دستی بگی. خاموش = کاملا خودکار."),
    "triangulation.reproj_error_threshold_triangulation": ("Strictness of 3D cleaning, in pixels. Higher keeps more but noisier.",
                                                           "سخت‌گیری تمیزکاری سه‌بعدی به پیکسل. بیشتر یعنی نگه‌داشتن بیشتر ولی نویزی‌تر."),
    "triangulation.likelihood_threshold_triangulation": ("Ignore 2D points the AI is unsure about (below this score).",
                                                         "نقاطی که هوش مصنوعی مطمئن نیست (زیر این نمره) نادیده گرفته می‌شن."),
    "triangulation.min_cameras_for_triangulation": ("Minimum cameras that must agree on each point.",
                                                   "کمترین دوربینی که باید روی هر نقطه توافق کنن."),
    "filtering.type": ("Smoothing method. Butterworth is the standard choice.",
                       "روش هموارسازی. باترورث استاندارده."),
    "filtering.butterworth.cut_off_frequency": ("Lower = smoother. Walking 3–6 Hz, running 6–15 Hz.",
                                                "کمتر یعنی هموارتر. راه رفتن ۳ تا ۶ هرتز، دویدن ۶ تا ۱۵."),
    "markerAugmentation.feet_on_floor": ("Snap the feet to the ground plane. Useful for force estimates.",
                                         "پاها رو می‌چسبونه به زمین. برای محاسبه‌ی نیرو خوبه."),
    "kinematics.use_augmentation": ("Fill in the full marker set with AI. Most OpenSim models need it.",
                                    "ست کامل مارکر رو با هوش مصنوعی پر می‌کنه. بیشتر مدل‌های اوپن‌سیم لازمش دارن."),
    "kinematics.use_simple_model": ("Much faster, but with a stiff spine and simple shoulders.",
                                     "خیلی سریع‌تر، ولی ستون فقرات خشک و شونه‌های ساده."),
    "kinematics.filter_ik": ("Also smooth the final joint angles.",
                             "زاویه‌های مفصلی نهایی رو هم هموار کن."),
}


def _rtoml():
    try:
        import rtoml
        return rtoml
    except ImportError:
        return None


def _make_field_widget(f: dict):
    kind = f["kind"]
    if kind == "bool":
        return QCheckBox()
    if kind == "choice":
        cb = QComboBox()
        cb.setEditable(False)
        for c in f.get("choices", []):
            cb.addItem(str(c))
        return cb
    return QLineEdit()


def _fill_field_widget(kind: str, w, val):
    if kind == "bool":
        w.setChecked(bool(val))
    elif kind == "choice":
        s = str(val)
        idx = w.findText(s)
        if idx < 0:
            w.addItem(s)
            idx = w.findText(s)
        w.setCurrentIndex(idx)
    else:
        w.setText(format_value(val))


def _apply_field(cfg: dict, key: str, kind: str, w):
    from .config_io import set_dotted
    if kind == "bool":
        set_dotted(cfg, key, bool(w.isChecked()))
    elif kind == "choice":
        set_dotted(cfg, key, w.currentText())
    elif kind == "int":
        try:
            set_dotted(cfg, key, int(w.text().strip()))
        except ValueError:
            raise ValueError(f'{key}: expected a whole number, got "{w.text()}"')
    elif kind == "float":
        try:
            set_dotted(cfg, key, float(w.text().strip()))
        except ValueError:
            raise ValueError(f'{key}: expected a number, got "{w.text()}"')
    else:
        set_dotted(cfg, key, parse_text_value(w.text()))


def _sec_fields(sid: str, prefix: str | None = None):
    for sec in SECTIONS:
        if sec["id"] != sid:
            continue
        for f in sec["fields"]:
            if prefix is None or f["key"].startswith(prefix):
                yield f


_PAGE_TEXTS = {
    "project": ("Project", "Who is in the videos?", "پروژه", "توی ویدیوها کیه؟"),
    "pose": ("Pose tracking", "What should the AI track, and how carefully?",
             "دنبال کردن پوز", "هوش مصنوعی چی رو با چه دقتی دنبال کنه؟"),
    "caltype": ("Calibration", "Do you already have a calibration file?",
                "کالیبراسیون", "فایل کالیبراسیون داری؟"),
    "convert": ("Calibration file", "Which software made it?",
                "فایل کالیبراسیون", "کدوم نرم‌افزار ساخته‌ش؟"),
    "calc": ("Checkerboard", "Tell me about your checkerboard.",
             "شطرنجی", "درباره‌ی شطرنجی‌ت بگو."),
    "sync": ("Sync & 3D", "How strict should the 3D cleaning be?",
             "همگامی و سه‌بعدی", "تمیزکاری سه‌بعدی چقدر سخت‌گیر باشه؟"),
    "filt": ("Smoothing & model", "Smoothing and the OpenSim model.",
             "هموارسازی و مدل", "هموارسازی و مدل اوپن‌سیم."),
    "review": ("Review", "Check and save.", "بازبینی", "چک کن و ذخیره کن."),
}


class _FieldsPage(QWizardPage):
    """One wizard page = spec fields with labels + one-line help."""

    def __init__(self, wiz, fields):
        super().__init__(wiz)
        self._wiz = wiz
        self._fields = list(fields)
        lay = QVBoxLayout(self)
        for f in self._fields:
            lab = QLabel()
            lab.setProperty("fkey", f["key"])
            lab.setStyleSheet("font-weight: 600;")
            w = _make_field_widget(f)
            help_lbl = QLabel(wordWrap=True, objectName="StepDesc")
            help_lbl.setProperty("fhelp", f["key"])
            lay.addWidget(lab)
            lay.addWidget(w)
            lay.addWidget(help_lbl)
            wiz._widgets[f["key"]] = (f, w)
            wiz._labels[f["key"]] = (lab, help_lbl)
        lay.addStretch(1)


class _CalibTypePage(_FieldsPage):
    def nextId(self):
        _f, w = self._wiz._widgets["calibration.calibration_type"]
        if w.currentText() == "calculate":
            return self._wiz._id_calc
        return self._wiz._id_convert


class _ReviewPage(QWizardPage):
    def __init__(self, wiz):
        super().__init__(wiz)
        self._wiz = wiz
        lay = QVBoxLayout(self)
        self.info = QLabel(wordWrap=True)
        lay.addWidget(self.info)
        lay.addStretch(1)

    def initializePage(self):
        self.info.setText(self._wiz._review_text())


class ConfigEditorDialog(QWizard):
    """Guided step-by-step settings for Config.toml. No file editing needed."""

    def __init__(self, project_dir: str | Path, lang: str = "en", parent=None):
        super().__init__(parent)
        self.project_dir = Path(project_dir)
        self.lang = lang
        self.setModal(True)
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.resize(640, 540)
        self._widgets: dict[str, tuple[dict, object]] = {}
        self._labels: dict[str, tuple[QLabel, QLabel]] = {}

        cfg_path = self.project_dir / "Config.toml"
        self.cfg = load_config(cfg_path) if cfg_path.is_file() else load_config(template_path())
        if not self.cfg:
            self.cfg = load_config(template_path())

        self._id_project = self.addPage(_FieldsPage(self, _sec_fields("project")))
        self._id_pose = self.addPage(_FieldsPage(self, _sec_fields("pose")))
        self._id_caltype = self.addPage(_CalibTypePage(
            self, [f for f in _sec_fields("calibration")
                   if f["key"] == "calibration.calibration_type"]))
        self._id_convert = self.addPage(_FieldsPage(
            self, [f for f in _sec_fields("calibration")
                   if f["key"].startswith("calibration.convert.")]))
        self._id_calc = self.addPage(_FieldsPage(
            self, [f for f in _sec_fields("calibration")
                   if f["key"].startswith("calibration.calculate")]))
        self._id_sync = self.addPage(_FieldsPage(self, _sec_fields("sync_tri")))
        self._id_filt = self.addPage(_FieldsPage(self, _sec_fields("filter_kin")))
        self._id_review = self.addPage(_ReviewPage(self))
        self._page_ids = {
            self._id_project: "project", self._id_pose: "pose",
            self._id_caltype: "caltype", self._id_convert: "convert",
            self._id_calc: "calc", self._id_sync: "sync",
            self._id_filt: "filt", self._id_review: "review",
        }

        from .config_io import get_dotted
        for key, (f, w) in self._widgets.items():
            _fill_field_widget(f["kind"], w, get_dotted(self.cfg, key, f.get("default")))
        self._apply_lang()

    def _apply_lang(self):
        fa = self.lang == "fa"
        self.setLayoutDirection(Qt.RightToLeft if fa else Qt.LeftToRight)
        self.setWindowTitle("تنظیمات" if fa else "Settings")
        for pid, sid in self._page_ids.items():
            t_en, s_en, t_fa, s_fa = _PAGE_TEXTS[sid]
            self.page(pid).setTitle(t_fa if fa else t_en)
            self.page(pid).setSubTitle(s_fa if fa else s_en)
        for key, (lab, help_lbl) in self._labels.items():
            for sec in SECTIONS:
                for f in sec["fields"]:
                    if f["key"] == key:
                        lab.setText(f["label_fa"] if fa else f["label_en"])
            h = HELPS.get(key)
            if h:
                help_lbl.setText(h[1] if fa else h[0])
        self.setButtonText(QWizard.NextButton, "بعدی ‹" if fa else "Next ›")
        self.setButtonText(QWizard.BackButton, "› قبلی" if fa else "‹ Back")
        self.setButtonText(QWizard.CancelButton, "انصراف" if fa else "Cancel")
        self.setButtonText(QWizard.FinishButton, "ذخیره" if fa else "Save")

    def _review_text(self):
        fa = self.lang == "fa"
        vals = {}
        for key, (f, w) in self._widgets.items():
            kind = f["kind"]
            if kind == "bool":
                vals[key] = bool(w.isChecked())
            elif kind == "choice":
                vals[key] = w.currentText()
            else:
                vals[key] = w.text().strip()
        multi = vals.get("project.multi_person", False)
        lines = [
            ("نفرات: " if fa else "People: ")
            + ("چند نفر" if (multi and fa) else "چند نفره" if multi else ("یه نفر" if fa else "One person")),
            ("مدل: " if fa else "Model: ")
            + f"{vals.get('pose.pose_model', '')} • {vals.get('pose.mode', '')}",
        ]
        if vals.get("calibration.calibration_type") == "calculate":
            lines.append(("کالیبراسیون: ساخت با شطرنجی" if fa else "Calibration: make with checkerboard"))
        else:
            lines.append(("کالیبراسیون: تبدیل از " if fa else "Calibration: convert from ")
                         + str(vals.get("calibration.convert.convert_from", "")))
        lines.append(("خروجی: " if fa else "Output: ") + str(self.project_dir))
        return "\n".join("• " + ln for ln in lines)

    def accept(self):
        try:
            cfg = deepcopy(self.cfg)
            for key, (f, w) in self._widgets.items():
                _apply_field(cfg, key, f["kind"], w)
            proj = cfg.get("project")
            if isinstance(proj, dict):
                proj["project_dir"] = "."
            save_config(self.project_dir / "Config.toml", cfg)
        except ValueError as e:
            QMessageBox.warning(self, "Pose2Sim", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Pose2Sim", str(e))
            return
        super().accept()


class NewProjectDialog(QDialog):
    """Pick destination + videos + calibration, scaffold the project folders."""

    def __init__(self, lang: str = "en", parent=None, start_dir: str = ""):
        super().__init__(parent)
        self.lang = lang
        self.setModal(True)
        self.resize(640, 480)
        self.result_path = ""
        lay = QVBoxLayout(self)

        form = QFormLayout()
        self.dest_lbl = QLabel()
        dl = QHBoxLayout()
        self.dest_edit = QLineEdit()
        if start_dir:
            self.dest_edit.setText(start_dir)
        self.dest_btn = QPushButton("…")
        self.dest_btn.clicked.connect(self._pick_dest)
        dl.addWidget(self.dest_edit, 1)
        dl.addWidget(self.dest_btn)
        form.addRow(self.dest_lbl, dl)
        lay.addLayout(form)

        self.vid_lbl = QLabel()
        lay.addWidget(self.vid_lbl)
        self.vid_list = QListWidget()
        lay.addWidget(self.vid_list, 1)
        vb = QHBoxLayout()
        self.add_vid_btn = QPushButton()
        self.add_vid_btn.clicked.connect(self._add_videos)
        self.del_vid_btn = QPushButton()
        self.del_vid_btn.clicked.connect(self._del_video)
        vb.addWidget(self.add_vid_btn)
        vb.addWidget(self.del_vid_btn)
        lay.addLayout(vb)

        self.cal_lbl = QLabel()
        cl = QHBoxLayout()
        self.cal_edit = QLineEdit()
        self.cal_file_btn = QPushButton("📄")
        self.cal_file_btn.clicked.connect(self._pick_cal_file)
        self.cal_dir_btn = QPushButton("📁")
        self.cal_dir_btn.clicked.connect(self._pick_cal_dir)
        cl.addWidget(self.cal_edit, 1)
        cl.addWidget(self.cal_file_btn)
        cl.addWidget(self.cal_dir_btn)
        lay.addWidget(self.cal_lbl)
        lay.addLayout(cl)

        self.info = QLabel(wordWrap=True)
        lay.addWidget(self.info)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._on_create)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.retranslate()

    def _pick_dest(self):
        d = QFileDialog.getExistingDirectory(self, "project")
        if d:
            self.dest_edit.setText(d)

    def _add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "videos", "", "Videos (*.mp4 *.avi *.mov *.mkv *.mpg *.mpeg)")
        for f in files:
            if self.vid_list.findItems(f, Qt.MatchExactly) == []:
                self.vid_list.addItem(f)

    def _del_video(self):
        for it in self.vid_list.selectedItems():
            self.vid_list.takeItem(self.vid_list.row(it))

    def _pick_cal_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "calibration file")
        if f:
            self.cal_edit.setText(f)

    def _pick_cal_dir(self):
        d = QFileDialog.getExistingDirectory(self, "calibration folder")
        if d:
            self.cal_edit.setText(d)

    def _on_create(self):
        dest = self.dest_edit.text().strip()
        if not dest:
            QMessageBox.information(self, "Pose2Sim", self._t("need_dest"))
            return
        videos = [self.vid_list.item(i).text() for i in range(self.vid_list.count())]
        if not videos:
            QMessageBox.information(self, "Pose2Sim", self._t("need_videos"))
            return
        cals = [self.cal_edit.text().strip()] if self.cal_edit.text().strip() else []
        try:
            res = scaffold_project(dest, videos, cals)
        except Exception as e:
            QMessageBox.warning(self, "Pose2Sim", str(e))
            return
        self.result_path = dest
        fa = self.lang == "fa"
        QMessageBox.information(
            self, "Pose2Sim",
            (f"{res['videos_copied']} ویدیو و {res['calib_copied']} فایل کالیبراسیون کپی شد.")
            if fa else
            (f"Copied {res['videos_copied']} video(s), {res['calib_copied']} calibration file(s)."),
        )
        self.accept()

    def _t(self, key: str) -> str:
        fa = self.lang == "fa"
        return {
            "need_dest": ("اول پوشه‌ی مقصد رو انتخاب کن." if fa else "Pick a destination folder first."),
            "need_videos": ("حداقل یه ویدیو اضافه کن." if fa else "Add at least one video."),
        }[key]

    def retranslate(self):
        fa = self.lang == "fa"
        self.setLayoutDirection(Qt.RightToLeft if fa else Qt.LeftToRight)
        self.setWindowTitle("پروژه‌ی جدید" if fa else "New project")
        self.dest_lbl.setText("پوشه‌ی پروژه" if fa else "Project folder")
        self.vid_lbl.setText("ویدیوها" if fa else "Videos")
        self.add_vid_btn.setText("افزودن ویدیو…" if fa else "Add videos…")
        self.del_vid_btn.setText("حذف" if fa else "Remove")
        self.cal_lbl.setText("فایل یا پوشه‌ی کالیبراسیون" if fa else "Calibration file or folder")
        self.info.setText(
            "ساختار videos و calibration ساخته می‌شه و فایل‌ها کپی می‌شن. فایل Config.toml هم از قالب پیش‌فرض ساخته می‌شه."
            if fa else
            "Creates videos/ and calibration/, copies the files, and writes a default Config.toml."
        )
