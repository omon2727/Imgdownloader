from pathlib import Path
from datetime import datetime
from qtpy.QtCore import QThread, Signal
import pandas as pd


class ConverterWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    result = Signal(int)

    def __init__(self, source_folder, format_choice):
        super().__init__()
        self.source_folder = source_folder
        self.format_choice = format_choice  # "1" или "2"
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            source_path = Path(self.source_folder)

            if self.format_choice == "1":
                file_ext = ".txt"
                format_name = "Текст_Юникод"
                sep = '\t'
                encoding = 'utf-16'
                lineterminator = '\r\n'
            else:
                file_ext = ".csv"
                format_name = "CSV_разделитель_;"
                sep = ';'
                encoding = 'utf-8-sig'
                lineterminator = '\r\n'

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_folder = source_path / f"{format_name}_{timestamp}"
            output_folder.mkdir(parents=True, exist_ok=True)

            self.log.emit(f"Создана папка: {output_folder}\n")

            excel_files = list(source_path.glob("*.xlsx")) + list(source_path.glob("*.XLSX"))
            excel_files = sorted(set(excel_files))

            self.log.emit(f"Найдено Excel-файлов: {len(excel_files)}\n")

            if not excel_files:
                self.log.emit("Excel-файлы не найдены.")
                self.result.emit(0)
                return

            for i, file_path in enumerate(excel_files, 1):
                if self.is_cancelled:
                    self.log.emit("Конвертация отменена.")
                    break

                try:
                    self.log.emit(f"Обрабатываю: {file_path.name}")
                    df = pd.read_excel(file_path, sheet_name=0)

                    output_filename = file_path.stem + file_ext
                    output_path = output_folder / output_filename

                    df.to_csv(
                        output_path,
                        sep=sep,
                        index=False,
                        encoding=encoding,
                        lineterminator=lineterminator
                    )

                    self.log.emit(f" ✓ Готово: {output_filename} ({len(df)} строк)")
                    self.progress.emit(int((i / len(excel_files)) * 100))

                except Exception as e:
                    self.log.emit(f" ✗ Ошибка {file_path.name}: {e}")

            self.result.emit(len(excel_files))
            self.log.emit("\n✅ Конвертация завершена!")
            self.log.emit(f"Результаты в: {output_folder}")

        except Exception as e:
            self.log.emit(f"Критическая ошибка: {e}")
        finally:
            self.finished.emit()