# api/teacher/class_excel_report_api.py
from flask_restful import Resource
from flask import send_file
from data import db_session
from data.student import Student
from data.user import User
from data.subject import Subject
from data.classes import Class
from api.teacher.teacher_grades_homework_attendance_api import GradeResource, AttendanceResource
from api.teacher.class_teacher_api import ClassTeacherResource
from api.teacher.teacher_schedule_api import TeacherScheduleResource
from decorators.authorization_teacher_decorator import teacher_authorization_required
import logging
import pandas as pd
from io import BytesIO
from datetime import datetime
from openpyxl.styles import Font, Alignment

logging.basicConfig(
    filename='api_access.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


# Существующий ClassExcelReportResource (оставлен без изменений для примера)
class ClassExcelReportResource(Resource):
    @teacher_authorization_required('/api/teacher/<int:class_id>/<int:subject_id>/excel', method='GET')
    def get(self, username, position_name, class_id=None, subject_id=None):
        logging.debug(
            f"Starting ClassExcelReportResource.get for user={username}, class_id={class_id}, subject_id={subject_id}")
        if not class_id or not subject_id:
            logging.error(f"GET /api/class_excel_report - Missing class_id or subject_id for user {username}")
            return {"status": "error", "description": "Не указаны class_id или subject_id"}, 400

        db_sess = db_session.create_session()
        try:
            class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
            if not class_:
                logging.error(f"GET /api/class_excel_report - Class {class_id} not found for user {username}")
                return {"status": "error", "description": "Класс не найден"}, 404

            subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
            if not subject:
                logging.error(f"GET /api/class_excel_report - Subject {subject_id} not found for user {username}")
                return {"status": "error", "description": "Предмет не найден"}, 404

            grade_resource = GradeResource()
            logging.debug(f"Fetching grades for class_id={class_id}")
            grades_response, grades_status = grade_resource.get(class_id=class_id)
            if grades_status != 200:
                logging.error(f"GET /api/class_excel_report - Failed to get grades: {grades_response['description']}")
                return grades_response, grades_status
            grades_data = [g for g in grades_response['data'] if g['subject_id'] == subject_id]
            logging.debug(f"Filtered grades: {len(grades_data)} entries for subject_id={subject_id}")
            logging.debug(f"Grades data sample: {grades_data[:2] if grades_data else 'No grades'}")

            attendance_resource = AttendanceResource()
            logging.debug(f"Fetching attendance for class_id={class_id}")
            attendance_response, attendance_status = attendance_resource.get(class_id=class_id)
            if attendance_status != 200:
                logging.error(
                    f"GET /api/class_excel_report - Failed to get attendance: {attendance_response['description']}")
                return attendance_response, attendance_status
            attendance_data = attendance_response['data']
            logging.debug(f"Attendance data: {len(attendance_data)} entries")

            students = db_sess.query(Student).join(User).filter(Student.class_id == class_id).all()
            if not students:
                logging.error(
                    f"GET /api/class_excel_report - No students found in class {class_id} for user {username}")
                return {"status": "error", "description": "В классе нет учеников"}, 404
            logging.debug(f"Found {len(students)} students in class {class_id}")

            data = []
            for student in students:
                full_name = f"{student.user.first_name} {student.user.last_name}"
                student_grades = [g for g in grades_data if g['student_id'] == student.user_id]
                student_attendance = [a for a in attendance_data if a['student_id'] == student.user_id]

                grades_str = "; ".join([str(g['grade']) for g in student_grades]) or "Нет оценок"
                attendance_str = "; ".join([f"{a['date']}: {a['status']}" for a in student_attendance]) or "Нет записей"

                logging.debug(
                    f"Student {full_name}: grades={[{k: v for k, v in g.items()} for g in student_grades]}, grades_str={grades_str}")

                data.append({
                    "ФИО ученика": full_name,
                    "Оценки": grades_str,
                    "Посещаемость": attendance_str
                })

            logging.debug("Creating DataFrame")
            df = pd.DataFrame(data)

            logging.debug("Generating Excel file")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=f"{class_.class_name}_{subject.subject_name}", index=False)
                workbook = writer.book
                worksheet = writer.sheets[f"{class_.class_name}_{subject.subject_name}"]
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                worksheet.column_dimensions['A'].width = 30
                worksheet.column_dimensions['B'].width = 40
                worksheet.column_dimensions['C'].width = 50

            output.seek(0)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{class_.class_name}_{subject.subject_name}_{timestamp}.xlsx"

            logging.info(
                f"GET /api/class_excel_report - Excel report generated for class {class_id}, subject {subject_id} by {username}")
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            logging.error(f"GET /api/class_excel_report - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()


# Новый ресурс для полного отчета по классу
class ClassFullReportResource(Resource):
    """API для генерации Excel-файла с полной информацией о классе классного руководителя."""

    @teacher_authorization_required('/api/teacher/my_class/excel', method='GET')
    def get(self, username, position_name):
        """Генерация Excel-файла с четырьмя листами: расписание, оценки, посещаемость, информация об учениках."""
        logging.debug(f"Starting ClassFullReportResource.get for user={username}")

        try:
            class_teacher_resource = ClassTeacherResource()
            response, status = class_teacher_resource.get(position_name=position_name)
            if status != 200:
                logging.error(f"GET /api/my_class_full_report - Failed to get class data: {response['description']}")
                return response, status

            class_data = response['data']
            students_data = class_data['students']
            schedule_data = class_data['schedule']
            class_name = class_data['class_name']
            logging.debug(
                f"Class data retrieved: class_id={class_data['class_id']}, students={len(students_data)}, schedule={len(schedule_data)}")

            schedule_df_data = [
                {
                    "День недели": s['day_of_week'],
                    "Время": f"{s['start_time']}-{s['end_time']}" if s['start_time'] and s['end_time'] else "Не указано",
                    "Предмет": s['subject_name'],
                    "Учитель": s['teacher_name']
                }
                for s in schedule_data
            ]
            schedule_df = pd.DataFrame(schedule_df_data)
            logging.debug(f"Schedule data: {len(schedule_df_data)} entries")

            subjects = set()
            for student in students_data:
                for grade in student['grades']:
                    subjects.add(grade['subject_name'])
            subjects = sorted(subjects)  # Сортируем для единообразия
            logging.debug(f"Unique subjects: {subjects}")

            # Формируем данные для таблицы оценок
            grades_df_data = []
            for student in students_data:
                full_name = f"{student['first_name']} {student['last_name']}"
                student_row = {"ФИО ученика": full_name}
                # Инициализируем пустые значения для каждого предмета
                for subject in subjects:
                    student_row[subject] = ""
                # Заполняем оценки по предметам
                for grade in student['grades']:
                    subject_name = grade['subject_name']
                    if subject_name in student_row:
                        # Добавляем оценку в соответствующую колонку
                        if student_row[subject_name]:
                            student_row[subject_name] += f", {grade['grade']}"
                        else:
                            student_row[subject_name] = str(grade['grade'])
                grades_df_data.append(student_row)
                logging.debug(f"Student {full_name}: grades={student_row}")
            grades_df = pd.DataFrame(grades_df_data)

            # 3. Данные для листа "Посещаемость"
            attendance_df_data = []
            for student in students_data:
                full_name = f"{student['first_name']} {student['last_name']}"
                attendance_str = "; ".join(
                    [f"{a['date']}: {a['status']}" for a in student['attendance']]) or "Нет записей"
                attendance_df_data.append({
                    "ФИО ученика": full_name,
                    "Посещаемость": attendance_str
                })
            attendance_df = pd.DataFrame(attendance_df_data)

            # 4. Данные для листа "Ученики"
            students_df_data = [
                {
                    "ФИО": f"{s['first_name']} {s['last_name']}",
                    "Дата рождения": s['birth_date'] or "Не указана",
                    "Адрес": s['address'] or "Не указан",
                    "Email": s['email'] or "Не указан",
                    "Телефон": s['phone_number'] or "Не указан"
                }
                for s in students_data
            ]
            students_df = pd.DataFrame(students_df_data)
            logging.debug(f"Students data: {len(students_df_data)} entries")

            # Создание Excel-файла с четырьмя листами
            logging.debug("Generating Excel file with multiple sheets")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Лист 1: Расписание
                schedule_df.to_excel(writer, sheet_name="Расписание", index=False)
                worksheet = writer.sheets["Расписание"]
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                worksheet.column_dimensions['A'].width = 20
                worksheet.column_dimensions['B'].width = 15
                worksheet.column_dimensions['C'].width = 25
                worksheet.column_dimensions['D'].width = 30

                # Лист 2: Оценки
                grades_df.to_excel(writer, sheet_name="Оценки", index=False)
                worksheet = writer.sheets["Оценки"]
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                worksheet.column_dimensions['A'].width = 30
                for idx, subject in enumerate(subjects, 2):  # Начинаем с колонки B
                    worksheet.column_dimensions[chr(64 + idx)].width = 20

                # Лист 3: Посещаемость
                attendance_df.to_excel(writer, sheet_name="Посещаемость", index=False)
                worksheet = writer.sheets["Посещаемость"]
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                worksheet.column_dimensions['A'].width = 30
                worksheet.column_dimensions['B'].width = 50

                # Лист 4: Ученики
                students_df.to_excel(writer, sheet_name="Ученики", index=False)
                worksheet = writer.sheets["Ученики"]
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                worksheet.column_dimensions['A'].width = 30
                worksheet.column_dimensions['B'].width = 20
                worksheet.column_dimensions['C'].width = 40
                worksheet.column_dimensions['D'].width = 30
                worksheet.column_dimensions['E'].width = 20

            output.seek(0)

            # Формирование имени файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"my_class_full_report_{class_name}_{timestamp}.xlsx"

            logging.info(f"GET /api/my_class_full_report - Excel report generated for class {class_name} by {username}")
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            logging.error(f"GET /api/my_class_full_report - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500


class TeacherScheduleExcelResource(Resource):
    """API для генерации Excel-файла с расписанием учителя."""

    @teacher_authorization_required('/api/teacher/my_schedule/excel', method='GET')
    def get(self, username, position_name):
        """Генерация Excel-файла с расписанием учителя."""
        logging.debug(f"Starting TeacherScheduleExcelResource.get for user={username}")

        try:
            # Получение данных через TeacherScheduleResource
            schedule_resource = TeacherScheduleResource()
            response, status = schedule_resource.get()
            if status != 200:
                logging.error(f"GET /api/teacher_schedule_excel - Failed to get schedule: {response['description']}")
                return response, status

            schedule_data = response['data']['schedule']
            logging.debug(f"Schedule data retrieved: {len(schedule_data)} entries")

            # Формирование данных для Excel
            excel_data = [
                {
                    "День недели": s['day_of_week'],
                    "Время": f"{s['start_time']}-{s['end_time']}" if s['start_time'] and s[
                        'end_time'] else "Не указано",
                    "Предмет": s['subject_name'],
                    "Класс": s['class_name']
                }
                for s in schedule_data
            ]
            df = pd.DataFrame(excel_data)
            logging.debug(f"Excel data prepared: {len(excel_data)} rows")

            # Создание Excel-файла
            logging.debug("Generating Excel file")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="Расписание", index=False)
                worksheet = writer.sheets["Расписание"]
                for cell in worksheet[1]:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(horizontal='center')
                worksheet.column_dimensions['A'].width = 20
                worksheet.column_dimensions['B'].width = 15
                worksheet.column_dimensions['C'].width = 25
                worksheet.column_dimensions['D'].width = 15

            output.seek(0)

            # Формирование имени файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"teacher_schedule_{username}_{timestamp}.xlsx"

            logging.info(f"GET /api/teacher_schedule_excel - Excel schedule generated for user {username}")
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            logging.error(f"GET /api/teacher_schedule_excel - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
