from qtpy.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QTableView, QLabel, QMenu,
    QTextEdit, QProgressBar, QLineEdit
)
from qtpy.QtCore import QAbstractTableModel, Qt
from qtpy.QtGui import QColor

import pandas as pd
from workers.excel_to_json_worker import ExcelToJsonWorker
from utils import create_header


class PandasModel(QAbstractTableModel):
    def __init__(self, df):
        super().__init__()
        self._df = df
        self.brand_col = None
        self.article_display_col = None
        self.article_name_col = None
        self.group_col = None

    def rowCount(self, parent=None):
        return self._df.shape[0]

    def columnCount(self, parent=None):
        return self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])

        if role == Qt.BackgroundRole:
            if index.column() == self.brand_col:
                return QColor("#fff3cd")
            if index.column() == self.article_display_col:
                return QColor("#cce5ff")
            if index.column() == self.article_name_col:
                return QColor("#d4edda")
            if index.column() == self.group_col:
                return QColor("#f8d7da")
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            name = str(self._df.columns[section])
            if section == self.brand_col:
                return f"{name} [БРЕНД]"
            if section == self.article_display_col:
                return f"{name} [АРТИКУЛ НА САЙТЕ]"
            if section == self.article_name_col:
                return f"{name} [ИМЯ АРТИКУЛА]"
            if section == self.group_col:
                return f"{name} [ГРУППА]"
            return name
        return None


class ExcelToJsonTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.excel_path = None
        self.output_dir = None
        self.df = None
        self.model = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(create_header("Excel → JSON для базы данных"))
        layout.addSpacing(15)

        # Выбор файла и папки
        top = QHBoxLayout()
        self.file_btn = QPushButton("Выбрать Excel файл")
        self.file_btn.setFixedWidth(200)
        self.file_btn.clicked.connect(self.select_file)

        self.folder_btn = QPushButton("Папка для сохранения")
        self.folder_btn.setFixedWidth(200)
        self.folder_btn.clicked.connect(self.select_folder)

        top.addStretch()
        top.addWidget(self.file_btn)
        top.addSpacing(15)
        top.addWidget(self.folder_btn)
        top.addStretch()
        layout.addLayout(top)
        layout.addSpacing(15)

        # Поле catalog
        catalog_layout = QHBoxLayout()
        catalog_label = QLabel("Название каталога (catalog):")
        self.catalog_input = QLineEdit()
        self.catalog_input.setFixedWidth(200)
        self.catalog_input.setText("jenya123")
        self.catalog_input.setPlaceholderText("jenya123")

        catalog_layout.addStretch()
        catalog_layout.addWidget(catalog_label)
        catalog_layout.addSpacing(10)
        catalog_layout.addWidget(self.catalog_input)
        catalog_layout.addStretch()
        layout.addLayout(catalog_layout)
        layout.addSpacing(15)

        # Подсказка
        hint = QLabel("Правой кнопкой мыши по заголовку столбца назначьте роли")
        hint.setStyleSheet("color: gray;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        layout.addSpacing(10)

        # Таблица
        self.table = QTableView()
        layout.addWidget(self.table)

        # Кнопка
        start_layout = QHBoxLayout()
        self.start_btn = QPushButton("Начать преобразование")
        self.start_btn.setFixedWidth(260)
        self.start_btn.clicked.connect(self.on_start_clicked)
        start_layout.addStretch()
        start_layout.addWidget(self.start_btn)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        layout.addSpacing(15)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        layout.addSpacing(10)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Excel файл", "", "Excel (*.xlsx *.xls)"
        )
        if not path:
            return

        try:
            self.df = pd.read_excel(path, header=None)
            self.excel_path = path
            # показываем первые 15 строк (включая шапку для удобства)
            self.model = PandasModel(self.df.head(15))
            self.table.setModel(self.model)

            header = self.table.horizontalHeader()
            header.setContextMenuPolicy(Qt.CustomContextMenu)
            header.customContextMenuRequested.connect(self.open_column_menu)

            self.log.append(f"Загружен файл: {path}")
            self.log.append(f"Строк: {len(self.df)}, столбцов: {self.df.shape[1]}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def select_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if directory:
            self.output_dir = directory
            self.log.append(f"Папка сохранения: {directory}")

    def open_column_menu(self, pos):
        if self.model is None:
            return

        header = self.table.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < 0:
            return

        menu = QMenu(self)
        brand_action = menu.addAction("Использовать как Бренд")
        article_display_action = menu.addAction("Использовать как Артикул на сайте")
        article_name_action = menu.addAction("Использовать как Имя артикула")
        group_action = menu.addAction("Использовать как Название группы")
        clear_action = menu.addAction("Сбросить назначение")

        action = menu.exec(header.mapToGlobal(pos))

        if action is brand_action:
            self.model.brand_col = col
        elif action is article_display_action:
            self.model.article_display_col = col
        elif action is article_name_action:
            self.model.article_name_col = col
        elif action is group_action:
            self.model.group_col = col
        elif action is clear_action:
            if self.model.brand_col == col:
                self.model.brand_col = None
            if self.model.article_display_col == col:
                self.model.article_display_col = None
            if self.model.article_name_col == col:
                self.model.article_name_col = None
            if self.model.group_col == col:
                self.model.group_col = None

        self.table.viewport().update()
        self.table.horizontalHeader().viewport().update()

    def on_start_clicked(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.start_btn.setText("Начать преобразование")
            return

        if not self.excel_path:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите Excel файл")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите папку для сохранения")
            return
        if self.model is None:
            QMessageBox.warning(self, "Ошибка", "Файл не загружен")
            return

        if all(x is None for x in [
            self.model.brand_col,
            self.model.article_display_col,
            self.model.article_name_col,
            self.model.group_col
        ]):
            QMessageBox.warning(self, "Ошибка", "Назначьте хотя бы один столбец")
            return

        catalog_name = self.catalog_input.text().strip() or "jenya123"

        column_map = {
            "brand": self.model.brand_col,
            "article_display": self.model.article_display_col,
            "article_name": self.model.article_name_col,
            "group": self.model.group_col
        }

        self.log.append("\nЗапуск преобразования...\n")
        self.progress.setValue(0)

        self.worker = ExcelToJsonWorker(
            self.excel_path,
            self.output_dir,
            column_map,
            catalog_name=catalog_name
        )
        self.worker.log.connect(self.log.append)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.result.connect(lambda count: self.log.append(f"\n✅ Обработано записей: {count}"))
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

        self.start_btn.setText("Отмена")

    def on_finished(self):
        self.start_btn.setText("Начать преобразование")
        self.progress.setValue(100)