try:
    from .dbc_client import create_new_catalog, delete_catalog, add_data_to_catalog, add_data_to_catalog_async
except ImportError:
    from dbc_client import create_new_catalog, delete_catalog, add_data_to_catalog, add_data_to_catalog_async
import asyncio
import json
import os

def read_json_file(filename):
    path = os.path.join("to_load", filename)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# # Чтение файла для загрузки, изменять название файла

data = read_json_file("parts_for_db_2026-09-11_11-38-55.json")

# # Просмотр данных

print(data)

# # # Удаление каталога

# delete_catalog("jenya123")

# # # Создание каталога

# create_new_catalog("jenya1234")

# # # # # Запуск загрузчика

# asyncio.run(add_data_to_catalog_async(data))





