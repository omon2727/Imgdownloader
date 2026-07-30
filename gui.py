import os
from qtpy.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from qtpy.QtGui import QIcon

from utils import get_resource_path
from tabs.download_tab import DownloadTab
from tabs.compress_tab import CompressTab
from tabs.split_tab import SplitTab
from tabs.converter_tab import ConverterTab
from tabs.excel_to_json_tab import ExcelToJsonTab


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        icon_path = get_resource_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setWindowTitle("RemzonaDownloader")
        self.resize(950, 720)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(DownloadTab(), "Скачать файлы по ссылкам")
        self.tabs.addTab(CompressTab(), "Упаковать файлы в архив")
        self.tabs.addTab(SplitTab(), "Разбивка файла")
        self.tabs.addTab(ConverterTab(), "Конвертер Excel")
        self.tabs.addTab(ExcelToJsonTab(), "Excel → JSON")