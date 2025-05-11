import requests
import json
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

BASE_URL = "http://127.0.0.1:5000"
valid_api_key_head_teacher = "58323e61-ce12-4418-b340-8d757073b21e"  # Ключ для завуча
valid_api_key_teacher = "1db011ad-1d3f-436c-9721-1d05584d3d4c"  # Ключ для обычного учителя
invalid_api_key = "invalid_api_key"
headers_head_teacher = {"X-API-Key": valid_api_key_head_teacher}
headers_teacher = {"X-API-Key": valid_api_key_teacher}
headers_invalid = {"X-API-Key": invalid_api_key}
headers_no_key = {}
RESULTS_DIR = "teacher_test_results"

created_resources = []
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

def cleanup_resources():
    """Удаление всех созданных ресурсов (только с правами завуча)."""
    console.print(Panel("Cleaning up created resources...", style="bold yellow", expand=False))
    for resource in created_resources:
        resource_type, resource_id, endpoint = resource
        with Progress(SpinnerColumn(), TextColumn(f"Deleting {resource_type} {resource_id}..."), transient=True) as progress:
            progress.add_task(f"Deleting {resource_type}", total=1)
            response = requests.delete(f"{BASE_URL}{endpoint}/{resource_id}", headers=headers_head_teacher)
            if response.status_code != 200:
                console.print(f"[red]Failed to delete {resource_type} {resource_id}: {response.status_code} - {response.text}[/red]")
            else:
                console.print(f"[green]Deleted {resource_type} {resource_id}[/green]")
    created_resources.clear()

# Тесты для TeacherClassesAPI
def test_teacher_classes():
    tests = [
        # Тесты для завуча
        ("TeacherClassesAPI - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes", headers=headers_head_teacher)),
        ("TeacherClassesAPI - Valid POST (Head Teacher)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/classes",
            json={
                "class_name": f"NewClass_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "teacher_id": 1012,
                "students": [
                    {
                        "username": f"student_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "first_name": "Test",
                        "last_name": "Student",
                        "email": f"student_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                        "password": "password123",
                        "birth_date": "2005-01-01",
                        "phone_number": "+1234567890",
                        "address": "123 Street"
                    }
                ]
            },
            headers=headers_head_teacher
        )),
        ("TeacherClassesAPI - Valid PATCH (Head Teacher)", lambda: requests.patch(
            f"{BASE_URL}/api/teachers/classes/12",
            json={
                "students": [
                    {
                        "username": f"patchstudent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "first_name": "Patch",
                        "last_name": "Student",
                        "email": f"patchstudent_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                        "password": "password123",
                        "birth_date": "2005-01-01"
                    }
                ]
            },
            headers=headers_head_teacher
        )),
        # ("TeacherClassesAPI - Valid DELETE (Head Teacher)", lambda: requests.delete(f"{BASE_URL}/api/teachers/classes/12", headers=headers_head_teacher)),
        # Тесты для обычного учителя
        ("TeacherClassesAPI - Valid GET (Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes", headers=headers_teacher)),
        ("TeacherClassesAPI - Invalid POST (Teacher, No Permission)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/classes",
            json={
                "class_name": f"InvalidClass_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "teacher_id": 1002,
                "students": []
            },
            headers=headers_teacher
        )),
        ("TeacherClassesAPI - Invalid PATCH (Teacher, No Permission)", lambda: requests.patch(
            f"{BASE_URL}/api/teachers/classes/1",
            json={
                "students": [
                    {
                        "username": f"patchstudent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "first_name": "Patch",
                        "last_name": "Student",
                        "email": f"patchstudent_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                        "password": "password123",
                        "birth_date": "2005-01-01"
                    }
                ]
            },
            headers=headers_teacher
        )),
        ("TeacherClassesAPI - Invalid DELETE (Teacher, No Permission)", lambda: requests.delete(f"{BASE_URL}/api/teachers/classes/1", headers=headers_teacher)),
        # Общие тесты
        ("TeacherClassesAPI - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes", headers=headers_invalid)),
        ("TeacherClassesAPI - No API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes", headers=headers_no_key)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if "POST" in test_name and response.status_code == 201:
                try:
                    class_id = response.json().get("data", {}).get("class_id")
                    if class_id:
                        created_resources.append(("class", class_id, "/api/teachers/classes"))
                except:
                    console.print(f"[yellow]Could not extract class_id from response[/yellow]")

