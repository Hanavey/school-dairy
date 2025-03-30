from flask import send_file
from sqlalchemy.orm import joinedload
from sqlalchemy.testing.plugin.plugin_base import logging
from decorators.authorization_admin_decorator import admin_authorization_required
from flask_restful import Resource, abort
from data import db_session
from data.classes import Class
from data.student import Student
from data.teacher import Teacher
from data.teacher_position import TeacherPosition
from data.subject import Subject
from data.schedule import Schedule
import pandas as pd
from io import BytesIO
import logging


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


class AdminStudentsExcelFile(Resource):
    @admin_authorization_required('/api/admin/students/excel', 'GET')
    def get(self, username=None):
        db_sess = db_session.create_session()
        try:
            classes = db_sess.query(Class).all()
            if not classes:
                logging.error(f'GET /api/admin/students/excel - classes not found by {username}')
                abort(404, description='classes not found')
            data_ = []
            for class_ in classes:
                class_id, class_name = class_.class_id, class_.class_name
                students = (db_sess.query(Student)
                            .options(joinedload(Student.user))
                            .filter(Student.class_id == class_id)
                            .all())
                students_data = []
                for student in students:
                    student_data = {
                        'user_id': student.user_id,
                        'student_id': student.student_id,
                        'username': student.user.username if student.user else None,
                        'first_name': student.user.first_name if student.user else None,
                        'last_name': student.user.last_name if student.user else None,
                        'email': student.user.email if student.user else None,
                        'phone_number': student.user.phone_number if student.user else None,
                        'birth_date': student.birth_date.strftime('%Y-%m-%d') if student.birth_date else None,
                        'address': student.address
                    }
                    students_data.append(student_data)
                data_.append({class_name: students_data})

            if not data_:
                logging.error(f'GET /api/admin/students/excel - data not found by {username}')
                abort(404, description='data not found')

            out = BytesIO()

            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                for class_dict in data_:
                    # Получаем имя класса и список студентов
                    class_name = list(class_dict.keys())[0]
                    students_data = class_dict[class_name]

                    # Преобразуем список студентов в DataFrame
                    df = pd.DataFrame(students_data)

                    # Записываем DataFrame на отдельный лист с именем class_name
                    df.to_excel(writer, sheet_name=str(class_name), index=False)

                    worksheet = writer.sheets[str(class_name)]
                    for cell in worksheet["1:1"]:  # Первая строка (заголовки)
                        cell.font = cell.font.copy(bold=True)

                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2

            out.seek(0)

            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="students.xlsx"
            )

        finally:
            db_sess.close()


class AdminTeachersExcelFile(Resource):
    @admin_authorization_required('/api/admin/teachers/excel', 'GET')
    def get(self, username=None):
        db_sess = db_session.create_session()
        try:
            # Запрос учителей с жадной загрузкой связанных данных
            teachers = (db_sess.query(Teacher)
                        .options(joinedload(Teacher.user))
                        .options(joinedload(Teacher.classes))
                        .options(joinedload(Teacher.schedules))
                        .options(joinedload(Teacher.positions))
                        .all())

            # Проверка на наличие данных
            if not teachers:
                logging.error(f'GET /api/admin/teacher/excel - teachers not found by {username}')
                return {
                    'message': 'Список учителей пуст.',
                    'teachers': []
                }, 200

            # Формируем данные
            data_ = []
            for teacher in teachers:
                classes = [
                    {'class_id': cls.class_id, 'class_name': cls.class_name}
                    for cls in teacher.classes
                ]
                positions = [
                    {
                        'position_id': pos.position_id,
                        'class_id': pos.class_id,
                        'subject_id': pos.subject_id
                    }
                    for pos in teacher.positions
                ]

                teacher_data = {
                    'teacher_id': teacher.teacher_id,
                    'user_id': teacher.user_id,
                    'username': teacher.user.username if teacher.user else None,
                    'first_name': teacher.user.first_name if teacher.user else None,
                    'last_name': teacher.user.last_name if teacher.user else None,
                    'email': teacher.user.email if teacher.user else None,
                    'phone_number': teacher.user.phone_number if teacher.user else None,
                    'classes': classes,
                    'positions': positions
                }
                data_.append(teacher_data)

            # Разворачиваем данные в плоский список для удобного заполнения
            flat_data = []
            for teacher in data_:
                # Если нет классов или позиций, добавляем запись с пустыми значениями
                if not teacher['classes'] and not teacher['positions']:
                    flat_data.append({
                        'Teacher ID': teacher['teacher_id'],
                        'User ID': teacher['user_id'],
                        'Username': teacher['username'],
                        'First Name': teacher['first_name'],
                        'Last Name': teacher['last_name'],
                        'Email': teacher['email'],
                        'Phone Number': teacher['phone_number'],
                        'Class ID': None,
                        'Class Name': None,
                        'Position ID': None,
                        'Position Class ID': None,
                        'Subject ID': None
                    })
                else:
                    # Создаем строки для всех комбинаций классов и позиций
                    for cls in teacher['classes'] or [{}]:
                        for pos in teacher['positions'] or [{}]:
                            flat_data.append({
                                'Teacher ID': teacher['teacher_id'],
                                'User ID': teacher['user_id'],
                                'Username': teacher['username'],
                                'First Name': teacher['first_name'],
                                'Last Name': teacher['last_name'],
                                'Email': teacher['email'],
                                'Phone Number': teacher['phone_number'],
                                'Class Name': cls.get('class_name'),
                                'Position': (db_sess.query(TeacherPosition.position_name)
                                             .filter(TeacherPosition.position_id == pos.get('position_id'))
                                             .scalar()),
                                'Subject': (db_sess.query(Subject.subject_name)
                                            .filter(Subject.subject_id == pos.get('subject_id'))
                                            .scalar())
                            })

            # Преобразуем в DataFrame с понятными названиями столбцов
            df = pd.DataFrame(flat_data)

            # Создаем Excel-файл в памяти
            out = BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Teachers", index=False)

                # Форматирование для удобства
                worksheet = writer.sheets["Teachers"]
                for cell in worksheet["1:1"]:  # Жирные заголовки
                    cell.font = cell.font.copy(bold=True)
                for col in worksheet.columns:
                    max_length = max(len(str(cell.value)) for cell in col if cell.value)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = max_length + 2

            # Перемещаем указатель в начало
            out.seek(0)

            # Отправляем файл клиенту
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="teachers.xlsx"
            )

        finally:
            db_sess.close()


