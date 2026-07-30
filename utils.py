# utils.py
import sys
import os
from qtpy.QtWidgets import QHBoxLayout, QLabel
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap, QFont


def get_resource_path(relative_path):
    """Работает и при запуске из .exe, и из Python"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return relative_path


def create_header(title_text):
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
    title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    title.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    header_layout.addStretch()
    header_layout.addWidget(logo)
    header_layout.addSpacing(15)
    header_layout.addWidget(title)
    header_layout.addStretch()
    return header_layout