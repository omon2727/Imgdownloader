from qtpy.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QTableView, QLabel, QMenu,
    QRadioButton, QButtonGroup, QLineEdit, QTextEdit, QProgressBar
)
from qtpy.QtCore import QAbstractTableModel, Qt
from qtpy.QtGui import QColor, QPixmap, QFont

from table_reader import UniversalTableReader
from workers.download_worker import DownloadWorker

from utils import get_resource_path, create_header


class PandasModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        self._df = df
        self.url_col = None
        self.name_col = None
        self.brand_col = None

    def rowCount(self, parent=None):
        return self._df.shape[0]

    def columnCount(self, parent=None):
        return self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])
        if role == Qt.BackgroundRole:
            if index.column() == self.url_col:
                return QColor("#cce5ff")
            if index.column() == self.name_col:
                return QColor("#d4edda")
            if index.column() == self.brand_col:
                return QColor("#fff3cd")
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            name = str(self._df.columns[section])
            if section == self.url_col:
                return f"{name} [URL]"
            if section == self.name_col:
                return f"{name} [NAME]"
            if section == self.brand_col:
                return f"{name} [BRAND]"
            return name
        return None


class DownloadTab(QWidget):
    def __init__(self):
        super().__init__()
        self.reader = UniversalTableReader()
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(create_header("Скачивание изображений по ссылкам"))
        layout.addSpacing(20)

        self.download_stack_layout = QVBoxLayout()
        layout.addLayout(self.download_stack_layout)

        self.download_start_screen = self._create_download_start_screen()
        self.download_preview_screen = self._create_download_preview_screen()
        self.download_process_screen = self._create_download_process_screen()

        self.download_stack_layout.addWidget(self.download_start_screen)

    def _create_download_start_screen(self):
        screen = QWidget()
        layout = QVBoxLayout()
        btn = QPushButton("Выбрать файл")
        btn.setFixedWidth(150)
        btn.clicked.connect(self.download_open_file)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        placeholder = QLabel("Поддерживаемые файлы в формате .csv, .xls, .xlsx")
        placeholder.setStyleSheet("color: gray; font-size: 14px;")
        placeholder_layout = QHBoxLayout()
        placeholder_layout.addStretch()
        placeholder_layout.addWidget(placeholder)
        placeholder_layout.addStretch()
        layout.addLayout(placeholder_layout)
        layout.addStretch()
        screen.setLayout(layout)
        return screen

    def _create_download_preview_screen(self):
        screen = QWidget()
        layout = QVBoxLayout()
        top = QHBoxLayout()
        self.download_back_btn = QPushButton("Назад")
        self.download_back_btn.clicked.connect(self.download_go_back)
        self.download_forward_btn = QPushButton("Вперёд")
        self.download_forward_btn.setEnabled(False)
        self.download_forward_btn.clicked.connect(self.download_process_data)
        top.addWidget(self.download_back_btn)
        top.addStretch()
        top.addWidget(self.download_forward_btn)
        layout.addSpacing(10)
        layout.addLayout(top)
        layout.addSpacing(20)
        self.download_table = QTableView()
        layout.addWidget(self.download_table)
        screen.setLayout(layout)
        return screen

    def _create_download_process_screen(self):
        screen = QWidget()
        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.download_back_process_btn = QPushButton("Назад")
        self.download_back_process_btn.setFixedWidth(100)
        self.download_back_process_btn.clicked.connect(self.download_go_back_to_preview)
        top_layout.addWidget(self.download_back_process_btn)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        layout.addSpacing(20)

        center_layout = QHBoxLayout()
        self.download_dir_button = QPushButton("Выбрать папку для скачивания")
        self.download_dir_button.setFixedWidth(260)
        self.download_dir_button.clicked.connect(self.download_select_directory)
        center_layout.addStretch()
        center_layout.addWidget(self.download_dir_button)
        center_layout.addStretch()
        layout.addLayout(center_layout)
        layout.addSpacing(20)

        delim_layout = QHBoxLayout()
        delim_label = QLabel("Разделитель ссылок:")
        self.download_delimiter_input = QLineEdit()
        self.download_delimiter_input.setFixedWidth(40)
        delim_layout.addStretch()
        delim_layout.addWidget(delim_label)
        delim_layout.addSpacing(10)
        delim_layout.addWidget(self.download_delimiter_input)
        delim_layout.addStretch()
        layout.addLayout(delim_layout)
        layout.addSpacing(20)

        headers_layout = QHBoxLayout()
        headers_label = QLabel("Пропустить первую строку (заголовки)?")
        self.download_radio_skip = QRadioButton("Пропустить")
        self.download_radio_no_skip = QRadioButton("Не пропускать")
        self.download_headers_group = QButtonGroup()
        self.download_headers_group.addButton(self.download_radio_skip)
        self.download_headers_group.addButton(self.download_radio_no_skip)
        self.download_radio_skip.setChecked(True)
        self.download_radio_skip.toggled.connect(self.download_update_headers)
        headers_layout.addStretch()
        headers_layout.addWidget(headers_label)
        headers_layout.addSpacing(10)
        headers_layout.addWidget(self.download_radio_skip)
        headers_layout.addWidget(self.download_radio_no_skip)
        headers_layout.addStretch()
        layout.addLayout(headers_layout)
        layout.addSpacing(20)

        start_layout = QHBoxLayout()
        self.download_start_button = QPushButton("Начать")
        self.download_start_button.setFixedWidth(260)
        self.download_start_button.clicked.connect(self.download_on_start_cancel_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.download_start_button)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        layout.addSpacing(20)

        self.download_progress = QProgressBar()
        self.download_progress.setValue(0)
        self.download_progress.setEnabled(False)
        layout.addWidget(self.download_progress)
        layout.addSpacing(10)

        self.download_log_output = QTextEdit()
        self.download_log_output.setReadOnly(True)
        layout.addWidget(self.download_log_output)

        screen.setLayout(layout)
        return screen

    def download_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Файл", "", "All (*);;CSV (*.csv);;Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            self.reader.read_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.download_show_preview()

    def download_show_preview(self):
        preview = self.reader.data_frame.head(10)
        self.download_model = PandasModel(preview)
        self.download_table.setModel(self.download_model)
        header = self.download_table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.download_open_menu)
        self._switch_download_screen(self.download_preview_screen)

    def download_open_menu(self, pos):
        header = self.download_table.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < 0:
            return
        menu = QMenu(self)
        url_action = menu.addAction("Использовать как ссылки")
        name_action = menu.addAction("Использовать как имена файлов")
        brand_action = menu.addAction("Использовать как бренд")
        action = menu.exec(header.mapToGlobal(pos))
        if action is url_action:
            self.download_model.url_col = col
            self.reader.urls_column_index = col
            self.download_forward_btn.setEnabled(True)
        elif action is name_action:
            self.download_model.name_col = col
            self.reader.filenames_column_index = col
        elif action is brand_action:
            self.download_model.brand_col = col
            self.reader.brands_column_index = col
        self.download_table.viewport().update()

    def download_process_data(self):
        self.reader.urls_column_index = self.download_model.url_col
        self.reader.filenames_column_index = self.download_model.name_col
        self.reader.brands_column_index = self.download_model.brand_col
        self._switch_download_screen(self.download_process_screen)

    def download_go_back(self):
        self.reader = UniversalTableReader()
        self.download_table.setModel(None)
        self.download_forward_btn.setEnabled(False)
        self._switch_download_screen(self.download_start_screen)

    def download_go_back_to_preview(self):
        self._switch_download_screen(self.download_preview_screen)

    def download_select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not directory:
            return
        self.reader.download_dir = directory
        self.download_log_output.append(f"Папка для скачивания: {directory}")

    def download_on_start_cancel_clicked(self):
        if self.worker is not None and self.worker.is_running:
            self.download_cancel_processing()
        else:
            self.download_start_processing()

    def download_start_processing(self):
        try:
            delimiter = self.download_delimiter_input.text().strip()
            if delimiter:
                self.reader.urls_delimiter = delimiter

            if not self.reader.download_dir:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите папку")
                return

            data = self.reader.preparing_data()
            data = [
                {
                    "url": item["url"],
                    "file_name": item["file_name"],
                    "brand": item.get("brand")
                }
                for item in data
            ]

            self.download_progress.setEnabled(True)
            self.download_progress.setMaximum(len(data))
            self.download_progress.setValue(0)
            self.download_log_output.append("Начинаю скачивание файлов по ссылкам...\n")

            self.worker = DownloadWorker(data, self.reader.download_dir)
            self.worker.progress.connect(self.download_update_progress)
            self.worker.log_item.connect(self.download_add_log_item)
            self.worker.result.connect(self.download_show_result)
            self.worker.cancelled.connect(self.download_on_cancelled)
            self.worker.log.connect(self.download_add_error_log)
            self.worker.finished.connect(self.download_on_finished)
            self.worker.start()

            self.download_start_button.setText("Отмена")
            self.download_dir_button.setEnabled(False)
            self.download_delimiter_input.setEnabled(False)
            self.download_radio_skip.setEnabled(False)
            self.download_radio_no_skip.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def download_cancel_processing(self):
        if self.worker is not None and self.worker.is_running:
            self.download_log_output.append("\n<span style='color:orange'>Отмена скачивания...</span>")
            self.worker.cancel_download()

    def download_on_finished(self):
        self.download_start_button.setText("Начать")
        self.download_dir_button.setEnabled(True)
        self.download_delimiter_input.setEnabled(True)
        self.download_radio_skip.setEnabled(True)
        self.download_radio_no_skip.setEnabled(True)

    def download_on_cancelled(self):
        self.download_log_output.append("\n<span style='color:orange'>Загрузка отменена пользователем.</span>")

    def download_add_log_item(self, url, success):
        color = "green" if success else "red"
        self.download_log_output.append(f'<span style="color:{color}">{url}</span>')

    def download_update_progress(self, value):
        self.download_progress.setValue(value)

    def download_show_result(self, total, errors_count):
        success = total - errors_count
        self.download_log_output.append("")
        self.download_log_output.append(
            f'<span style="color:black">'
            f'Готово. Успешно скачано файлов: {success} из {total}. '
            f'Ошибок: {errors_count}.'
            f'</span>'
        )

    def download_add_error_log(self, text):
        self.download_log_output.append(f'<span style="color:black">{text}</span>')

    def download_update_headers(self):
        self.reader.headers_column = self.download_radio_skip.isChecked()

    def _switch_download_screen(self, new_screen):
        while self.download_stack_layout.count():
            item = self.download_stack_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        self.download_stack_layout.addWidget(new_screen)
        new_screen.show()