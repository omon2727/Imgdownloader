import asyncio
from aiohttp import ClientTimeout, ClientSession
import requests
import json


def create_new_catalog(catalog_name: str, url: str = "http://127.0.0.1:8000/api/catalog/") -> None:
    """Создать новый каталог"""
    # catalog_name = catalog_name.replace('_', "-")
    catalog_name = catalog_name.replace('-', "_")
    r = requests.get(url=url + catalog_name)
    if r.status_code == 200:
        print(f"Database tables with the prefix {catalog_name}_ have been successfully created")
        return
    else:
        raise ValueError(r.status_code)


def delete_catalog(catalog_name: str, url: str = "http://127.0.0.1:8000/api/catalog/") -> None:
    """Удалить существующий каталог со всеми данными"""
    catalog_name = catalog_name.rstrip('_')
    r = requests.delete(url=url, json={"catalog": catalog_name})
    if r.status_code != 200:
        raise ValueError(r.status_code)
    return print("Success...")


def add_data_to_catalog(data: dict, url: str = "http://127.0.0.1:8000/api/catalog/") -> None:
    """Добавить данные в каталог"""
    data['catalog'] = data['catalog'].rstrip('_')
    r = requests.post(url=url, json=data)
    if r.status_code != 200:
        except_message = f"{r.status_code}, data -> {json.dumps(data, ensure_ascii=False)}'"
        raise ValueError(except_message)
    return print("Success")


##########################################

async def send_post_request(session: ClientSession, url: str, data: dict, semaphore: asyncio.Semaphore,
                            timeout) -> None:
    """
    Отправляет один POST запрос с семафором
    """
    async with semaphore:
        try:
            async with session.post(url, json=data, timeout=ClientTimeout(total=timeout)) as response:
                response.raise_for_status()
                print(response.status)

        except Exception as ex:
            print(f"data -> {json.dumps(data, ensure_ascii=False)}")
            raise ex


        
async def add_data_to_catalog_async(
    items: list[dict],
    url: str = "http://127.0.0.1:8000/api/catalog",
    max_concurrent: int = 10,
    timeout: int = 30,
) -> None:
    """Асинхронная функция для записи данных в каталог. Принимает список словарей."""
    if not items:
        print("done: nothing to send")
        return []

    semaphore = asyncio.Semaphore(max_concurrent)

    async with ClientSession() as session:
        # 1. Шлём первый элемент отдельно — как "пробный"
        first = items[0]
        await send_post_request(session, url, first, semaphore, timeout)

        # 2. Если первый ок — гоним остальные
        rest = items[1:]
        if rest:
            tasks = [send_post_request(session, url, item, semaphore, timeout) for item in items]
            await asyncio.gather(*tasks, return_exceptions=True)

        print("done")


# # old version 
# async def add_data_to_catalog_async(items: list[dict], url: str = "http://127.0.0.1:8000/api/catalog/",
#                                     max_concurrent: int = 10, timeout: int = 30) -> None:  
#     """Асинхронная функция для записи данных в каталог. Принимает список словарей.l: URL эндпоинта"""
#     # # # чтобы увеличить кол-во запросов за раз, изменить инт=10, можно 20-25
#     semaphore = asyncio.Semaphore(max_concurrent)

#     async with ClientSession() as session:
#         tasks = [send_post_request(session, url, item, semaphore, timeout) for item in items]
#         await asyncio.gather(*tasks, return_exceptions=True)

#     print("done")


### run
# asyncio.run(add_data_to_catalog_async(items))
