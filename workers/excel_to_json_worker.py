import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from qtpy.QtCore import QThread, Signal


def clean(value):
    """Очистка значения от nan / None"""
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() == "nan":
        return ""
    return s


class ExcelToJsonWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    result = Signal(int)

    def __init__(self, excel_path: str, output_dir: str, column_map: dict, catalog_name: str = "jenya123"):
        """
        column_map:
        {
            "brand": int | None,
            "article_display": int | None,
            "article_name": int | None,
            "group": int | None,
            "param_cols": [int, ...],
            "manufacture": int | None,
            "model": int | None,
            "type": int | None,
            "engine": int | None
        }
        """
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
            df = pd.read_excel(self.excel_path, header=None)

            header_row = df.iloc[0]
            data_df = df.iloc[1:]

            brand_col = self.column_map.get("brand")
            article_display_col = self.column_map.get("article_display")
            article_name_col = self.column_map.get("article_name")
            group_col = self.column_map.get("group")
            param_cols = self.column_map.get("param_cols") or []
            manufacture_col = self.column_map.get("manufacture")
            model_col = self.column_map.get("model")
            type_col = self.column_map.get("type")
            engine_col = self.column_map.get("engine")

            db_parts = []
            total = len(data_df)

            for i, (_, row) in enumerate(data_df.iterrows()):
                if self.is_cancelled:
                    self.log.emit("Операция отменена.")
                    break

                brand = clean(row.iloc[brand_col]) if brand_col is not None else ""
                article_display = clean(row.iloc[article_display_col]) if article_display_col is not None else ""
                article_name = clean(row.iloc[article_name_col]) if article_name_col is not None else ""
                group = clean(row.iloc[group_col]) if group_col is not None else ""

                if not any([brand, article_display, article_name, group]):
                    continue

                db_part = {
                    "catalog": self.catalog_name,
                    "supplier": {
                        "name": brand
                    },
                    "article": {
                        "name": article_name,
                        "display": article_display
                    }
                }

                if group_col is not None:
                    db_part["products"] = [
                        {
                            "name": group
                        }
                    ]

                # ===== params =====
                # добавляем только если значение ячейки НЕ пустое
                if param_cols:
                    params = []
                    for col_idx in param_cols:
                        param_name = clean(header_row.iloc[col_idx])
                        param_value = clean(row.iloc[col_idx])
                        if param_value:  # только при непустом значении
                            params.append({
                                "name": param_name,
                                "value": param_value
                            })
                    if params:
                        db_part["params"] = params

                # ===== vehicles =====
                if any(x is not None for x in [manufacture_col, model_col, type_col, engine_col]):
                    manufacture = clean(row.iloc[manufacture_col]) if manufacture_col is not None else ""
                    model = clean(row.iloc[model_col]) if model_col is not None else ""
                    vehicle_type = clean(row.iloc[type_col]) if type_col is not None else ""
                    engine = clean(row.iloc[engine_col]) if engine_col is not None else ""

                    db_part["vehicles"] = [
                        {
                            "manufacture": {
                                "name": manufacture
                            },
                            "model": {
                                "name": model
                            },
                            "type": {
                                "name": vehicle_type
                            },
                            "engine": {
                                "name": engine
                            }
                        }
                    ]

                db_parts.append(db_part)

                if i % 50 == 0:
                    self.progress.emit(int((i / total) * 100))

            if self.is_cancelled:
                return

            os.makedirs(self.output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

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