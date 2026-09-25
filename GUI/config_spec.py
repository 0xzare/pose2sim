# -*- coding: utf-8 -*-
"""Declarative spec for the Config.toml fields exposed in the GUI form.

Only the most-used parameters are exposed; everything else stays reachable
through the Raw TOML tab. Paths are dotted (e.g. "calibration.convert.convert_from").
"""
from __future__ import annotations

FIELD = dict  # alias for readability

SECTIONS = [
    {
        "id": "project",
        "title_en": "Project",
        "title_fa": "پروژه",
        "fields": [
            {"key": "project.multi_person", "kind": "bool", "default": False, "simple": True,
             "label_en": "Multi person", "label_fa": "چندنفره"},
            {"key": "project.participant_height", "kind": "text", "default": "auto",
             "label_en": "Height (m) or 'auto'", "label_fa": "قد (متر) یا auto"},
            {"key": "project.participant_mass", "kind": "float", "default": 70.0,
             "label_en": "Mass (kg)", "label_fa": "وزن (کیلوگرم)"},
            {"key": "project.frame_rate", "kind": "text", "default": "auto",
             "label_en": "Frame rate or 'auto'", "label_fa": "نرخ فریم یا auto"},
            {"key": "project.frame_range", "kind": "text", "default": "auto",
             "label_en": "Frame range ('auto' or [a,b])", "label_fa": "بازه فریم (auto یا [a,b])"},
        ],
    },
    {
        "id": "pose",
        "title_en": "Pose estimation",
        "title_fa": "تخمین پوز",
        "fields": [
            {"key": "pose.pose_model", "kind": "choice", "default": "Body_with_feet", "simple": True,
             "choices": ["Body_with_feet", "Whole_body", "Whole_body_wrist", "Lower_body", "Body"],
             "label_en": "Pose model", "label_fa": "مدل پوز"},
            {"key": "pose.mode", "kind": "choice", "default": "balanced", "simple": True,
             "choices": ["lightweight", "balanced", "performance"],
             "label_en": "Speed ↔ accuracy", "label_fa": "سرعت ↔ دقت"},
            {"key": "pose.det_frequency", "kind": "int", "default": 4,
             "label_en": "Detection every N frames", "label_fa": "آشکارسازی هر N فریم"},
            {"key": "pose.device", "kind": "choice", "default": "auto",
             "choices": ["auto", "CPU", "CUDA", "MPS"],
             "label_en": "Device", "label_fa": "دستگاه"},
            {"key": "pose.display_detection", "kind": "bool", "default": True,
             "label_en": "Show detection preview", "label_fa": "نمایش پیش‌نمایش"},
            {"key": "pose.overwrite_pose", "kind": "bool", "default": False,
             "label_en": "Overwrite previous pose", "label_fa": "بازنویسی پوز قبلی"},
        ],
    },
    {
        "id": "calibration",
        "title_en": "Calibration",
        "title_fa": "کالیبراسیون",
        "fields": [
            {"key": "calibration.calibration_type", "kind": "choice", "default": "convert", "simple": True,
             "choices": ["convert", "calculate"],
             "label_en": "Type", "label_fa": "نوع"},
            {"key": "calibration.convert.convert_from", "kind": "choice", "default": "qualisys", "simple": True,
             "choices": ["qualisys", "caliscope", "anipose", "freemocap", "vicon", "opencap", "easymocap", "biocv", "optitrack"],
             "label_en": "Convert from", "label_fa": "تبدیل از"},
            {"key": "calibration.convert.qualisys.binning_factor", "kind": "int", "default": 1,
             "label_en": "Binning factor (qualisys)", "label_fa": "بینینگ (کوالیسیس)"},
        ],
    },
    {
        "id": "sync_tri",
        "title_en": "Sync / Triangulation",
        "title_fa": "همگامی / مثلث‌سازی",
        "fields": [
            {"key": "synchronization.synchronization_gui", "kind": "bool", "default": True,
             "label_en": "Synchronization GUI", "label_fa": "رابط همگام‌سازی"},
            {"key": "triangulation.reproj_error_threshold_triangulation", "kind": "int", "default": 15,
             "label_en": "Reproj. error threshold (px)", "label_fa": "آستانه خطا (پیکسل)"},
            {"key": "triangulation.likelihood_threshold_triangulation", "kind": "float", "default": 0.3,
             "label_en": "Likelihood threshold", "label_fa": "آستانه اطمینان"},
            {"key": "triangulation.min_cameras_for_triangulation", "kind": "int", "default": 2,
             "label_en": "Min cameras", "label_fa": "حداقل دوربین"},
        ],
    },
    {
        "id": "filter_kin",
        "title_en": "Filtering / Kinematics",
        "title_fa": "فیلتر / کینماتیک",
        "fields": [
            {"key": "filtering.type", "kind": "choice", "default": "butterworth",
             "choices": ["butterworth", "kalman", "one_euro", "gcv_spline", "gaussian", "median"],
             "label_en": "Filter type", "label_fa": "نوع فیلتر"},
            {"key": "filtering.butterworth.cut_off_frequency", "kind": "int", "default": 6,
             "label_en": "Cutoff frequency (Hz)", "label_fa": "فرکانس قطع (هرتز)"},
            {"key": "markerAugmentation.feet_on_floor", "kind": "bool", "default": False,
             "label_en": "Feet on floor", "label_fa": "پاها روی زمین"},
            {"key": "kinematics.use_augmentation", "kind": "bool", "default": True,
             "label_en": "Use augmentation", "label_fa": "استفاده از افزایش"},
            {"key": "kinematics.use_simple_model", "kind": "bool", "default": False, "simple": True,
             "label_en": "Fast model (10x faster)", "label_fa": "مدل سریع (۱۰ برابر سریع‌تر)"},
            {"key": "kinematics.filter_ik", "kind": "bool", "default": False,
             "label_en": "Filter IK", "label_fa": "فیلتر IK"},
        ],
    },
]
