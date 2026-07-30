from qtpy.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QLabel, QRadioButton, QTextEdit, QProgressBar
)
from workers.converter_worker import ConverterWorker

from utils import create_header


class ConverterTab(QWidget):
    def __init__(self):
        super().__init__()
        self.converter_worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(create_header("Конвертер Excel → TXT / CSV"))
        layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        self.conv_folder_btn = QPushButton("Выбрать папку с Excel файлами")
        self.conv_folder_btn.setFixedWidth(280)
        self.conv_folder_btn.clicked.connect(self.conv_select_folder)
        btn_layout.addStretch()
        btn_layout.addWidget(self.conv_folder_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addSpacing(20)

        format_layout = QHBoxLayout()
        format_label = QLabel("Формат вывода:")
        self.conv_radio_txt = QRadioButton("Текст Юникод (.txt)")
        self.conv_radio_csv = QRadioButton("CSV с разделителем ; (.csv)")
        self.conv_radio_txt.setChecked(True)
        format_layout.addStretch()
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.conv_radio_txt)
        format_layout.addWidget(self.conv_radio_csv)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        layout.addSpacing(30)

        start_layout = QHBoxLayout()
        self.conv_start_btn = QPushButton("Начать конвертацию")
        self.conv_start_btn.setFixedWidth(260)
        self.conv_start_btn.clicked.connect(self.conv_on_start_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.conv_start_btn)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        layout.addSpacing(20)

        self.conv_progress = QProgressBar()
        layout.addWidget(self.conv_progress)
        layout.addSpacing(10)

        self.conv_log = QTextEdit()
        self.conv_log.setReadOnly(True)
        layout.addWidget(self.conv_log)

    def conv_select_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку с Excel файлами")
        if directory:
            self.conv_folder = directory
            self.conv_log.append(f"Выбрана папка: {directory}")

    def conv_on_start_clicked(self):
        if self.converter_worker and self.converter_worker.isRunning():
            self.converter_worker.cancel()
            self.conv_start_btn.setText("Начать конвертацию")
            return

        if not hasattr(self, 'conv_folder'):
            QMessageBox.warning(self, "Ошибка", "Сначала выберите папку с Excel файлами!")
            return

        choice = "1" if self.conv_radio_txt.isChecked() else "2"

        self.conv_log.clear()
        self.conv_log.append("Запуск конвертации...\n")
        self.conv_progress.setValue(0)
        self.conv_progress.setMaximum(100)

        self.converter_worker = ConverterWorker(self.conv_folder, choice)
        self.converter_worker.log.connect(self.conv_log.append)
        self.converter_worker.progress.connect(self.conv_progress.setValue)
        self.converter_worker.result.connect(lambda c: self.conv_log.append(f"\n✅ Обработано файлов: {c}"))
        self.converter_worker.finished.connect(self.conv_on_finished)
        self.converter_worker.start()
        self.conv_start_btn.setText("Отмена")

    def conv_on_finished(self):
        self.conv_start_btn.setText("Начать конвертацию")