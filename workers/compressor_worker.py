from qtpy.QtCore import QThread, Signal
from files_compressor import Compressor


class CompressorWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    result = Signal(int, int)
    cancelled = Signal()

    def __init__(self, compressor: Compressor):
        super().__init__()
        self.compressor = compressor
        self.is_running = False
        self.was_cancelled = False

    def run(self):
        self.is_running = True
        try:
            self.compressor.log_callback = self._on_file_packed
            self.compressor.run()

            if self.compressor._cancelled:
                self.was_cancelled = True
                self.cancelled.emit()
            else:
                self.log.emit("Архивирование завершено успешно!")
                self.result.emit(self.compressor.all_files_count, 0)
        except Exception as e:
            self.log.emit(f"Ошибка при архивировании: {str(e)}")
            self.result.emit(0, 1)
        finally:
            self.is_running = False
            self.finished.emit()

    def _on_file_packed(self, file_name: str):
        self.progress.emit(self.compressor.files_count)
        self.log.emit(f"Добавлено в архив: {file_name}")

    def cancel_compression(self):
        if self.compressor:
            self.compressor.cancel()