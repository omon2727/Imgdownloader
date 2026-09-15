from qtpy.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QTableView, QLabel, QMenu,
    QRadioButton, QButtonGroup, QLineEdit, QTextEdit, QProgressBar
)
from qtpy.QtCore import QAbstractTableModel, Qt
from qtpy.QtGui import QColor

from table_reader import UniversalTableReader
from workers.download_worker import DownloadWorker
from utils import create_header


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
        self.download_model = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(create_header("Скачивание изображений по ссылкам"))
        layout.addSpacing(10)

        # ===== Верхняя панель: файл + папка =====
        top = QHBoxLayout()
        self.file_btn = QPushButton("Выбрать файл")
        self.file_btn.setFixedWidth(180)
        self.file_btn.clicked.connect(self.download_open_file)

        self.dir_btn = QPushButton("Папка для скачивания")
        self.dir_btn.setFixedWidth(200)
        self.dir_btn.clicked.connect(self.download_select_directory)

        top.addStretch()
        top.addWidget(self.file_btn)
        top.addSpacing(15)
        top.addWidget(self.dir_btn)
        top.addStretch()
        layout.addLayout(top)
        layout.addSpacing(8)

        # ===== Настройки =====
        settings = QHBoxLayout()

        delim_label = QLabel("Разделитель ссылок:")
        self.delimiter_input = QLineEdit()
        self.delimiter_input.setFixedWidth(40)
        self.delimiter_input.setPlaceholderText(";")

        headers_label = QLabel("Первая строка:")
        self.radio_skip = QRadioButton("Пропустить")
        self.radio_no_skip = QRadioButton("Не пропускать")
        self.headers_group = QButtonGroup()
        self.headers_group.addButton(self.radio_skip)
        self.headers_group.addButton(self.radio_no_skip)
        self.radio_skip.setChecked(True)
        self.radio_skip.toggled.connect(self.download_update_headers)

        settings.addStretch()
        settings.addWidget(delim_label)
        settings.addWidget(self.delimiter_input)
        settings.addSpacing(20)
        settings.addWidget(headers_label)
        settings.addWidget(self.radio_skip)
        settings.addWidget(self.radio_no_skip)
        settings.addStretch()
        layout.addLayout(settings)
        layout.addSpacing(8)

        # ===== Подсказка =====
        hint = QLabel("Правой кнопкой по заголовку столбца: URL / Имя файла / Бренд")
        hint.setStyleSheet("color: gray;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        layout.addSpacing(5)

                # ===== Таблица =====
        self.table = QTableView()
        header = self.table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.download_open_menu)
        layout.addWidget(self.table, stretch=1)

        # ===== Кнопка старта =====
        start_layout = QHBoxLayout()
        self.start_btn = QPushButton("Начать")
        self.start_btn.setFixedWidth(220)
        self.start_btn.clicked.connect(self.download_on_start_cancel_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.start_btn)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        layout.addSpacing(8)

        # ===== Прогресс =====
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setEnabled(False)
        layout.addWidget(self.progress)
        layout.addSpacing(5)

        # ===== Лог =====
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(140)
        layout.addWidget(self.log_output)

    # ---------- действия ----------
    def download_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Файл", "", "All (*);;CSV (*.csv);;Excel (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            self.reader.read_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return

        # сброс назначений при новом файле
        self.reader.urls_column_index = None
        self.reader.filenames_column_index = None
        self.reader.brands_column_index = None

        preview = self.reader.data_frame.head(15)
        self.download_model = PandasModel(preview)
        self.table.setModel(self.download_model)

        self.log_output.append(f"Загружен файл: {path}")
        self.log_output.append(
            f"Строк: {len(self.reader.data_frame)}, столбцов: {self.reader.data_frame.shape[1]}"
        )

    def download_open_menu(self, pos):
        if self.download_model is None:
            return
        header = self.table.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < 0:
            return

        menu = QMenu(self)
        url_action = menu.addAction("Использовать как ссылки (URL)")
        name_action = menu.addAction("Использовать как имена файлов")
        brand_action = menu.addAction("Использовать как бренд")
        clear_action = menu.addAction("Сбросить назначение")

        action = menu.exec(header.mapToGlobal(pos))
        if action is url_action:
            self.download_model.url_col = col
            self.reader.urls_column_index = col
        elif action is name_action:
            self.download_model.name_col = col
            self.reader.filenames_column_index = col
        elif action is brand_action:
            self.download_model.brand_col = col
            self.reader.brands_column_index = col
        elif action is clear_action:
            if self.download_model.url_col == col:
                self.download_model.url_col = None
                self.reader.urls_column_index = None
            if self.download_model.name_col == col:
                self.download_model.name_col = None
                self.reader.filenames_column_index = None
            if self.download_model.brand_col == col:
                self.download_model.brand_col = None
                self.reader.brands_column_index = None

        self.table.viewport().update()
        self.table.horizontalHeader().viewport().update()

    def download_select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not directory:
            return
        self.reader.download_dir = directory
        self.log_output.append(f"Папка для скачивания: {directory}")

    def download_update_headers(self):
        self.reader.headers_column = self.radio_skip.isChecked()

    def download_on_start_cancel_clicked(self):
        if self.worker is not None and self.worker.is_running:
            self.download_cancel_processing()
        else:
            self.download_start_processing()

    def download_start_processing(self):
        try:
            if self.download_model is None or self.download_model.url_col is None:
                QMessageBox.warning(self, "Ошибка", "Назначьте столбец со ссылками (URL)")
                return
            if not self.reader.download_dir:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите папку для скачивания")
                return

            delimiter = self.delimiter_input.text().strip()
            if delimiter:
                self.reader.urls_delimiter = delimiter

            self.reader.urls_column_index = self.download_model.url_col
            self.reader.filenames_column_index = self.download_model.name_col
            self.reader.brands_column_index = self.download_model.brand_col
            self.reader.headers_column = self.radio_skip.isChecked()

            data = self.reader.preparing_data()
            data = [
                {
                    "url": item["url"],
                    "file_name": item["file_name"],
                    "brand": item.get("brand")
                }
                for item in data
            ]

            if not data:
                QMessageBox.warning(self, "Ошибка", "Нет данных для скачивания")
                return

            self.progress.setEnabled(True)
            self.progress.setMaximum(len(data))
            self.progress.setValue(0)
            self.log_output.append("\nНачинаю скачивание файлов по ссылкам...\n")

            self.worker = DownloadWorker(data, self.reader.download_dir)
            self.worker.progress.connect(self.download_update_progress)
            self.worker.log_item.connect(self.download_add_log_item)
            self.worker.result.connect(self.download_show_result)
            self.worker.cancelled.connect(self.download_on_cancelled)
            self.worker.log.connect(self.download_add_error_log)
            self.worker.finished.connect(self.download_on_finished)
            self.worker.start()

            self.start_btn.setText("Отмена")
            self.file_btn.setEnabled(False)
            self.dir_btn.setEnabled(False)
            self.delimiter_input.setEnabled(False)
            self.radio_skip.setEnabled(False)
            self.radio_no_skip.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def download_cancel_processing(self):
        if self.worker is not None and self.worker.is_running:
            self.log_output.append("\n<span style='color:orange'>Отмена скачивания...</span>")
            self.worker.cancel_download()

    def download_on_finished(self):
        self.start_btn.setText("Начать")
        self.file_btn.setEnabled(True)
        self.dir_btn.setEnabled(True)
        self.delimiter_input.setEnabled(True)
        self.radio_skip.setEnabled(True)
        self.radio_no_skip.setEnabled(True)

    def download_on_cancelled(self):
        self.log_output.append("\n<span style='color:orange'>Загрузка отменена пользователем.</span>")

    def download_add_log_item(self, text, success):
        color = "green" if success else "red"
        self.log_output.append(f'<span style="color:{color}">{text}</span>')

    def download_update_progress(self, value):
        self.progress.setValue(value)

    def download_show_result(self, total, errors_count):
        success = total - errors_count
        self.log_output.append("")
        self.log_output.append(
            f'<span style="color:black">'
            f'Готово. Успешно скачано файлов: {success} из {total}. '
            f'Ошибок: {errors_count}.'
            f'</span>'
        )

    def download_add_error_log(self, text):
        self.log_output.append(f'<span style="color:black">{text}</span>')