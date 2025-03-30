"""Тестирование api расписания (админ)"""


import requests
import json

BASE_URL = "http://127.0.0.1:5000"
API_KEY = "f3caa8cb-57dc-4c16-9726-7e58818a625a"
HEADERS = {"X-API-Key": API_KEY}

def test_post_schedule():
    """Тестирование POST (создание записи расписания)."""
    print("Тестирование POST (создание записи расписания)...")
    payload = {
        "class_id": 1,
        "subject_id": 1,
        "teacher_id": 4006,
        "day_of_week": "Monday",
        "start_time": "09:00",
        "end_time": "10:00"
    }
    response = requests.post(f"{BASE_URL}/api/admin/schedule", json=payload, headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    if response.status_code == 201:
        return response.json()["schedule"]["schedule_id"]
    else:
        print("Ошибка при создании записи расписания!")
        return None

def test_get_schedule(schedule_id):
    """Тестирование GET (получение записи расписания)."""
    print(f"\nТестирование GET (получение записи расписания {schedule_id})...")
    response = requests.get(f"{BASE_URL}/api/admin/schedule/{schedule_id}", headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_patch_schedule(schedule_id):
    """Тестирование PATCH (обновление записи расписания)."""
    print(f"\nТестирование PATCH (обновление записи расписания {schedule_id})...")
    payload = {
        "day_of_week": "Tuesday",
        "start_time": "10:00",
        "end_time": "11:00"
    }
    response = requests.patch(f"{BASE_URL}/api/admin/schedule/{schedule_id}", json=payload, headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_delete_schedule(schedule_id):
    """Тестирование DELETE (удаление записи расписания)."""
    print(f"\nТестирование DELETE (удаление записи расписания {schedule_id})...")
    response = requests.delete(f"{BASE_URL}/api/admin/schedule/{schedule_id}", headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_all_schedules_api():
    """Тестирование GET-запроса к /api/admin/schedules для получения списка всех записей расписания."""
    print("\nТестирование GET /api/admin/schedules...")
    try:
        # Отправляем GET-запрос
        response = requests.get(f"{BASE_URL}/api/admin/schedules", headers=HEADERS)

        # Выводим статус-код и тело ответа
        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            print("Ответ:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Ошибка: {response.json().get('message', 'Неизвестная ошибка')}")

    except requests.exceptions.ConnectionError:
        print("Ошибка: Не удалось подключиться к серверу. Убедитесь, что сервер запущен.")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    # Тестируем создание, получение, обновление и удаление одной записи расписания
    schedule_id = test_post_schedule()
    if schedule_id:
        test_get_schedule(schedule_id)
        test_patch_schedule(schedule_id)
        test_delete_schedule(schedule_id)
    else:
        print("Тесты прерваны из-за ошибки в POST.")

    # Тестируем получение списка всех записей расписания
    test_all_schedules_api()