# Тесты для TeacherListAPI
def test_teacher_list():
    tests = [
        ("TeacherListAPI - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/free-teachers", headers=headers_head_teacher)),
        ("TeacherListAPI - Invalid GET (Teacher, No Permission)", lambda: requests.get(f"{BASE_URL}/api/teachers/free-teachers", headers=headers_teacher)),
        ("TeacherListAPI - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/free-teachers", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для ClassTeacherResource
def test_class_teacher():
    tests = [
        ("ClassTeacherResource - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/my-class", headers=headers_head_teacher)),
        ("ClassTeacherResource - Valid GET (Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/my-class", headers=headers_teacher)),
        ("ClassTeacherResource - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/my-class", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для GradeResource
def test_grades():
    tests = [
        ("GradeResource - Valid GET (Head Teacher, class_id=2)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/2/grades", headers=headers_head_teacher)),
        ("GradeResource - Valid GET (Teacher, class_id=2)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/2/grades", headers=headers_teacher)),
        ("GradeResource - Invalid GET (Non-existent class_id=9999)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/9999/grades", headers=headers_teacher)),
        ("GradeResource - Valid POST (Teacher)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/grades",
            json={
                "student_id": 15,
                "subject_id": 1,
                "grade": 5,
                "date": "2025-05-12"
            },
            headers=headers_teacher
        )),
        ("GradeResource - Invalid POST (Invalid Grade)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/grades",
            json={
                "student_id": 15,
                "subject_id": 1,
                "grade": 6,
                "date": "2025-05-12"
            },
            headers=headers_teacher
        )),
        ("GradeResource - Valid PUT (Teacher)", lambda: requests.put(
            f"{BASE_URL}/api/teachers/grades",
            json={
                "grade_id": 1,
                "student_id": 15,
                "subject_id": 1,
                "grade": 4,
                "date": "2025-05-12"
            },
            headers=headers_teacher
        )),
        ("GradeResource - Valid DELETE (Teacher)", lambda: requests.delete(f"{BASE_URL}/api/teachers/grades/1", headers=headers_teacher)),
        ("GradeResource - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/grades", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if "POST" in test_name and response.status_code == 201:
                try:
                    grade_id = response.json().get("data", {}).get("grade_id")
                    if grade_id:
                        created_resources.append(("grade", grade_id, "/api/teachers/grades"))
                except:
                    console.print(f"[yellow]Could not extract grade_id from response[/yellow]")

# Тесты для HomeworkResource
def test_homework():
    tests = [
        ("HomeworkResource - Valid GET (Head Teacher, class_id=2)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/2/homework", headers=headers_head_teacher)),
        ("HomeworkResource - Valid GET (Teacher, class_id=2)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/2/homework", headers=headers_teacher)),
        ("HomeworkResource - Invalid GET (Non-existent class_id=9999)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/9999/homework", headers=headers_teacher)),
        ("HomeworkResource - Valid POST (Teacher)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/homework",
            json={
                "subject_id": 1,
                "class_id": 2,
                "task": "Solve problems 1-5",
                "due_date": "2025-05-15"
            },
            headers=headers_teacher
        )),
        ("HomeworkResource - Invalid POST (Missing Fields)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/homework",
            json={"subject_id": 1, "class_id": 1},
            headers=headers_teacher
        )),
        ("HomeworkResource - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/homework", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if "POST" in test_name and response.status_code == 201:
                try:
                    homework_id = response.json().get("data", {}).get("homework_id")
                    if homework_id:
                        created_resources.append(("homework", homework_id, "/api/teachers/homework"))
                except:
                    console.print(f"[yellow]Could not extract homework_id from response[/yellow]")

# Тесты для AttendanceResource
def test_attendance():
    tests = [
        ("AttendanceResource - Valid GET (Head Teacher, class_id=2)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/2/attendance", headers=headers_head_teacher)),
        ("AttendanceResource - Valid GET (Teacher, class_id=2)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/2/attendance", headers=headers_teacher)),
        ("AttendanceResource - Invalid GET (Non-existent class_id=9999)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/9999/attendance", headers=headers_teacher)),
        ("AttendanceResource - Valid POST (Teacher)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/attendance",
            json={
                "student_id": 15,
                "date": "2025-05-11",
                "status": "присутствовал"
            },
            headers=headers_teacher
        )),
        ("AttendanceResource - Invalid POST (Invalid Status)", lambda: requests.post(
            f"{BASE_URL}/api/teachers/attendance",
            json={
                "student_id": 15,
                "date": "2025-05-11",
                "status": "invalid"
            },
            headers=headers_teacher
        )),
        ("AttendanceResource - Valid PUT (Teacher)", lambda: requests.put(
            f"{BASE_URL}/api/teachers/attendance",
            json={
                "attendance_id": 1,
                "student_id": 15,
                "date": "2025-05-11",
                "status": "отсутствовал"
            },
            headers=headers_teacher
        )),
        ("AttendanceResource - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/attendance", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if "POST" in test_name and response.status_code == 201:
                try:
                    attendance_id = response.json().get("data", {}).get("attendance_id")
                    if attendance_id:
                        created_resources.append(("attendance", attendance_id, "/api/teachers/attendance"))
                except:
                    console.print(f"[yellow]Could not extract attendance_id from response[/yellow]")

# Тесты для TeacherScheduleResource
def test_teacher_schedule():
    tests = [
        ("TeacherScheduleResource - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/schedule", headers=headers_head_teacher)),
        ("TeacherScheduleResource - Valid GET (Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/schedule", headers=headers_teacher)),
        ("TeacherScheduleResource - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/schedule", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для TeacherSubjectsAPI
def test_teacher_subjects():
    tests = [
        ("TeacherSubjectsAPI - Valid GET (Head Teacher, class_id=1)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/subjects", headers=headers_head_teacher)),
        ("TeacherSubjectsAPI - Valid GET (Teacher, class_id=1)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/subjects", headers=headers_teacher)),
        ("TeacherSubjectsAPI - Invalid GET (Non-existent class_id=9999)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/9999/subjects", headers=headers_teacher)),
        ("TeacherSubjectsAPI - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/subjects", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)

