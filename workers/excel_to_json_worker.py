import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from qtpy.QtCore import QThread, Signal


class ExcelToJsonWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    result = Signal(int)

    def __init__(self, excel_path: str, output_dir: str, column_map: dict, catalog_name: str = "jenya123"):
        super().__init__()
        self.excel_path = excel_path
        self.output_dir = output_dir
        self.column_map = column_map
        self.catalog_name = catalog_name
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        try:
            self.log.emit(f"Читаем файл: {self.excel_path}")
            # header=None + пропускаем первую строку (шапку)
            df = pd.read_excel(self.excel_path, header=None)
            df = df.iloc[1:]  # начинаем со 2-й строки

            brand_col = self.column_map.get("brand")
            article_display_col = self.column_map.get("article_display")
            article_name_col = self.column_map.get("article_name")
            group_col = self.column_map.get("group")

            db_parts = []
            total = len(df)

            for i, (_, row) in enumerate(df.iterrows()):
                if self.is_cancelled:
                    self.log.emit("Операция отменена.")
                    break

                brand = str(row.iloc[brand_col]).strip() if brand_col is not None else ""
                article_display = str(row.iloc[article_display_col]).strip() if article_display_col is not None else ""
                article_name = str(row.iloc[article_name_col]).strip() if article_name_col is not None else ""
                group = str(row.iloc[group_col]).strip() if group_col is not None else ""

                # пропускаем полностью пустые строки
                if not any([brand, article_display, article_name, group]):
                    continue

                # защита от nan
                if brand.lower() == "nan":
                    brand = ""
                if article_display.lower() == "nan":
                    article_display = ""
                if article_name.lower() == "nan":
                    article_name = ""
                if group.lower() == "nan":
                    group = ""

                db_part = {
                    "catalog": self.catalog_name,
                    "supplier": {
                        "name": brand
                    },
                    "products": [
                        {
                            "name": group
                        }
                    ],
                    "article": {
                        "name": article_name,
                        "display": article_display
                    }
                }
                db_parts.append(db_part)

                if i % 50 == 0:
                    self.progress.emit(int((i / total) * 100))

            if self.is_cancelled:
                return

            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            # Только один файл — массив JSON
            db_path = Path(self.output_dir) / f"parts_for_db_{timestamp}.json"
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(db_parts, f, ensure_ascii=False, indent=2)

            self.log.emit(f"✓ JSON для базы: {db_path.name}")
            self.log.emit(f"Всего записей: {len(db_parts)}")
            self.progress.emit(100)
            self.result.emit(len(db_parts))
            self.log.emit("\n✅ Готово!")

        except Exception as e:
            self.log.emit(f"Ошибка: {e}")
        finally:
            self.finished.emit()