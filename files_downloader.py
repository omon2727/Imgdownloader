import aiohttp
import aiofiles
import asyncio
import os
import re
import shutil
import subprocess
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from typing import List, TypedDict, Dict, Optional, Callable, Tuple
from urllib.parse import urlparse


class DownloadableItemDict(TypedDict):
    url: str
    file_name: str
    brand: Optional[str]


class FileDownloader:
    __batch_size = 10
    __max_retries = 4
    __max_cookie_refreshes = 2  # сколько раз подряд обрабатываем заглушку с cookie на один файл
    __retry_delay = 1.5

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    }

    # Заглушка вида: document.cookie = 'dhd2=abc; max-age=86400; path=/; domain=example.com'
    _STUB_COOKIE_RE = re.compile(r"""document\.cookie\s*=\s*(['"])(.+?)\1""", re.DOTALL)

    def __init__(self):
        self.path2download_dir: Optional[str] = None
        self.errors: list[str] = []
        self.total_items_count: int = 0
        self.process_items_count: int = 0
        self.log_callback: Optional[Callable[..., None]] = None
        self.is_cancelled: bool = False
        self.skip_existing: bool = False
        self._name_counters: Dict[str, int] = {}
        self._curl_path = self._find_curl()

    @staticmethod
    def _find_curl():
        # На Windows нужен именно curl.exe, не alias PowerShell
        if os.name == "nt":
            for candidate in ("curl.exe", r"C:\Windows\System32\curl.exe"):
                path = shutil.which(candidate) if not os.path.isabs(candidate) else (
                    candidate if os.path.exists(candidate) else None
                )
                if path:
                    return path
            return None
        return shutil.which("curl")

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
        key = (directory, base_filename)
        if key not in self._name_counters:
            self._name_counters[key] = 0

        target_dir = Path(directory)
        name = Path(base_filename)
        stem = name.stem
        suffix = name.suffix.lower()

        match = re.search(r'(.+?)_(\d+)$', stem)
        base_stem = match.group(1) if match else stem

        self._name_counters[key] += 1
        counter = self._name_counters[key]
        new_filename = f"{base_stem}_{counter}{suffix}"

        while (target_dir / new_filename).exists():
            self._name_counters[key] += 1
            counter = self._name_counters[key]
            new_filename = f"{base_stem}_{counter}{suffix}"

        return new_filename

    def _is_protected_cdn(self, url: str) -> bool:
        host = (urlparse(url).netloc or "").lower()
        return "revolutionparts" in host

    @staticmethod
    def _is_html_bytes(head: bytes) -> bool:
        head = head.lstrip().lower()
        return head.startswith((b"<!doctype html", b"<html", b"<head"))

    def _is_html_file(self, path: str) -> bool:
        try:
            with open(path, "rb") as f:
                return self._is_html_bytes(f.read(512))
        except Exception:
            return False

    @classmethod
    def _parse_js_cookie(cls, html: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
        """Достаёт cookie из страницы-заглушки, которая ставит её через JS.

        Возвращает (имя, значение, атрибуты) или None, если в странице такого скрипта нет.
        """
        m = cls._STUB_COOKIE_RE.search(html)
        if not m:
            return None
        parts = [p.strip() for p in m.group(2).split(";") if p.strip()]
        if not parts or "=" not in parts[0]:
            return None
        name, value = parts[0].split("=", 1)
        name, value = name.strip(), value.strip()
        if not name:
            return None
        attrs: Dict[str, str] = {}
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                attrs[k.strip().lower()] = v.strip()
        return name, value, attrs

    @staticmethod
    def _apply_js_cookie(session: aiohttp.ClientSession, response_url,
                         parsed: Tuple[str, str, Dict[str, str]]) -> bool:
        """Кладёт cookie из заглушки в cookie jar сессии (аналог document.cookie в браузере)."""
        name, value, attrs = parsed
        try:
            host = (response_url.host or "").lower()
            c = SimpleCookie()
            c[name] = value
            c[name]["path"] = attrs.get("path", "/")
            domain = attrs.get("domain", "").lstrip(".").lower()
            # домен принимаем только если он относится к хосту ответа, как это делает браузер
            if domain and (host == domain or host.endswith("." + domain)):
                c[name]["domain"] = domain
            if "max-age" in attrs:
                c[name]["max-age"] = attrs["max-age"]
            session.cookie_jar.update_cookies(c, response_url)
            return True
        except Exception:
            return False

    def _build_headers(self, url: str) -> dict:
        headers = dict(self.DEFAULT_HEADERS)
        try:
            parsed = urlparse(url)
            host = (parsed.netloc or "").lower()
            if "revolutionparts" in host:
                headers["Referer"] = "https://www.revolutionparts.com/"
                headers["Origin"] = "https://www.revolutionparts.com"
            elif parsed.scheme and parsed.netloc:
                headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        except Exception:
            pass
        return headers

    def _download_with_curl(self, url: str, filepath: str) -> bool:
        if not self._curl_path:
            return False

        headers = self._build_headers(url)
        cmd = [
            self._curl_path,
            "-sS",
            "-L",
            "--fail",
            "-o", filepath,
            "-A", headers["User-Agent"],
            "-H", f"Accept: {headers['Accept']}",
            "-H", f"Accept-Language: {headers['Accept-Language']}",
        ]
        if "Referer" in headers:
            cmd.extend(["-e", headers["Referer"]])
        if "Origin" in headers:
            cmd.extend(["-H", f"Origin: {headers['Origin']}"])
        cmd.append(url)

        try:
            kwargs = {"capture_output": True, "timeout": 60}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(cmd, **kwargs)
            if (
                result.returncode == 0
                and os.path.exists(filepath)
                and os.path.getsize(filepath) > 0
                and not self._is_html_file(filepath)
            ):
                return True
        except Exception:
            pass

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        return False

    def _download_with_urllib(self, url: str, filepath: str) -> bool:
        """Ещё один fallback — urllib с браузерными заголовками"""
        headers = self._build_headers(url)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if not data or self._is_html_bytes(data[:512]):
                return False
            with open(filepath, "wb") as f:
                f.write(data)
            return True
        except Exception:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
            return False

    async def __download_file(self, session: aiohttp.ClientSession, item: DownloadableItemDict):
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
        headers = self._build_headers(url)

        last_error = None
        need_fallback = False
        attempt = 0
        cookie_refreshes = 0

        while attempt < self.__max_retries:
            attempt += 1
            if self.is_cancelled:
                return

            try:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    if self.is_cancelled:
                        self.process_items_count += 1
                        return

                    content_type = response.headers.get("Content-Type", "").lower()

                    # --- Заглушка: сайт отдаёт 202/HTML и ставит cookie через JS ---
                    if response.status == 202 or (
                        response.status == 200 and content_type.startswith("text/html")
                    ):
                        html = await response.text(errors="ignore")
                        parsed = self._parse_js_cookie(html)

                        if parsed and cookie_refreshes < self.__max_cookie_refreshes:
                            if self._apply_js_cookie(session, response.url, parsed):
                                cookie_refreshes += 1
                                attempt -= 1  # обработка заглушки не считается неудачной попыткой
                                last_error = f"{url} -> заглушка, cookie '{parsed[0]}' применена"
                                continue

                        if response.status == 202:
                            last_error = (
                                f"{url} -> HTTP 202 (сервер вернул заглушку вместо изображения)"
                            )
                            if attempt < self.__max_retries:
                                await asyncio.sleep(self.__retry_delay * attempt)
                                continue
                            break

                        msg = f"{url} -> HTML-страница вместо изображения (HTTP 200)"
                        self.errors.append(f"> {msg}")
                        if self.log_callback:
                            self.log_callback(url, False)
                        self.process_items_count += 1
                        return

                    if response.status in (403, 429, 503):
                        last_error = f"{url} -> HTTP {response.status}"
                        need_fallback = True
                        if attempt < self.__max_retries:
                            await asyncio.sleep(self.__retry_delay * attempt)
                            continue
                        break

                    if response.status != 200:
                        msg = f"{url} -> HTTP {response.status}"
                        self.errors.append(f"> {msg}")
                        if self.log_callback:
                            self.log_callback(url, False)
                        self.process_items_count += 1
                        return

                    head = await response.content.read(512)
                    if self._is_html_bytes(head):
                        msg = f"{url} -> HTML-страница вместо изображения (HTTP 200)"
                        self.errors.append(f"> {msg}")
                        if self.log_callback:
                            self.log_callback(url, False)
                        self.process_items_count += 1
                        return

                    if not Path(final_file_name).suffix:
                        if "webp" in content_type:
                            final_file_name += ".webp"
                            filepath += ".webp"
                        elif "jpeg" in content_type or "jpg" in content_type:
                            final_file_name += ".jpg"
                            filepath += ".jpg"
                        elif "png" in content_type:
                            final_file_name += ".png"
                            filepath += ".png"

                    async with aiofiles.open(filepath, "wb") as f:
                        await f.write(head)
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
                    self.process_items_count += 1
                    return

            except Exception as e:
                last_error = f"{url} -> Exception: {e}"
                need_fallback = True
                if attempt < self.__max_retries:
                    await asyncio.sleep(self.__retry_delay * attempt)
                    continue
                break

        # Fallback 1: curl.exe
        if need_fallback:
            ok = await asyncio.to_thread(self._download_with_curl, url, filepath)
            if ok:
                if self.log_callback:
                    self.log_callback(f"✓ {final_file_name}", True)
                self.process_items_count += 1
                return

            # Fallback 2: urllib
            ok = await asyncio.to_thread(self._download_with_urllib, url, filepath)
            if ok:
                if self.log_callback:
                    self.log_callback(f"✓ {final_file_name}", True)
                self.process_items_count += 1
                return

        self.errors.append(f"> {last_error or url}")
        if self.log_callback:
            self.log_callback(url, False)
        self.process_items_count += 1

    async def download_files(self, data: List[DownloadableItemDict]):
        self.__reset_counters()
        self.total_items_count = len(data)

        timeout = aiohttp.ClientTimeout(total=90, sock_connect=20)

        # Одна сессия на весь запуск: cookie из заглушки хранится в её cookie jar
        # и используется для всех следующих картинок.
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=self.DEFAULT_HEADERS
        ) as session:

            has_protected = any(self._is_protected_cdn(item["url"]) for item in data)

            if has_protected:
                for item in data:
                    if self.is_cancelled:
                        break
                    await self.__download_file(session, item)
                    await asyncio.sleep(0.3)
            else:
                batch_tasks = []
                for item in data:
                    if self.is_cancelled:
                        break
                    batch_tasks.append(item)
                    if len(batch_tasks) >= self.__batch_size:
                        tasks = [self.__download_file(session, it) for it in batch_tasks]
                        await asyncio.gather(*tasks, return_exceptions=True)
                        batch_tasks = []

                if batch_tasks and not self.is_cancelled:
                    tasks = [self.__download_file(session, it) for it in batch_tasks]
                    await asyncio.gather(*tasks, return_exceptions=True)