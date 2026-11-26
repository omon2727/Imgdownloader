import sys
from qtpy.QtWidgets import QApplication
from gui import MainWindow
from utils import apply_app_style
import multiprocessing


if __name__ == "__main__":
    multiprocessing.freeze_support()

    # В собранном приложении загрузчик запускается повторным экземпляром
    # этого же exe. В исходниках тот же режим вызывается через run.py.
    if "--db-loader" in sys.argv:
        from add_app.dbc_gui import App

        loader_args = [arg for arg in sys.argv[1:] if arg != "--db-loader"]
        initial_json_path = loader_args[0] if loader_args else None
        loader_app = App(initial_json_path)
        loader_app.mainloop()
        sys.exit(0)

    app = QApplication(sys.argv)
    apply_app_style(app)

    w = MainWindow()
    w.show()

    sys.exit(app.exec())
