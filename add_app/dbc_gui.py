import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import asyncio
import subprocess
import threading
import sys

def resource_path(relative_path):
    """Путь к ресурсу работает и в .py, и в .exe (PyInstaller)"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Импортируем функции из твоего client
try:
    from .dbc_client import create_new_catalog, delete_catalog, add_data_to_catalog_async
except ImportError:
    from dbc_client import create_new_catalog, delete_catalog, add_data_to_catalog_async

# ==================== НАСТРОЙКИ ====================
# Путь к серверу (измени при необходимости)
SERVER_DIR = r"C:\Users\user\source\repos\REMZONA_api"
VENV_ACTIVATE = os.path.join(SERVER_DIR, "venv", "Scripts", "activate.bat")
UVICORN_CMD = "uvicorn api.api_:app --log-level debug --env-file core/.env"

# Имя каталога по умолчанию
DEFAULT_CATALOG = "jenya123"
# ===================================================


class App(tk.Tk):
    def __init__(self, initial_json_path=None):
        super().__init__()
        self.title("REMZONA Data Loader")
        try:
            self.iconbitmap(resource_path("icons/app.ico"))
        except Exception:
            pass  # если файла нет — просто пропускаем
        self.geometry("780x620")
        self.minsize(700, 550)

        self.json_data = None
        self.json_path = None
        self.server_process = None

        self._build_ui()
        if initial_json_path:
            self.load_json(initial_json_path)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self):
        # --- Верхняя панель: выбор файла ---
        file_frame = ttk.LabelFrame(self, text="JSON файл", padding=10)
        file_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.file_label = ttk.Label(file_frame, text="Файл не выбран", foreground="gray")
        self.file_label.pack(side="left", fill="x", expand=True)

        ttk.Button(file_frame, text="Выбрать JSON…", command=self.select_json).pack(side="right")

        # --- Каталог ---
        cat_frame = ttk.LabelFrame(self, text="Каталог", padding=10)
        cat_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(cat_frame, text="Имя каталога:").pack(side="left")
        self.catalog_var = tk.StringVar(value=DEFAULT_CATALOG)
        ttk.Entry(cat_frame, textvariable=self.catalog_var, width=30).pack(side="left", padx=8)

        # --- Кнопки команд ---
        btn_frame = ttk.LabelFrame(self, text="Команды", padding=10)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="1. Просмотр данных", command=self.view_data).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="2. Удалить каталог", command=self.delete_cat).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="3. Создать каталог", command=self.create_cat).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="4. Загрузить данные", command=self.load_data).pack(side="left", padx=4)

        # --- Сервер ---
        server_frame = ttk.LabelFrame(self, text="Сервер", padding=10)
        server_frame.pack(fill="x", padx=10, pady=5)

        self.server_status = ttk.Label(server_frame, text="Сервер не запущен", foreground="gray")
        self.server_status.pack(side="left", fill="x", expand=True)

        ttk.Button(server_frame, text="▶ Запустить сервер", command=self.start_server).pack(side="left", padx=4)
        ttk.Button(server_frame, text="■ Остановить сервер", command=self.stop_server).pack(side="left", padx=4)

        # --- Лог ---
        log_frame = ttk.LabelFrame(self, text="Лог", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log = scrolledtext.ScrolledText(log_frame, height=18, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        # Кнопка очистки лога
        ttk.Button(log_frame, text="Очистить лог", command=self.clear_log).pack(anchor="e", pady=(4, 0))

    # -------------------- Вспомогательные --------------------
    def log_msg(self, text, level="info"):
        self.log.configure(state="normal")
        colors = {"info": "black", "success": "green", "error": "red", "warn": "orange"}
        tag = level
        self.log.tag_config(tag, foreground=colors.get(level, "black"))
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def get_catalog(self):
        name = self.catalog_var.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Укажи имя каталога")
            return None
        return name

    # -------------------- JSON --------------------
    def load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.json_data = json.load(f)
            self.json_path = path
            self.file_label.config(text=os.path.basename(path), foreground="black")
            self.log_msg(f"Загружен JSON: {path}", "success")
            self.log_msg(
                f"Записей: {len(self.json_data) if isinstance(self.json_data, list) else 'не список'}"
            )
            return True
        except Exception as e:
            self.json_data = None
            self.json_path = None
            self.log_msg(f"Ошибка чтения JSON: {e}", "error")
            messagebox.showerror("Ошибка чтения JSON", str(e))
            return False

    def select_json(self):
        path = filedialog.askopenfilename(
            title="Выбери JSON файл",
            initialdir=os.path.join(os.getcwd(), "to_load"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        self.load_json(path)

    def view_data(self):
        if self.json_data is None:
            messagebox.showwarning("Нет данных", "Сначала выбери JSON файл")
            return
        self.log_msg("=== Просмотр данных ===")
        # Красивый вывод (первые 3 записи + общая информация)
        if isinstance(self.json_data, list):
            self.log_msg(f"Всего записей: {len(self.json_data)}")
            for i, item in enumerate(self.json_data[:3]):
                self.log_msg(f"[{i}] {json.dumps(item, ensure_ascii=False, indent=2)[:500]}...")
            if len(self.json_data) > 3:
                self.log_msg(f"... и ещё {len(self.json_data) - 3} записей")
        else:
            self.log_msg(json.dumps(self.json_data, ensure_ascii=False, indent=2)[:2000])

    # -------------------- Каталог --------------------
    def delete_cat(self):
        name = self.get_catalog()
        if not name:
            return
        if not messagebox.askyesno("Подтверждение", f"Удалить каталог «{name}»?"):
            return
        try:
            self.log_msg(f"Удаляю каталог «{name}»...")
            delete_catalog(name)
            self.log_msg(f"Каталог «{name}» удалён", "success")
        except Exception as e:
            self.log_msg(f"Ошибка удаления: {e}", "error")
            messagebox.showerror("Ошибка", str(e))

    def create_cat(self):
        name = self.get_catalog()
        if not name:
            return
        try:
            self.log_msg(f"Создаю каталог «{name}»...")
            create_new_catalog(name)
            self.log_msg(f"Каталог «{name}» создан", "success")
        except Exception as e:
            self.log_msg(f"Ошибка создания: {e}", "error")
            messagebox.showerror("Ошибка", str(e))

    def load_data(self):
        if self.json_data is None:
            messagebox.showwarning("Нет данных", "Сначала выбери JSON файл")
            return
        name = self.get_catalog()
        if not name:
            return

        def worker():
            try:
                self.log_msg("Начинаю загрузку данных...")
                asyncio.run(add_data_to_catalog_async(self.json_data))
                self.log_msg("Загрузка завершена успешно!", "success")
            except Exception as e:
                self.log_msg(f"Ошибка загрузки: {e}", "error")
                messagebox.showerror("Ошибка загрузки", str(e))

        threading.Thread(target=worker, daemon=True).start()

   # -------------------- Сервер --------------------
       # -------------------- Сервер --------------------
    def start_server(self):
        if self.server_process and self.server_process.poll() is None:
            messagebox.showinfo("Сервер", "Сервер уже запущен")
            return

        if not os.path.isdir(SERVER_DIR):
            messagebox.showerror("Ошибка", f"Папка сервера не найдена:\n{SERVER_DIR}")
            return

        python_exe = os.path.join(SERVER_DIR, "venv", "Scripts", "python.exe")
        if not os.path.isfile(python_exe):
            messagebox.showerror("Ошибка", f"Не найден python.exe:\n{python_exe}")
            return

        try:
            # Запуск без окна консоли
            self.server_process = subprocess.Popen(
                [
                    python_exe, "-m", "uvicorn",
                    "api.api_:app",
                    "--log-level", "debug",
                    "--env-file", "core/.env"
                ],
                cwd=SERVER_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW,  # ← без окна
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.server_status.config(text="Сервер запущен (в фоне)", foreground="green")
            self.log_msg(f"Сервер запущен в фоне (PID {self.server_process.pid})", "success")
        except Exception as e:
            self.log_msg(f"Не удалось запустить сервер: {e}", "error")
            messagebox.showerror("Ошибка", str(e))

    def stop_server(self):
        if not self.server_process or self.server_process.poll() is not None:
            self.server_status.config(text="Сервер не запущен", foreground="gray")
            self.log_msg("Сервер не был запущен", "warn")
            self.server_process = None
            return

        try:
            pid = self.server_process.pid
            self.log_msg(f"Останавливаю сервер (PID {pid})...")

            # Убиваем всё дерево процессов
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # чтобы taskkill тоже не мигал
            )

            try:
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass

            self.server_status.config(text="Сервер остановлен", foreground="gray")
            self.log_msg("Сервер остановлен", "warn")
        except Exception as e:
            self.log_msg(f"Ошибка при остановке: {e}", "error")
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.server_process = None


    def on_closing(self):
        """При закрытии окна останавливаем сервер, если он ещё работает"""
        if self.server_process and self.server_process.poll() is None:
            self.log_msg("Закрытие приложения — останавливаю сервер...", "warn")
            self.stop_server()
        self.destroy()

if __name__ == "__main__":
    initial_json_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = App(initial_json_path)
    app.mainloop()