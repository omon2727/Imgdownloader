import sys
from qtpy.QtWidgets import QApplication
from gui import MainWindow
from utils import apply_app_style
import multiprocessing


if __name__ == "__main__":
    multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    apply_app_style(app)

    w = MainWindow()
    w.show()

    sys.exit(app.exec())
