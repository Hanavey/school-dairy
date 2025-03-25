import requests
import json

BASE_URL = "http://127.0.0.1:5000"
API_KEY = "f3caa8cb-57dc-4c16-9726-7e58818a625"  # Используем ключ из логов
HEADERS = {"X-API-Key": API_KEY}

def test_post_teacher():
    print("Тестирование POST (создание учителя)...")
    payload = {
        "username": "test_teacher",
        "password": "teach123",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone_number": "+9876543210",
    }
    response = requests.post(f"{BASE_URL}/api/admin/teacher", json=payload, headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    if response.status_code == 201:
        return response.json()["teacher"]["teacher_id"]
    else:
        print("Ошибка при создании учителя!")
        return None

def test_get_teacher(teacher_id):
    print(f"\nТестирование GET (получение учителя {teacher_id})...")
    response = requests.get(f"{BASE_URL}/api/admin/teacher/{teacher_id}", headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_patch_teacher(teacher_id):
    print(f"\nТестирование PATCH (обновление учителя {teacher_id})...")
    payload = {
        "first_name": "Janet",
        "email": "janet.smith@example.com",
        "position_id": 1,  # Например, назначение на должность (ID должен существовать в teacher_positions)
        "class_id": 1,     # Привязка к классу (ID должен существовать в classes)
        "subject_id": 2    # Привязка к предмету (ID должен существовать в subjects)
    }
    response = requests.patch(f"{BASE_URL}/api/admin/teacher/{teacher_id}", json=payload, headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_delete_teacher(teacher_id):
    print(f"\nТестирование DELETE (удаление учителя {teacher_id})...")
    response = requests.delete(f"{BASE_URL}/api/admin/teacher/{teacher_id}", headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_all_teachers_api():
    print("\nТестирование GET /api/admin/teachers...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/teachers", headers=HEADERS)
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

# Добавьте вызов в if __name__ == "__main__":
if __name__ == "__main__":
    teacher_id = test_post_teacher()
    if teacher_id:
        test_get_teacher(teacher_id)
        test_patch_teacher(teacher_id)
        test_delete_teacher(teacher_id)
    else:
        print("Тесты прерваны из-за ошибки в POST.")
    test_all_teachers_api()
