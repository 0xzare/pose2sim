# -*- coding: utf-8 -*-
"""Dark modern theme for Pose2Sim GUI."""

APP_QSS = """
* { font-size: 13px; }
QMainWindow, QWidget { background: #14181d; color: #e8edf2; }
QGroupBox {
    border: 1px solid #2a323b; border-radius: 12px;
    margin-top: 14px; padding: 12px; background: #191f26;
    font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #7dd3c0; }
QLineEdit, QPlainTextEdit, QTextEdit {
    background: #0f1318; border: 1px solid #2a323b; border-radius: 8px;
    padding: 8px; selection-background-color: #2b6f62;
}
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #7dd3c0; }
QPushButton {
    background: #222b34; border: 1px solid #33404d; border-radius: 10px;
    padding: 9px 14px; font-weight: 600;
}
QPushButton:hover { background: #2a3541; border-color: #7dd3c0; }
QPushButton:disabled { color: #6b7684; background: #1b2128; }
QPushButton#PrimaryBtn { background: #1f7a6b; border: 1px solid #2aa88f; color: white; }
QPushButton#PrimaryBtn:hover { background: #24917f; }
QPushButton#DangerBtn { background: #5a2626; border-color: #8a3a3a; }
QCheckBox { spacing: 8px; padding: 4px 2px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 6px; border: 1px solid #3a4654; background: #0f1318; }
QCheckBox::indicator:checked { background: #2aa88f; border-color: #2aa88f; }
QProgressBar { background: #0f1318; border: 1px solid #2a323b; border-radius: 8px; text-align: center; height: 18px; }
QProgressBar::chunk { background: #2aa88f; border-radius: 7px; }
QLabel#TitleLabel { font-size: 19px; font-weight: 800; }
QLabel#SubLabel { color: #9aa7b4; font-size: 12px; }
QLabel#StepDesc { color: #9aa7b4; font-size: 11.5px; }
QLabel#StatusOk { color: #7dd3c0; }
QLabel#StatusBad { color: #e08a8a; }
QComboBox { background: #0f1318; border: 1px solid #2a323b; border-radius: 8px; padding: 6px 10px; }
"""
