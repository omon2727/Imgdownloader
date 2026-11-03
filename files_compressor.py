from typing import Optional, Callable
import zipfile
import os
from pathlib import Path


class Compressor:

    def __init__(self):
        self.path2dir: Optional[str] = None
        self.pack: Optional[int] = None
        self.all_files_count: Optional[int] = None
        self.files_count: Optional[int] = 0
        self.archive_name: Optional[str] = None
        self.log_callback: Optional[Callable[[str], None]] = None
        self._cancelled: bool = False

    def cancel(self):
        self._cancelled = True

    def _split_into_chunks_batch(self) -> list[list[str]]:
        if not self.path2dir:
            raise ValueError('self.path2dir is None')
        file_list = [
            entry.name for entry in Path(self.path2dir).iterdir()
            if entry.is_file() and entry.suffix.lower() != ".zip"
        ]
        if not self.pack:
            raise ValueError('self.pack_files is None')
        self.all_files_count = len(file_list)
        if self.all_files_count == 0:
            return []

        if self.all_files_count <= self.pack:
            return [[os.path.join(self.path2dir, file_name) for file_name in file_list]]

        result = []
        start_i = 0
        stop_i = start_i + self.pack
        while start_i < self.all_files_count:
            if stop_i > self.all_files_count:
                stop_i = self.all_files_count
            result.append([os.path.join(self.path2dir, file_name) for file_name in file_list[start_i: stop_i]])

            start_i += self.pack
            stop_i += self.pack
        return result

    def _pack_files(self, files: list, archive_name: str):
        archive_path = os.path.join(self.path2dir, archive_name)
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if self._cancelled:
                        return False

                    file_name = Path(file_path).name
                    zipf.write(file_path, arcname=file_name)
                    self.files_count += 1

                    if self.log_callback:
                        self.log_callback(file_name)
            return True
        finally:
            if self._cancelled and os.path.exists(archive_path):
                os.remove(archive_path)
                # add file to archive
                file_name = Path(file_path).name
                zipf.write(file_path, arcname=file_name)
                self.files_count += 1

                #  callback for log
                if self.log_callback:
                    self.log_callback(file_name)

    def reset_values(self):
        self.pack: Optional[int] = None
        self.all_files_count: Optional[int] = None
        self.files_count: Optional[int] = 0
        self.archive_name: Optional[str] = None

    def run(self):

        files = self._split_into_chunks_batch()
        self.files_count = 0
        if not files:
            return 0
        if len(files) == 1:
            archive_name = f"{self.archive_name}.zip"
            self._pack_files(files[0], archive_name)
            return self.all_files_count
        for i in range(len(files)):
            if self._cancelled:
                return self.files_count
            archive_name = f"{self.archive_name}_{str(i + 1)}.zip"
            self._pack_files(files[i], archive_name)
        return self.files_count
