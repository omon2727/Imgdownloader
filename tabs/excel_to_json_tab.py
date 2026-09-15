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
        self.param_cols = []
        self.manufacture_col = None
        self.model_col = None
        self.type_col = None
        self.engine_col = None

    def rowCount(self, parent=None):
        return self._df.shape[0]

    def columnCount(self, parent=None):
        return self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])

        if role == Qt.BackgroundRole:
            col = index.column()
            if col == self.brand_col:
                return QColor("#fff3cd")
            if col == self.article_display_col:
                return QColor("#cce5ff")
            if col == self.article_name_col:
                return QColor("#d4edda")
            if col == self.group_col:
                return QColor("#f8d7da")
            if col in self.param_cols:
                return QColor("#e2d5f1")
            if col == self.manufacture_col:
                return QColor("#d1ecf1")
            if col == self.model_col:
                return QColor("#d4edda")
            if col == self.type_col:
                return QColor("#fff3cd")
            if col == self.engine_col:
                return QColor("#fce4d6")  # оранжевый
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
            if section in self.param_cols:
                return f"{name} [ПАРАМЕТР]"
            if section == self.manufacture_col:
                return f"{name} [АВТОПРОИЗВОДИТЕЛЬ]"
            if section == self.model_col:
                return f"{name} [МОДЕЛЬ АВТО]"
            if section == self.type_col:
                return f"{name} [ТИП АВТО]"
            if section == self.engine_col:
                return f"{name} [ДВИГАТЕЛЬ]"
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

        hint = QLabel("Правой кнопкой мыши по заголовку столбца назначьте роли")
        hint.setStyleSheet("color: gray;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        layout.addSpacing(10)

        self.table = QTableView()
        header = self.table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.open_column_menu)
        layout.addWidget(self.table)

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
            self.model = PandasModel(self.df.head(15))
            self.table.setModel(self.model)

            header = self.table.horizontalHeader()
            

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
        brand_action = menu.addAction("Бренд")
        article_display_action = menu.addAction("Артикул на сайте")
        article_name_action = menu.addAction("Имя артикула")
        group_action = menu.addAction("Название группы")
        menu.addSeparator()
        param_action = menu.addAction("Параметр")
        menu.addSeparator()
        manufacture_action = menu.addAction("Автопроизводитель")
        model_action = menu.addAction("Модель авто")
        type_action = menu.addAction("Тип авто")
        engine_action = menu.addAction("Двигатель")
        menu.addSeparator()
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
        elif action is param_action:
            if col not in self.model.param_cols:
                self.model.param_cols.append(col)
        elif action is manufacture_action:
            self.model.manufacture_col = col
        elif action is model_action:
            self.model.model_col = col
        elif action is type_action:
            self.model.type_col = col
        elif action is engine_action:
            self.model.engine_col = col
        elif action is clear_action:
            if self.model.brand_col == col:
                self.model.brand_col = None
            if self.model.article_display_col == col:
                self.model.article_display_col = None
            if self.model.article_name_col == col:
                self.model.article_name_col = None
            if self.model.group_col == col:
                self.model.group_col = None
            if col in self.model.param_cols:
                self.model.param_cols.remove(col)
            if self.model.manufacture_col == col:
                self.model.manufacture_col = None
            if self.model.model_col == col:
                self.model.model_col = None
            if self.model.type_col == col:
                self.model.type_col = None
            if self.model.engine_col == col:
                self.model.engine_col = None

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
        ]) and not self.model.param_cols and all(x is None for x in [
            self.model.manufacture_col, self.model.model_col,
            self.model.type_col, self.model.engine_col
        ]):
            QMessageBox.warning(self, "Ошибка", "Назначьте хотя бы один столбец")
            return

        catalog_name = self.catalog_input.text().strip() or "jenya123"

        column_map = {
            "brand": self.model.brand_col,
            "article_display": self.model.article_display_col,
            "article_name": self.model.article_name_col,
            "group": self.model.group_col,
            "param_cols": list(self.model.param_cols),
            "manufacture": self.model.manufacture_col,
            "model": self.model.model_col,
            "type": self.model.type_col,
            "engine": self.model.engine_col
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