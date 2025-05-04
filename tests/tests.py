import requests
import json
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


BASE_URL = "http://127.0.0.1:5000"
valid_api_key = "f3caa8cb-57dc-4c16-9726-7e58818a625a"
invalid_api_key = "invalid_api_key"
headers_valid = {"X-API-Key": valid_api_key}
headers_invalid = {"X-API-Key": invalid_api_key}
headers_no_key = {}
RESULTS_DIR = "test_results"

created_resources = []


console = Console(force_terminal=True)

# Создание директории для результатов, если она не существует
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)


def save_response(response, test_name, is_excel=False):
    """Сохранение ответа API в файл."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_test_name = test_name.replace(" ", "_").replace("/", "_")

    if is_excel and response.status_code == 200:
        file_extension = 'xlsx'
    else:
        file_extension = 'json'

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
    """Вывод результата теста в консоль с использованием rich."""
    table = Table(show_header=True, expand=False)
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="green" if 200 <= status_code < 300 else "red")
    table.add_column("File", style="blue")
    table.add_row(test_name, str(status_code), filename)
    console.print(table)


def cleanup_resources():
    """Удаление всех созданных ресурсов."""
    console.print(Panel("Cleaning up created resources...", style="bold yellow", expand=False))
    for resource in created_resources:
        resource_type, resource_id, endpoint = resource
        with Progress(SpinnerColumn(), TextColumn(f"Deleting {resource_type} {resource_id}..."),
                      transient=True) as progress:
            progress.add_task(f"Deleting {resource_type}", total=1)
            response = requests.delete(f"{BASE_URL}{endpoint}/{resource_id}", headers=headers_valid)
            if response.status_code != 200:
                console.print(
                    f"[red]Failed to delete {resource_type} {resource_id}: {response.status_code} - {response.text}[/red]")
            else:
                console.print(f"[green]Deleted {resource_type} {resource_id}[/green]")
    created_resources.clear()


# Тесты для AdminAllStudentsAPI
def test_admin_all_students():
    tests = [
        ("AdminAllStudentsAPI - Valid (No Search)",
         lambda: requests.get(f"{BASE_URL}/api/admin/students", headers=headers_valid)),
        ("AdminAllStudentsAPI - Valid (Search 'В')",
         lambda: requests.get(f"{BASE_URL}/api/admin/students/В", headers=headers_valid)),
        ("AdminAllStudentsAPI - Valid (Search '10A')",
         lambda: requests.get(f"{BASE_URL}/api/admin/students/10А", headers=headers_valid)),
        ("AdminAllStudentsAPI - Invalid API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/students", headers=headers_invalid)),
        ("AdminAllStudentsAPI - No API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/students", headers=headers_no_key)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)


# Тесты для AdminOneStudentAPI
def test_admin_one_student():
    tests = [
        ("AdminOneStudentAPI - Valid (student_id=3000)",
         lambda: requests.get(f"{BASE_URL}/api/admin/student/3000", headers=headers_valid)),
        ("AdminOneStudentAPI - Invalid (Non-existent student_id=9999)",
         lambda: requests.get(f"{BASE_URL}/api/admin/student/9999", headers=headers_valid)),
        ("AdminOneStudentAPI - Invalid API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/student/3000", headers=headers_invalid)),
        ("AdminOneStudentAPI - Valid POST", lambda: requests.post(
            f"{BASE_URL}/api/admin/student",
            json={
                "username": f"newstudent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "password": "password123",
                "first_name": "New",
                "last_name": "Student",
                "email": f"newstudent_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                "phone_number": "+1234567890",
                "class_id": "1",
                "birth_date": "2005-01-01",
                "address": "123 Street"
            },
            headers=headers_valid
        )),
        ("AdminOneStudentAPI - Invalid POST (Missing Fields)", lambda: requests.post(
            f"{BASE_URL}/api/admin/student",
            json={"username": "invalidstudent", "first_name": "Invalid"},
            headers=headers_valid
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if test_name == "AdminOneStudentAPI - Valid POST" and response.status_code == 201:
                try:
                    student_id = response.json().get("student", {}).get("student_id")
                    if student_id:
                        created_resources.append(("student", student_id, "/api/admin/student"))
                except:
                    console.print(f"[yellow]Could not extract student_id from response[/yellow]")


# Тесты для AdminAllTeachersAPI
def test_admin_all_teachers():
    tests = [
        ("AdminAllTeachersAPI - Valid (No Search)",
         lambda: requests.get(f"{BASE_URL}/api/admin/teachers", headers=headers_valid)),
        ("AdminAllTeachersAPI - Valid (Search 'М')",
         lambda: requests.get(f"{BASE_URL}/api/admin/teachers/М", headers=headers_valid)),
        ("AdminAllTeachersAPI - Valid (Search 'Teacher')",
         lambda: requests.get(f"{BASE_URL}/api/admin/teachers/Teacher", headers=headers_valid)),
        ("AdminAllTeachersAPI - Invalid API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/teachers", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)


# Тесты для AdminOneTeacherAPI
def test_admin_one_teacher():
    tests = [
        ("AdminOneTeacherAPI - Valid (teacher_id=1001)",
         lambda: requests.get(f"{BASE_URL}/api/admin/teacher/1001", headers=headers_valid)),
        ("AdminOneTeacherAPI - Invalid (Non-existent teacher_id=9999)",
         lambda: requests.get(f"{BASE_URL}/api/admin/teacher/9999", headers=headers_valid)),
        ("AdminOneTeacherAPI - Valid POST", lambda: requests.post(
            f"{BASE_URL}/api/admin/teacher",
            json={
                "username": f"newteacher_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "password": "password123",
                "first_name": "New",
                "last_name": "Teacher",
                "email": f"newteacher_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                "phone_number": "+1234567890",
                "position_id": 1,
                "subject_ids": [1, 2],
                "class_id": 1
            },
            headers=headers_valid
        )),
        ("AdminOneTeacherAPI - Invalid POST (Missing Fields)", lambda: requests.post(
            f"{BASE_URL}/api/admin/teacher",
            json={"username": "invalidteacher", "first_name": "Invalid"},
            headers=headers_valid
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if test_name == "AdminOneTeacherAPI - Valid POST" and response.status_code == 201:
                try:
                    teacher_id = response.json().get("teacher", {}).get("teacher_id")
                    if teacher_id:
                        created_resources.append(("teacher", teacher_id, "/api/admin/teacher"))
                except:
                    console.print(f"[yellow]Could not extract teacher_id from response[/yellow]")


# Тесты для AdminAllSchedulesAPI
def test_admin_all_schedules():
    tests = [
        ("AdminAllSchedulesAPI - Valid (No Filters)",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules", headers=headers_valid)),
        ("AdminAllSchedulesAPI - Valid (Filter by teacher 'М')",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules?teacher=М", headers=headers_valid)),
        ("AdminAllSchedulesAPI - Valid (Filter by class '10A')",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules?class=10А", headers=headers_valid)),
        ("AdminAllSchedulesAPI - Valid (Filter by subject 'Математика')",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules?subject=Математика", headers=headers_valid)),
        ("AdminAllSchedulesAPI - Valid (Filter by day 'Понедельник')",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules?day=Понедельник", headers=headers_valid)),
        ("AdminAllSchedulesAPI - Valid (Filter by time '09:00')",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules?time=09:00", headers=headers_valid)),
        ("AdminAllSchedulesAPI - Invalid API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)


# Тесты для AdminOneScheduleAPI
def test_admin_one_schedule():
    tests = [
        ("AdminOneScheduleAPI - Valid (schedule_id=1)",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedule/1", headers=headers_valid)),
        ("AdminOneScheduleAPI - Invalid (Non-existent schedule_id=9999)",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedule/9999", headers=headers_valid)),
        ("AdminOneScheduleAPI - Valid POST", lambda: requests.post(
            f"{BASE_URL}/api/admin/schedule",
            json={
                "class_id": 1,
                "subject_id": 1,
                "teacher_id": 1002,
                "day_of_week": "Понедельник",
                "start_time": "09:00",
                "end_time": "10:00"
            },
            headers=headers_valid
        )),
        ("AdminOneScheduleAPI - Invalid POST (Invalid Time)", lambda: requests.post(
            f"{BASE_URL}/api/admin/schedule",
            json={
                "class_id": 1,
                "subject_id": 1,
                "teacher_id": 1001,
                "day_of_week": "Понедельник",
                "start_time": "invalid_time",
                "end_time": "10:00"
            },
            headers=headers_valid
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if test_name == "AdminOneScheduleAPI - Valid POST" and response.status_code == 201:
                try:
                    schedule_id = response.json().get("schedule", {}).get("schedule_id")
                    if schedule_id:
                        created_resources.append(("schedule", schedule_id, "/api/admin/schedule"))
                except:
                    console.print(f"[yellow]Could not extract schedule_id from response[/yellow]")


# Тесты для AdminSubjectsApi
def test_admin_subjects():
    tests = [
        ("AdminSubjectsApi - Valid", lambda: requests.get(f"{BASE_URL}/api/admin/subjects", headers=headers_valid)),
        ("AdminSubjectsApi - Invalid API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/subjects", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)


# Тесты для AdminSubjectApi
def test_admin_subject():
    tests = [
        ("AdminSubjectApi - Valid (subject_id=1)",
         lambda: requests.get(f"{BASE_URL}/api/admin/subject/1", headers=headers_valid)),
        ("AdminSubjectApi - Invalid (Non-existent subject_id=9999)",
         lambda: requests.get(f"{BASE_URL}/api/admin/subject/9999", headers=headers_valid)),
        ("AdminSubjectApi - Valid POST", lambda: requests.post(
            f"{BASE_URL}/api/admin/subject",
            json={"subject_name": f"New_Subject_{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
            headers=headers_valid
        )),
        ("AdminSubjectApi - Invalid POST (Missing subject_name)", lambda: requests.post(
            f"{BASE_URL}/api/admin/subject",
            json={},
            headers=headers_valid
        )),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name)
            print_test_result(test_name, response.status_code, filename)
            if test_name == "AdminSubjectApi - Valid POST" and response.status_code == 201:
                try:
                    subject_id = response.json().get("subject", {}).get("subject_id")
                    if subject_id:
                        created_resources.append(("subject", subject_id, "/api/admin/subject"))
                except:
                    console.print(f"[yellow]Could not extract subject_id from response[/yellow]")


# Тесты для Excel-файлов
def test_admin_excel_files():
    tests = [
        ("AdminStudentsExcelFile - Valid",
         lambda: requests.get(f"{BASE_URL}/api/admin/students/excel", headers=headers_valid)),
        ("AdminStudentsExcelFile - Valid (Search 'В')",
         lambda: requests.get(f"{BASE_URL}/api/admin/students/excel/В", headers=headers_valid)),
        ("AdminTeachersExcelFile - Valid",
         lambda: requests.get(f"{BASE_URL}/api/admin/teachers/excel", headers=headers_valid)),
        ("AdminTeachersExcelFile - Valid (Search 'М')",
         lambda: requests.get(f"{BASE_URL}/api/admin/teachers/excel/М", headers=headers_valid)),
        ("AdminScheduleExcelFile - Valid",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules/excel", headers=headers_valid)),
        ("AdminScheduleExcelFile - Valid (Filter by class '10А')",
         lambda: requests.get(f"{BASE_URL}/api/admin/schedules/excel?class=10А", headers=headers_valid)),
        ("AdminSubjectsExcelFile - Valid",
         lambda: requests.get(f"{BASE_URL}/api/admin/subjects/excel", headers=headers_valid)),
        ("AdminStudentsExcelFile - Invalid API Key",
         lambda: requests.get(f"{BASE_URL}/api/admin/students/excel", headers=headers_invalid)),
    ]

    for test_name, test_func in tests:
        with Progress(SpinnerColumn(), TextColumn(f"Running {test_name}...\n"), transient=True) as progress:
            progress.add_task(test_name, total=1)
            response = test_func()
            filename = save_response(response, test_name, is_excel=True)
            print_test_result(test_name, response.status_code, filename)


if __name__ == "__main__":
    try:
        console.print(Panel("Starting API Tests", style="bold green", expand=False))
        test_admin_all_students()
        test_admin_one_student()
        test_admin_all_teachers()
        test_admin_one_teacher()
        test_admin_all_schedules()
        test_admin_one_schedule()
        test_admin_subjects()
        test_admin_subject()
        test_admin_excel_files()
        console.print(Panel("All Tests Completed", style="bold green", expand=False))
    finally:
        cleanup_resources()