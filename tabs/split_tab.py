from qtpy.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QLabel, QTextEdit, QProgressBar, QSpinBox
)
from workers.splitter_worker import SplitterWorker

from utils import create_header


class SplitTab(QWidget):
    def __init__(self):
        super().__init__()
        self.splitter_worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(create_header("Разбивка большого Excel-файла на части"))
        layout.addSpacing(25)

        file_layout = QHBoxLayout()
        self.split_file_btn = QPushButton("Выбрать Excel файл")
        self.split_file_btn.setFixedWidth(240)
        self.split_file_btn.clicked.connect(self.split_select_file)
        file_layout.addStretch()
        file_layout.addWidget(self.split_file_btn)
        file_layout.addStretch()
        layout.addLayout(file_layout)
        layout.addSpacing(10)

        out_layout = QHBoxLayout()
        self.split_output_btn = QPushButton("Выбрать папку для сохранения")
        self.split_output_btn.setFixedWidth(240)
        self.split_output_btn.clicked.connect(self.split_select_output_dir)
        out_layout.addStretch()
        out_layout.addWidget(self.split_output_btn)
        out_layout.addStretch()
        layout.addLayout(out_layout)
        layout.addSpacing(15)

        chunk_layout = QHBoxLayout()
        chunk_label = QLabel("Строк в одном файле:")
        self.split_chunk_spin = QSpinBox()
        self.split_chunk_spin.setFixedWidth(140)
        self.split_chunk_spin.setMinimum(100)
        self.split_chunk_spin.setMaximum(1000000)
        self.split_chunk_spin.setValue(300)
        self.split_chunk_spin.setSingleStep(100)
        chunk_layout.addStretch()
        chunk_layout.addWidget(chunk_label)
        chunk_layout.addWidget(self.split_chunk_spin)
        chunk_layout.addStretch()
        layout.addLayout(chunk_layout)
        layout.addSpacing(30)

        start_layout = QHBoxLayout()
        self.split_start_btn = QPushButton("Начать разбивку")
        self.split_start_btn.setFixedWidth(260)
        self.split_start_btn.clicked.connect(self.split_on_start_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.split_start_btn)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        layout.addSpacing(20)

        self.split_progress = QProgressBar()
        self.split_progress.setValue(0)
        layout.addWidget(self.split_progress)
        layout.addSpacing(10)

        self.split_log = QTextEdit()
        self.split_log.setReadOnly(True)
        layout.addWidget(self.split_log)

    def split_select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите Excel файл", "", "Excel (*.xlsx *.xls)")
        if path:
            self.split_input_file = path
            self.split_log.append(f"Выбран файл: {path}")

    def split_select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if directory:
            self.split_output_dir = directory
            self.split_log.append(f"Папка сохранения: {directory}")

    def split_on_start_clicked(self):
        if self.splitter_worker and self.splitter_worker.isRunning():
            self.splitter_worker.cancel()
            self.split_start_btn.setText("Начать разбивку")
            return

        if not hasattr(self, 'split_input_file') or not hasattr(self, 'split_output_dir'):
            QMessageBox.warning(self, "Ошибка", "Сначала выберите файл и папку!")
            return

        chunk_size = self.split_chunk_spin.value()
        self.split_log.clear()
        self.split_log.append("Запуск разбивки...\n")
        self.split_progress.setValue(0)
        self.split_progress.setMaximum(100)

        self.splitter_worker = SplitterWorker(
            self.split_input_file,
            self.split_output_dir,
            chunk_size
        )
        self.splitter_worker.log.connect(self.split_log.append)
        self.splitter_worker.progress.connect(self.split_progress.setValue)
        self.splitter_worker.result.connect(lambda count: self.split_log.append(f"\n✅ Создано файлов: {count}"))
        self.splitter_worker.finished.connect(self.split_on_finished)
        self.splitter_worker.start()
        self.split_start_btn.setText("Отмена")

    def split_on_finished(self):
        self.split_progress.setValue(100)
        self.split_start_btn.setText("Начать разбивку")