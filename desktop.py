"""Small, vendored Qt UI helpers. No dependency on another OKDEV repository."""
import os
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Signal, QThread, QLockFile, QLocale
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
                             QTableWidget, QHeaderView, QAbstractItemView)


STYLE = """
QWidget { background: #0d1423; color: #ecf0f8; font: 14px 'Segoe UI'; }
QFrame#sidebar { background: #101b2d; border-right: 1px solid #26334b; }
QFrame#card { background: #162136; border: 1px solid #2a3953; border-radius: 16px; }
QFrame#card QLabel, QFrame#sidebar QLabel { background: transparent; }
QLabel#brand { font-size: 30px; font-weight: 700; letter-spacing: -1px; }
QLabel#title { font-size: 32px; font-weight: 700; }
QLabel#muted { color: #a6b5cf; }
QLabel#eyebrow { color: #acbef1; font-size: 11px; font-weight: 600; letter-spacing: 2px; }
QLabel#metric { font-size: 29px; font-weight: 700; }
QPushButton { background: #22314a; border: 1px solid #354562; border-radius: 9px; padding: 11px 18px; font-weight: 600; }
QPushButton:hover { background: #304562; }
QPushButton:pressed { background: #3c5274; }
QPushButton:disabled { background: #1a2435; color: #718099; border-color: #263248; }
QPushButton#primary { background: #baff72; color: #132014; border: none; }
QPushButton#primary:hover { background: #d0ffa0; }
QPushButton#primary:disabled { background: #364938; color: #9aa99c; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit { background: #111c2e; border: 1px solid #354562; border-radius: 8px; padding: 9px; min-height: 22px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #baff72; }
QTableWidget, QListWidget { background: #111c2e; alternate-background-color: #162238; border: 1px solid #2a3953; border-radius: 10px; gridline-color: #27364e; }
QTableWidget::item, QListWidget::item { padding: 9px; }
QTableWidget::item:selected, QListWidget::item:selected { background: #314662; }
QHeaderView::section { background: #1c2a42; color: #b9c7dd; border: none; padding: 12px; font-weight: 600; }
QProgressBar { background: #233148; border: none; border-radius: 5px; height: 8px; text-align: center; }
QProgressBar::chunk { background: #baff72; border-radius: 5px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QTableView::indicator, QListView::indicator { width: 15px; height: 15px; border: 1px solid #7086a6; border-radius: 3px; background: #1a2b42; }
QTableView::indicator:checked, QListView::indicator:checked { background: #baff72; border-color: #baff72; }
QToolTip { background: #233148; color: #ffffff; border: 1px solid #526989; padding: 5px; }
QScrollBar:vertical { background: #152035; width: 10px; }
QScrollBar::handle:vertical { background: #405270; min-height: 28px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def label(text, role="", wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if role:
        widget.setObjectName(role)
    return widget


def button(text, callback=None, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if callback:
        widget.clicked.connect(callback)
    return widget


def card():
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)
    return frame, layout


def metric(title, value):
    frame, layout = card()
    layout.addWidget(label(title, "eyebrow"))
    number = label(value, "metric")
    layout.addWidget(number)
    return frame, number


def app_icon(letter, color="#baff72"):
    pix = QPixmap(256, 256)
    pix.fill(QColor("#101b2d"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(color))
    painter.setFont(QFont("Segoe UI", 120, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return QIcon(pix)


def data_folder(name):
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    path = base / "OkdevDesktop" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure(app):
    QLocale.setDefault(QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey))
    if app.platformName() == "offscreen" and os.name == "nt":
        for name in ("segoeui.ttf", "segoeuib.ttf"):
            font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name
            if font_path.exists():
                QFontDatabase.addApplicationFont(str(font_path))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))


def table(columns):
    widget = QTableWidget(0, len(columns))
    widget.setHorizontalHeaderLabels(columns)
    widget.verticalHeader().hide()
    widget.verticalHeader().setDefaultSectionSize(44)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return widget


def run(window_type, name):
    import argparse
    import json
    import sys
    import tempfile
    parser = argparse.ArgumentParser(description=name + " — OKDEV masaüstü uygulaması")
    parser.add_argument("--smoke-test", type=Path)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    testing = bool(args.smoke_test or args.preview)
    if testing:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication(sys.argv[:1])
    configure(app)
    temporary = tempfile.TemporaryDirectory(prefix=name + "-test-") if testing else None
    folder = Path(temporary.name) if temporary else data_folder(name)
    lock = single_instance(folder)
    if lock is None:
        return 1
    try:
        window = window_type(folder)
        if testing:
            window.seed_demo()
        window.show()
        if testing:
            for _ in range(5):
                app.processEvents()
            if args.preview:
                args.preview.parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(str(args.preview))
            checks = window.smoke()
            app.processEvents()
            if args.smoke_test:
                args.smoke_test.parent.mkdir(parents=True, exist_ok=True)
                args.smoke_test.write_text(json.dumps({"app": name, "ok": True, "checks": checks}, indent=2), encoding="utf-8")
            window.close()
            app.processEvents()
            return 0
        return app.exec()
    except Exception as exc:
        if args.smoke_test:
            args.smoke_test.write_text(json.dumps({"app": name, "ok": False, "error": repr(exc)}), encoding="utf-8")
        else:
            QMessageBox.critical(None, name, "Uygulama başlatılamadı: " + str(exc))
        return 1
    finally:
        lock.unlock()
        if temporary:
            temporary.cleanup()


def single_instance(folder):
    lock = QLockFile(str(folder / "application.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(None, "Uygulama zaten açık", "Aynı uygulama ikinci kez açılamaz. Açık pencereyi kullanın.")
        return None
    return lock


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, action):
        super().__init__()
        self.action = action

    def run(self):
        try:
            self.finished.emit(self.action())
        except Exception as exc:
            self.failed.emit(str(exc))


class Shell(QMainWindow):
    def __init__(self, name, tagline, title, description, section):
        super().__init__()
        self.setWindowTitle(f"{name} · OKDEV")
        self.setWindowIcon(app_icon(name[0]))
        self.resize(1140, 760)
        self.setMinimumSize(960, 650)
        self.busy = False
        outer = QWidget()
        self.setCentralWidget(outer)
        row = QHBoxLayout(outer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(200)
        nav = QVBoxLayout(side)
        nav.setContentsMargins(24, 34, 22, 24)
        nav.setSpacing(18)
        nav.addWidget(label("okdev / DESKTOP", "eyebrow"))
        nav.addWidget(label(name, "brand"))
        nav.addWidget(label(tagline, "muted", True))
        nav.addSpacing(30)
        active = label("●  " + section)
        active.setStyleSheet("color: #baff72; font-weight: 600;")
        nav.addWidget(active)
        nav.addStretch()
        nav.addWidget(label("ÇEVRİMDIŞI\nHesap gerekmez", "muted", True))
        nav.addWidget(label("v0.1.0  ·  okdev.tr", "muted"))
        row.addWidget(side)
        main = QWidget()
        self.body = QVBoxLayout(main)
        self.body.setContentsMargins(30, 28, 30, 20)
        self.body.setSpacing(18)
        self.body.addWidget(label(title, "title"))
        self.body.addWidget(label(description, "muted", True))
        row.addWidget(main, 1)
        self.status = label("Hazır", "muted", True)

    def finish_layout(self):
        self.body.addWidget(self.status)

    def work(self, action, callback):
        if self.busy:
            return
        self.busy = True
        self.centralWidget().setEnabled(False)
        self.status.setText("İşlem sürüyor…")
        self.thread = QThread(self)
        self.worker = Worker(action)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(callback)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._ready)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.start()

    def _ready(self):
        self.busy = False
        self.centralWidget().setEnabled(True)
        self.thread.deleteLater()

    def show_error(self, message):
        self.status.setText("İşlem tamamlanamadı: " + message)
        QMessageBox.warning(self, "İşlem tamamlanamadı", message)

    def closeEvent(self, event):
        if self.busy:
            QMessageBox.information(self, "İşlem sürüyor", "Dosyaların güvenliği için işlem bitene kadar bekleyin.")
            event.ignore()
        else:
            event.accept()
