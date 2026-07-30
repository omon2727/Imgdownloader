from qtpy.QtCore import QThread, Signal
import asyncio
from files_downloader import FileDownloader


class DownloadWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    log_item = Signal(str, bool)
    result = Signal(int, int)
    cancelled = Signal()

    def __init__(self, data, download_dir):
        super().__init__()
        self.data = data
        self.download_dir = download_dir
        self.downloader = None
        self.is_running = False
        self.was_cancelled = False

    def run(self):
        self.is_running = True
        try:
            asyncio.run(self.async_run())
        finally:
            self.is_running = False
            self.finished.emit()

    async def async_run(self):
        self.downloader = FileDownloader()
        self.downloader.set_download_dir(self.download_dir)
        total = len(self.data)
        self.downloader.log_callback = lambda url, ok: self.log_item.emit(url, ok)

        async def monitor():
            while (self.downloader.process_items_count < total and not self.downloader.is_cancelled):
                self.progress.emit(self.downloader.process_items_count)
                await asyncio.sleep(0.1)

        monitor_task = asyncio.create_task(monitor())

        try:
            await self.downloader.download_files(self.data)
        except asyncio.CancelledError:
            pass
        finally:
            if not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass

            self.progress.emit(self.downloader.process_items_count)
            total = self.downloader.total_items_count
            errors_count = len(self.downloader.errors)

            if self.downloader.is_cancelled:
                self.was_cancelled = True
                self.cancelled.emit()
            else:
                self.result.emit(total, errors_count)

            if self.downloader.errors:
                for err in self.downloader.errors:
                    self.log.emit(err)

    def cancel_download(self):
        if self.downloader is not None:
            self.downloader.cancel()