# Тесты для Excel-файлов
def test_teacher_excel_files():
    tests = [
        ("ClassExcelReportResource - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/1/excel", headers=headers_head_teacher)),
        ("ClassExcelReportResource - Valid GET (Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/1/excel", headers=headers_teacher)),
        ("ClassExcelReportResource - Invalid GET (Non-existent IDs)", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/9999/9999/excel", headers=headers_teacher)),
        ("ClassFullReportResource - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/my-class/excel", headers=headers_head_teacher)),
        ("ClassFullReportResource - Valid GET (Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/my-class/excel", headers=headers_teacher)),
        ("TeacherScheduleExcelResource - Valid GET (Head Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/schedule/excel", headers=headers_head_teacher)),
        ("TeacherScheduleExcelResource - Valid GET (Teacher)", lambda: requests.get(f"{BASE_URL}/api/teachers/schedule/excel", headers=headers_teacher)),
        ("ClassExcelReportResource - Invalid API Key", lambda: requests.get(f"{BASE_URL}/api/teachers/classes/1/1/excel", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name, is_excel=True)
            print_test_result(test_name, response.status_code, filename)

if __name__ == "__main__":
    try:
        console.print(Panel("Starting Teacher API Tests", style="bold green", expand=False))
        test_teacher_classes()
        test_teacher_list()
        test_class_teacher()
        test_grades()
        test_homework()
        test_attendance()
        test_teacher_schedule()
        test_teacher_subjects()
        test_teacher_excel_files()
        console.print(Panel("All Teacher Tests Completed", style="bold green", expand=False))
    finally:
        cleanup_resources()