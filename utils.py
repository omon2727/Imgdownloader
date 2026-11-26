# utils.py
import sys
import os
from qtpy.QtWidgets import QHBoxLayout, QLabel, QApplication
from qtpy.QtCore import QEvent, QObject, Qt
from qtpy.QtGui import QKeyEvent, QPixmap, QFont


def get_resource_path(relative_path):
    """Работает и при запуске из .exe, и из Python"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return relative_path


class _RussianShortcutFilter(QObject):
    """Позволяет стандартным Qt-сочетаниям работать в русской раскладке."""

    _layout_map = dict(zip(
        "йцукенгшщзхъфывапролджэячсмитьбю",
        "qwertyuiop[]asdfghjkl;'zxcvbnm,."
    ))

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        modifiers = event.modifiers()
        if not (modifiers & Qt.KeyboardModifier.ControlModifier):
            return super().eventFilter(watched, event)

        # Ctrl+Alt используется Windows для AltGr и не должно изменяться.
        if modifiers & Qt.KeyboardModifier.AltModifier:
            return super().eventFilter(watched, event)

        # При Ctrl Windows/Qt часто отдаёт в text() управляющий символ
        # (например, ``\x03`` для Ctrl+C), поэтому text() нельзя использовать
        # как единственный источник раскладки.  nativeVirtualKey содержит
        # физическую клавишу Windows и остаётся доступным в этом случае.
        russian_key = event.text().lower()
        latin_key = self._layout_map.get(russian_key)
        if not latin_key:
            native_key = event.nativeVirtualKey()
            if 0x41 <= native_key <= 0x5A:
                candidate = chr(native_key).lower()
                # Для английской раскладки Qt уже обрабатывает событие сам.
                # Переводим только клавишу, которую Qt не распознал как
                # обычную латинскую (русская раскладка).
                latin_enum = getattr(Qt.Key, f"Key_{candidate.upper()}", None)
                if latin_enum is not None and event.key() != latin_enum:
                    latin_key = candidate
        if not latin_key or not latin_key.isalpha():
            return super().eventFilter(watched, event)

        key_enum = getattr(Qt.Key, f"Key_{latin_key.upper()}", None)
        if key_enum is None:
            return super().eventFilter(watched, event)

        translated_event = QKeyEvent(
            QEvent.Type.KeyPress,
            key_enum,
            modifiers,
            latin_key,
            event.isAutoRepeat(),
            event.count(),
        )
        QApplication.sendEvent(watched, translated_event)
        return True


def apply_app_style(app: QApplication) -> None:
    """Apply a compact, classic desktop visual style to the application."""
    # Сохраняем фильтр на объекте приложения, чтобы он не был уничтожен
    # сборщиком мусора после установки.
    app._russian_shortcut_filter = _RussianShortcutFilter(app)
    app.installEventFilter(app._russian_shortcut_filter)
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget {
            color: #202020;
            font-family: "Segoe UI";
            font-size: 9pt;
        }
        QWidget#appRoot {
            background: #eeeeee;
        }
        QTabWidget::pane {
            background: #f7f7f7;
            border: 1px solid #bdbdbd;
            top: -1px;
        }
        QTabBar::tab {
            background: #dedede;
            color: #303030;
            padding: 7px 12px;
            margin-right: 1px;
            border: 1px solid #bdbdbd;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background: #f7f7f7;
            color: #000000;
            border-color: #9e9e9e;
            border-bottom-color: #f7f7f7;
        }
        QPushButton {
            background: #e5e5e5;
            color: #202020;
            border: 1px solid #9e9e9e;
            border-radius: 2px;
            padding: 5px 12px;
            min-height: 17px;
        }
        QPushButton:hover { background: #f2f2f2; }
        QPushButton:pressed { background: #cfcfcf; }
        QPushButton:disabled { background: #d4d4d4; color: #888888; }
        QLineEdit, QSpinBox, QComboBox {
            background: white;
            border: 1px solid #9e9e9e;
            border-radius: 2px;
            padding: 4px 6px;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #4f81bd;
        }
        QTableView, QTextEdit {
            background: white;
            border: 1px solid #9e9e9e;
            border-radius: 1px;
            selection-background-color: #c5d9f1;
            selection-color: #000000;
        }
        QHeaderView::section {
            background: #dedede;
            color: #202020;
            padding: 5px;
            border: 1px solid #b5b5b5;
            font-weight: 600;
        }
        QProgressBar {
            background: #ffffff;
            border: 1px solid #9e9e9e;
            border-radius: 1px;
            text-align: center;
            min-height: 10px;
        }
        QProgressBar::chunk {
            background: #7f9db9;
            border-radius: 0px;
        }
        QLabel#pageTitle {
            color: #202020;
            font-size: 12pt;
            font-weight: 500;
        }
        QLabel#pageSubtitle { color: #606060; }
        QRadioButton::indicator, QCheckBox::indicator {
            width: 13px;
            height: 13px;
        }
        """
    )


def create_header(title_text, actions=None):
    actions = actions or []
    header_layout = QHBoxLayout()
    logo = QLabel()
    logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

    pixmap = QPixmap(get_resource_path("logo.png"))
    if pixmap.isNull():
        logo.setText("🖼️")
        logo.setFont(QFont("Segoe UI", 28))
    else:
        scaled = pixmap.scaled(65, 65, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        logo.setPixmap(scaled)

    title = QLabel(title_text)
    title.setObjectName("pageTitle")
    title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    title.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    header_layout.addStretch()
    header_layout.addWidget(logo)
    header_layout.addSpacing(15)
    header_layout.addWidget(title)
    if actions:
        header_layout.addSpacing(18)
        for action in actions:
            header_layout.addWidget(action)
    header_layout.addStretch()
    return header_layout