class AdminScheduleExcelFile(Resource):
    @admin_authorization_required('/api/admin/schedules/excel', 'GET')
    def get(self, username=None):
        db_sess = db_session.create_session()
        try:
            classes = db_sess.query(Class).all()
            if not classes:
                logging.error(f'GET /api/admin/schedules/excel - classes not found by {username}')
                abort(404, description='classes not found')
            data_ = []
            for class_ in classes:
                class_id, class_name = class_.class_id, class_.class_name
                schedules_class = (db_sess.query(Schedule)
                         .options(joinedload(Schedule.subject))
                         .options(joinedload(Schedule.teacher).joinedload(Teacher.user))
                         .filter(Schedule.class_id == class_id)
                         .all())
                schedules_data = []
                for schedule in schedules_class:
                    schedule_data = {
                        'schedule_id': schedule.schedule_id,
                        'subject_name': schedule.subject.subject_name,
                        'first_name': schedule.teacher.user.first_name if schedule.teacher.user else None,
                        'last_name': schedule.teacher.user.last_name if schedule.teacher.user else None,
                        'day_of_week': schedule.day_of_week,
                        'start_time': schedule.start_time,
                        'end_time': schedule.end_time
                    }
                    schedules_data.append(schedule_data)
                data_.append({class_name: schedules_data})

            if not data_:
                logging.error(f'GET /api/admin/schedules/excel - data not found by {username}')
                abort(404, description='data not found')

            out = BytesIO()

            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                for class_dict in data_:
                    # Получаем имя класса и список расписания
                    class_name = list(class_dict.keys())[0]
                    students_data = class_dict[class_name]

                    # Преобразуем список расписания в DataFrame
                    df = pd.DataFrame(students_data)

                    # Записываем DataFrame на отдельный лист с именем class_name
                    df.to_excel(writer, sheet_name=str(class_name), index=False)

                    worksheet = writer.sheets[str(class_name)]
                    for cell in worksheet["1:1"]:  # Первая строка (заголовки)
                        cell.font = cell.font.copy(bold=True)

                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2

            out.seek(0)

            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="schedules.xlsx"
            )

        finally:
            db_sess.close()


class AdminSubjectsExcelFile(Resource):
    @admin_authorization_required('/api/admin/subjects/excel', 'GET')
    def get(self, username=None):
        db_sess = db_session.create_session()
        try:
            subjects = db_sess.query(Subject.subject_id, Subject.subject_name).all()
            if not subjects:
                logging.error(f'GET /api/admin/subjects/excel - subjects not found by {username}')
                abort(404, description='subjects not found')

            data = [
                {'Subject ID': subject.subject_id, 'Subject Name': subject.subject_name}
                for subject in subjects
            ]

            # Создаем DataFrame
            df = pd.DataFrame(data)

            # Создаем Excel-файл в памяти
            out = BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Subjects", index=False)

                # Форматирование для удобства
                worksheet = writer.sheets["Subjects"]
                for cell in worksheet["1:1"]:  # Жирные заголовки
                    cell.font = cell.font.copy(bold=True)
                for col in worksheet.columns:
                    max_length = max(len(str(cell.value)) for cell in col if cell.value)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = max_length + 2

            # Перемещаем указатель в начало
            out.seek(0)

            # Отправляем файл клиенту
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="subjects.xlsx"
            )

        finally:
            db_sess.close()
