from qtpy.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QLabel, QLineEdit, QTextEdit, QProgressBar, QSpinBox
)
from files_compressor import Compressor
from workers.compressor_worker import CompressorWorker
from qtpy.QtCore import Qt
from utils import create_header


class CompressTab(QWidget):
    def __init__(self):
        super().__init__()
        self.compressor = Compressor()
        self.compress_worker = None
        self.compress_selected_folder = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(create_header("Упаковка файлов в архив"))
        layout.addSpacing(20)

        self.compress_stack_layout = QVBoxLayout()
        layout.addLayout(self.compress_stack_layout)

        self.compress_start_screen = self._create_compress_start_screen()
        self.compress_params_screen = self._create_compress_params_screen()
        self.compress_stack_layout.addWidget(self.compress_start_screen)

    def _create_compress_start_screen(self):
        screen = QWidget()
        layout = QVBoxLayout()
        btn = QPushButton("Выбрать папку")
        btn.setFixedWidth(150)
        btn.clicked.connect(self.compress_select_folder)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        placeholder = QLabel("Выберите папку с файлами для архивирования")
        placeholder.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(placeholder, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        screen.setLayout(layout)
        return screen

    def _create_compress_params_screen(self):
        screen = QWidget()
        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.compress_back_params_btn = QPushButton("Назад")
        self.compress_back_params_btn.setFixedWidth(100)
        self.compress_back_params_btn.clicked.connect(self.compress_go_back)
        top_layout.addWidget(self.compress_back_params_btn)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        layout.addSpacing(20)

        archive_name_layout = QHBoxLayout()
        archive_name_label = QLabel("Имя архива(ов):")
        self.compress_archive_name_input = QLineEdit()
        self.compress_archive_name_input.setFixedWidth(200)
        self.compress_archive_name_input.setPlaceholderText("archive")
        archive_name_layout.addStretch()
        archive_name_layout.addWidget(archive_name_label)
        archive_name_layout.addSpacing(10)
        archive_name_layout.addWidget(self.compress_archive_name_input)
        archive_name_layout.addStretch()
        layout.addLayout(archive_name_layout)
        layout.addSpacing(20)

        max_files_layout = QHBoxLayout()
        max_files_label = QLabel("Макс. количество файлов в архиве:")
        self.compress_max_files_input = QSpinBox()
        self.compress_max_files_input.setFixedWidth(100)
        self.compress_max_files_input.setMinimum(1)
        self.compress_max_files_input.setMaximum(10000)
        self.compress_max_files_input.setValue(100)
        max_files_layout.addStretch()
        max_files_layout.addWidget(max_files_label)
        max_files_layout.addSpacing(10)
        max_files_layout.addWidget(self.compress_max_files_input)
        max_files_layout.addStretch()
        layout.addLayout(max_files_layout)
        layout.addSpacing(30)

        start_layout = QHBoxLayout()
        self.compress_start_button = QPushButton("Начать")
        self.compress_start_button.setFixedWidth(260)
        self.compress_start_button.clicked.connect(self.compress_on_start_cancel_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.compress_start_button)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        layout.addSpacing(20)

        self.compress_progress = QProgressBar()
        self.compress_progress.setValue(0)
        self.compress_progress.setEnabled(False)
        layout.addWidget(self.compress_progress)
        layout.addSpacing(10)

        self.compress_log_output = QTextEdit()
        self.compress_log_output.setReadOnly(True)
        layout.addWidget(self.compress_log_output)

        screen.setLayout(layout)
        return screen

    def compress_select_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку с файлами")
        if not directory:
            return
        self.compress_selected_folder = directory
        self.compressor.path2dir = directory
        self._switch_compress_screen(self.compress_params_screen)

    def compress_go_back(self):
        self.compress_selected_folder = None
        self.compressor.path2dir = None
        self.compress_archive_name_input.clear()
        self.compress_max_files_input.setValue(100)
        self.compress_log_output.clear()
        self.compress_progress.setValue(0)
        self._switch_compress_screen(self.compress_start_screen)

    def compress_on_start_cancel_clicked(self):
        if self.compress_worker is not None and self.compress_worker.is_running:
            self.compress_cancel_processing()
        else:
            self.compress_start_processing()

    def compress_on_cancelled(self):
        self.compress_log_output.append(
            "\n<span style='color:orange'>Архивирование отменено пользователем.</span>"
        )

    def compress_start_processing(self):
        try:
            archive_name = self.compress_archive_name_input.text().strip()
            max_files = self.compress_max_files_input.value()

            if not archive_name:
                QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите имя архива")
                return
            if max_files <= 0:
                QMessageBox.warning(self, "Ошибка", "Количество файлов должно быть больше нуля")
                return
            if not self.compress_selected_folder:
                QMessageBox.warning(self, "Ошибка", "Папка не выбрана")
                return

            self.compress_progress.setEnabled(True)
            self.compress_progress.setValue(0)
            self.compress_log_output.clear()
            self.compress_log_output.append(f"Начинаю архивирование папки: {self.compress_selected_folder}\n")
            self.compress_log_output.append(f"Имя архива: {archive_name}\n")
            self.compress_log_output.append(f"Макс. файлов в архиве: {max_files}\n\n")

            compressor = Compressor()
            compressor.path2dir = self.compress_selected_folder
            compressor.archive_name = archive_name
            compressor.pack = int(max_files)

            self.compress_worker = CompressorWorker(compressor)
            self.compress_worker.progress.connect(self.compress_update_progress)
            self.compress_worker.log.connect(self.compress_add_log)
            self.compress_worker.result.connect(self.compress_show_result)
            self.compress_worker.finished.connect(self.compress_on_finished)
            self.compress_worker.cancelled.connect(self.compress_on_cancelled)
            self.compress_worker.start()

            self.compress_start_button.setText("Отмена")
            self.compress_archive_name_input.setEnabled(False)
            self.compress_max_files_input.setEnabled(False)
            self.compress_back_params_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def compress_cancel_processing(self):
        if self.compress_worker and self.compress_worker.is_running:
            self.compress_log_output.append("\n<span style='color:orange'>Отмена архивирования...</span>")
            self.compress_worker.cancel_compression()

    def compress_on_finished(self):
        self.compress_start_button.setText("Начать")
        self.compress_archive_name_input.setEnabled(True)
        self.compress_max_files_input.setEnabled(True)
        self.compress_back_params_btn.setEnabled(True)

    def compress_update_progress(self, value):
        if self.compress_worker and self.compress_worker.compressor.all_files_count:
            max_value = self.compress_worker.compressor.all_files_count
            self.compress_progress.setMaximum(max_value)
            self.compress_progress.setValue(value)

    def compress_add_log(self, text):
        self.compress_log_output.append(f'<span style="color:black">{text}</span>')

    def compress_show_result(self, total, errors_count):
        self.compress_log_output.append("")
        if errors_count == 0:
            self.compress_log_output.append(
                f'<span style="color:green">Готово. Архивировано файлов: {total}.</span>'
            )
        else:
            self.compress_log_output.append(
                f'<span style="color:red">Ошибка при архивировании. Обработано файлов: {total}. Ошибок: {errors_count}.</span>'
            )

    def _switch_compress_screen(self, new_screen):
        while self.compress_stack_layout.count():
            item = self.compress_stack_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        self.compress_stack_layout.addWidget(new_screen)
        new_screen.show()