import aiohttp
import aiofiles
import asyncio
import os
import re
from pathlib import Path
from typing import List, TypedDict, Dict


class DownloadableItemDict(TypedDict):
    url: str
    file_name: str
    brand: str or None


class FileDownloader:
    __batch_size = 10

    def __init__(self):
        self.path2download_dir: str or None = None
        self.errors: list = []
        self.total_items_count: int = 0
        self.process_items_count: int = 0
        self.log_callback = None
        self.is_cancelled: bool = False
        self.skip_existing: bool = False
        self._name_counters: Dict[str, int] = {}  # Для надёжной нумерации

    def set_download_dir(self, path: str):
        full_path = os.path.abspath(path)
        os.makedirs(full_path, exist_ok=True)
        self.path2download_dir = full_path

    def __reset_counters(self):
        self.errors.clear()
        self.total_items_count = 0
        self.process_items_count = 0
        self.is_cancelled = False
        self._name_counters.clear()

    def cancel(self):
        self.is_cancelled = True

    def _get_unique_filename(self, directory: str, base_filename: str) -> str:
        """Самая надёжная версия с глобальным счётчиком"""
        key = (directory, base_filename)  # ключ = папка + исходное имя

        if key not in self._name_counters:
            self._name_counters[key] = 0

        target_dir = Path(directory)
        name = Path(base_filename)
        stem = name.stem
        suffix = name.suffix.lower()

        # Убираем старый номер если есть
        match = re.search(r'(.+?)_(\d+)$', stem)
        if match:
            base_stem = match.group(1)
        else:
            base_stem = stem

        # Увеличиваем счётчик
        self._name_counters[key] += 1
        counter = self._name_counters[key]

        new_filename = f"{base_stem}_{counter}{suffix}"

        # На случай, если файл уже существует от предыдущих запусков
        while (target_dir / new_filename).exists():
            self._name_counters[key] += 1
            counter = self._name_counters[key]
            new_filename = f"{base_stem}_{counter}{suffix}"

        return new_filename

    async def __download_file(self, session, item: DownloadableItemDict):
        if self.is_cancelled:
            return

        if not self.path2download_dir:
            raise ValueError("FileDownloader.path2download_dir is None")

        url = item["url"]
        original_file_name = item["file_name"]
        brand = item.get("brand")

        if brand:
            safe_brand = brand.strip().replace("/", "_")
            folder = os.path.join(self.path2download_dir, safe_brand)
            os.makedirs(folder, exist_ok=True)
            target_dir = folder
        else:
            target_dir = self.path2download_dir

        final_file_name = self._get_unique_filename(target_dir, original_file_name)
        filepath = os.path.join(target_dir, final_file_name)

        try:
            async with session.get(url) as response:
                if self.is_cancelled:
                    self.process_items_count += 1
                    return

                if response.status != 200:
                    msg = f"{url} -> HTTP {response.status}"
                    self.errors.append(f"> {msg}")
                    if self.log_callback:
                        self.log_callback(url, False)
                    self.process_items_count += 1
                    return

                # Fallback расширения
                if not Path(final_file_name).suffix:
                    content_type = response.headers.get('content-type', '')
                    if 'webp' in content_type:
                        final_file_name += '.webp'
                        filepath += '.webp'
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        final_file_name += '.jpg'
                        filepath += '.jpg'
                    elif 'png' in content_type:
                        final_file_name += '.png'
                        filepath += '.png'

                async with aiofiles.open(filepath, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        if self.is_cancelled:
                            try:
                                if os.path.exists(filepath):
                                    os.remove(filepath)
                            except Exception:
                                pass
                            self.process_items_count += 1
                            return
                        await f.write(chunk)

                if self.log_callback:
                    self.log_callback(f"✓ {final_file_name}", True)

        except Exception as e:
            self.errors.append(f"> {url} -> Exception: {e}")
            if self.log_callback:
                self.log_callback(url, False)
        finally:
            self.process_items_count += 1

    async def download_files(self, data: List[DownloadableItemDict]):
        self.__reset_counters()
        self.total_items_count = len(data)

        timeout = aiohttp.ClientTimeout(total=30, sock_connect=10)

        async def process_batch(batch: List[DownloadableItemDict]):
            async with aiohttp.ClientSession(timeout=timeout) as session:
                tasks = [self.__download_file(session, item) for item in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

        batch_tasks = []
        for item in data:
            if self.is_cancelled:
                break
            batch_tasks.append(item)
            if len(batch_tasks) >= self.__batch_size:
                await process_batch(batch_tasks)
                batch_tasks = []

        if batch_tasks and not self.is_cancelled:
            await process_batch(batch_tasks)