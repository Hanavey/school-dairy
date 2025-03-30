"""Тестирование api учеников (admin)"""


import requests
import json

BASE_URL = "http://127.0.0.1:5000"
API_KEY = "f3caa8cb-57dc-4c16-9726-7e58818a625a"  # Используем ключ из логов
HEADERS = {"X-API-Key": API_KEY}

def test_post_student():
    print("Тестирование POST (создание студента)...")
    payload = {
        "username": "test_student",
        "password": "test123",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+1234567890",
        "class_id": "1",
        "birth_date": "2005-05-15",
        "address": "123 Test Street",
        "api_key": "student_api_key_123"
    }
    response = requests.post(f"{BASE_URL}/api/admin/student", json=payload, headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    if response.status_code == 201:
        return response.json()["student"]["student_id"]
    else:
        print("Ошибка при создании студента!")
        return None

def test_get_student(student_id):
    print(f"\nТестирование GET (получение студента {student_id})...")
    response = requests.get(f"{BASE_URL}/api/admin/student/{student_id}", headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_patch_student(student_id):
    print(f"\nТестирование PATCH (обновление студента {student_id})...")
    payload = {
        "first_name": "Johnny",
        "email": "johnny.doe@example.com",
        "birth_date": "2005-05-16"
    }
    response = requests.patch(f"{BASE_URL}/api/admin/student/{student_id}", json=payload, headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_delete_student(student_id):
    print(f"\nТестирование DELETE (удаление студента {student_id})...")
    response = requests.delete(f"{BASE_URL}/api/admin/student/{student_id}", headers=HEADERS)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_all_students_api():
    """
    Тестирует GET-запрос к /api/admin/students для получения списка всех студентов.
    """
    print("\nТестирование GET /api/admin/students...")
    try:
        # Отправляем GET-запрос
        response = requests.get(f"{BASE_URL}/api/admin/students", headers=HEADERS)

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


def test_students_excel():
    """
        Тестирует GET-запрос к /api/admin/students/excel для получения файла со всеми студентами.
    """
    print("\nТестирование GET /api/admin/students/excel...")
    try:
        response = requests.get('http://127.0.0.1:5000/api/admin/students/excel', headers=HEADERS)

        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            with open('file.xlsx', 'wb') as f:
                f.write(response.content)
        else:
            print(f"Ошибка: {response.json().get('message', 'Неизвестная ошибка')}")

    except requests.exceptions.ConnectionError:
        print("Ошибка: Не удалось подключиться к серверу. Убедитесь, что сервер запущен.")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


if __name__ == "__main__":
    student_id = test_post_student()
    if student_id:
        test_get_student(student_id)
        test_patch_student(student_id)
        test_delete_student(student_id)
    else:
        print("Тесты прерваны из-за ошибки в POST.")
    test_all_students_api()
    test_students_excel()
