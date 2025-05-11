import requests
import json
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

BASE_URL = "http://127.0.0.1:5000"
valid_api_key_student = "db1586ba-11c1-4acf-9665-85d0e47d4d88"  # Ключ для студента (предполагаемый)
invalid_api_key = "invalid_api_key"
headers_student = {"X-API-Key": valid_api_key_student}
headers_invalid = {"X-API-Key": invalid_api_key}
headers_no_key = {}
RESULTS_DIR = "student_test_results"


console = Console(force_terminal=True)

# Создание директории для результатов
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

def save_response(response, test_name, is_excel=False):
    """Сохранение ответа API в файл."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_test_name = test_name.replace(" ", "_").replace("/", "_")
    file_extension = 'xlsx' if is_excel and response.status_code == 200 else 'json'
    filename = f"{RESULTS_DIR}/{safe_test_name}_{timestamp}.{file_extension}"

    if file_extension == 'xlsx':
        with open(filename, "wb") as f:
            f.write(response.content)
    else:
        try:
            data = response.json()
        except:
            data = {"text": response.text}
        data["status_code"] = response.status_code
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    return filename

def print_test_result(test_name, status_code, filename):
    """Вывод результата теста в консоль."""
    table = Table(show_header=True, expand=False)
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="green" if 200 <= status_code < 300 else "red")
    table.add_column("File", style="blue")
    table.add_row(test_name, str(status_code), filename)
    console.print(table)

# Тесты для ClassmatesResource
def test_classmates():
    tests = [
        ("ClassmatesResource - Valid GET (Student)", lambda: requests.get(
            f"{BASE_URL}/api/student/classmates",
            headers=headers_student
        )),
        ("ClassmatesResource - Invalid API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/classmates",
            headers=headers_invalid
        )),
        ("ClassmatesResource - No API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/classmates",
            headers=headers_no_key
        ))
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для StudentScheduleResource
def test_student_schedule():
    tests = [
        ("StudentScheduleResource - Valid GET (Student)", lambda: requests.get(
            f"{BASE_URL}/api/student/schedule",
            headers=headers_student
        )),
        ("StudentScheduleResource - Invalid API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/schedule",
            headers=headers_invalid
        )),
        ("StudentScheduleResource - No API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/schedule",
            headers=headers_no_key
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для StudentGradesAttendanceResource
def test_grades_attendance():
    tests = [
        ("StudentGradesAttendanceResource - Valid GET (Student, subject_id=1)", lambda: requests.get(
            f"{BASE_URL}/api/student/grades_attendance/1",
            headers=headers_student
        )),
        ("StudentGradesAttendanceResource - Invalid GET (Non-existent subject_id=9999)", lambda: requests.get(
            f"{BASE_URL}/api/student/grades_attendance/9999",
            headers=headers_student
        )),
        ("StudentGradesAttendanceResource - Invalid API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/grades_attendance/1",
            headers=headers_invalid
        )),
        ("StudentGradesAttendanceResource - No API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/grades_attendance/1",
            headers=headers_no_key
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для StudentHomeworkResource
def test_homework():
    tests = [
        ("StudentHomeworkResource - Valid GET (Student)", lambda: requests.get(
            f"{BASE_URL}/api/student/homework",
            headers=headers_student
        )),
        ("StudentHomeworkResource - Invalid API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/homework",
            headers=headers_invalid
        )),
        ("StudentHomeworkResource - No API Key", lambda: requests.get(
            f"{BASE_URL}/api/student/homework",
            headers=headers_no_key
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

if __name__ == "__main__":
    try:
        console.print(Panel("Starting Student API Tests", style="bold green", expand=False))
        test_classmates()
        test_student_schedule()
        test_grades_attendance()
        test_homework()
        console.print(Panel("All Student Tests Completed", style="bold green", expand=False))
    except Exception as e:
        console.print(f"[red]Error during tests: {str(e)}[/red]")