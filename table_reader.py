from pathlib import Path
import pandas as pd
import re
from files_downloader import DownloadableItemDict
from typing import List


class UniversalTableReader:
    """
    Universal Table Loader for reading files in CSV, XLS, and XLSX formats.
    """

    def __init__(self, encoding="utf-8"):
        self.encoding: str = encoding
        self.data_frame: pd.DataFrame or None = None
        self.filenames_column_index: int or None = None
        self.urls_column_index: int or None = None
        self.brands_column_index: int or None = None
        self.download_dir: str or None = None
        self.urls_delimiter: str or None = None
        self.headers_column: bool = True

    def read_file(self, file_path, **kwargs) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix == ".csv":
            self.data_frame = self._read_csv(path)
        elif suffix in [".xlsx", ".xls"]:
            self.data_frame = self._read_excel(path, **kwargs)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def _read_excel(self, path, **kwargs):
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            return pd.read_excel(path, engine="openpyxl", header=None, **kwargs)
        elif suffix == ".xls":
            return pd.read_excel(path, engine="xlrd", header=None, **kwargs)

    def _read_csv(self, path):
        separators = [",", ";", "\t", "|"]
        for sep in separators:
            try:
                df = pd.read_csv(path, sep=sep, encoding=self.encoding)
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
        return pd.read_csv(path, encoding=self.encoding)

    def preparing_data(self) -> List[DownloadableItemDict]:
        result = []

        if self.urls_column_index is None:
            raise ValueError("urls_column_index не задан")

        urls_column = self.data_frame.iloc[:, self.urls_column_index]
        filenames_column = (
            self.data_frame.iloc[:, self.filenames_column_index]
            if self.filenames_column_index is not None
            else None
        )
        brands_column = (
            self.data_frame.iloc[:, self.brands_column_index]
            if self.brands_column_index is not None
            else None
        )

        start_i = 1 if self.headers_column else 0

        for i in range(start_i, len(urls_column)):
            urls_value = urls_column[i]
            if not isinstance(urls_value, str) or not urls_value.strip():
                continue

            # filename
            if filenames_column is None:
                filenames_value = str(i)
            else:
                filenames_value = filenames_column[i]
                if pd.isna(filenames_value):
                    filenames_value = str(i)
                else:
                    filenames_value = str(filenames_value)

            filenames_value = self.sanitize_filename(filenames_value)

            # brand
            brand_value = None
            if brands_column is not None:
                brand_value = brands_column[i]
                if isinstance(brand_value, str):
                    brand_value = self.sanitize_filename(brand_value)
                else:
                    brand_value = None

            split_urls = [u.strip() for u in urls_value.split(self.urls_delimiter or ",") if u.strip()]

            for j, url in enumerate(split_urls):
                # === УЛУЧШЕННОЕ ОПРЕДЕЛЕНИЕ РАСШИРЕНИЯ ===
                ext = self._get_extension(url)

                filename = (
                    f"{filenames_value}_{j + 1}{ext}"
                    if len(split_urls) > 1
                    else f"{filenames_value}{ext}"
                )

                item = {
                    "file_name": filename,
                    "url": url
                }
                if brand_value:
                    item["brand"] = brand_value

                result.append(item)

        return result

    @staticmethod
    def _get_extension(url: str) -> str:
        """Определяет расширение из URL"""
        path = Path(url)
        ext = path.suffix.lower()
        if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.avif'}:
            return ext
        return '.jpg'  # fallback по умолчанию

    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 200) -> str:
        if not filename:
            return "unnamed"
        filename = re.sub(r'[<>:"/\\|?*]', ' ', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        return filename or "unnamed"