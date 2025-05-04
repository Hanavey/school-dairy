from flask import send_file
from flask_restful import Resource, request
from decorators.authorization_admin_decorator import admin_authorization_required
from data import db_session
from data.teacher_position import TeacherPosition
from .admin_students_api import AdminAllStudentsAPI
from .admin_teachers_api import AdminAllTeachersAPI
from .admin_schedules_api import AdminAllSchedulesAPI
from .admin_subjects_api import AdminSubjectsApi
from forms.admin_schedules import ScheduleSearchForm
import pandas as pd
from io import BytesIO
import logging


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


class AdminStudentsExcelFile(Resource):
    """Класс api Excel файла студентов"""
    @admin_authorization_required('/api/admin/students/excel/<string:search_query>', 'GET')
    def get(self, username=None, search_query=''):
        logging.info(f"Generating Excel for students, search_query: '{search_query}' (type: {type(search_query)})")
        logging.info(f"Raw search_query: {repr(search_query)}")

        admin_students_api = AdminAllStudentsAPI()
        logging.info(f"Calling AdminAllStudentsAPI with search: '{search_query}'")
        response, status = admin_students_api.get(username=username, search=search_query)
        logging.info(
            f"API response status: {status}, students count: {len(response.get('students', []))} for search_query: '{search_query}'")

        if status != 200:
            logging.error(f"AdminAllStudentsAPI failed with status {status}: {response}")
            return {'description': response.get('description', 'Ошибка при получении данных студентов')}, status

        students = response.get('students', [])
        if not students:
            logging.info(f'No students found for search: {search_query}')
            df = pd.DataFrame(columns=[
                'user_id', 'student_id', 'username', 'first_name', 'last_name',
                'email', 'phone_number', 'birth_date', 'address'
            ])
            out = BytesIO()
            try:
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="No Students", index=False)
                    worksheet = writer.sheets["No Students"]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            except Exception as e:
                logging.error(f"Error generating empty Excel: {str(e)}")
                return {'description': f"Ошибка при создании пустого Excel-файла: {str(e)}"}, 500
            out.seek(0)
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="students.xlsx"
            )

        data_ = {}
        for student in students:
            try:
                class_info = student.get('class', {})
                class_name = class_info.get('class_name', 'Без класса') or 'Без класса'
                logging.info(f"Student {student.get('student_id')}: class_name={class_name}")
                if class_name not in data_:
                    data_[class_name] = []
                student_data = {
                    'user_id': student.get('user_id', ''),
                    'student_id': student.get('student_id', ''),
                    'username': student.get('username', ''),
                    'first_name': student.get('first_name', ''),
                    'last_name': student.get('last_name', ''),
                    'email': student.get('email', ''),
                    'phone_number': student.get('phone_number', ''),
                    'birth_date': student.get('birth_date', ''),
                    'address': student.get('address', '')
                }
                data_[class_name].append(student_data)
            except Exception as e:
                logging.error(f"Error processing student {student.get('student_id', 'unknown')}: {str(e)}")
                continue

        if not data_:
            logging.info(f'No class data found for search: {search_query}')
            df = pd.DataFrame(columns=[
                'user_id', 'student_id', 'username', 'first_name', 'last_name',
                'email', 'phone_number', 'birth_date', 'address'
            ])
            out = BytesIO()
            try:
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="No Students", index=False)
                    worksheet = writer.sheets["No Students"]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            except Exception as e:
                logging.error(f"Error generating empty Excel: {str(e)}")
                return {'description': f"Ошибка при создании пустого Excel-файла: {str(e)}"}, 500
            out.seek(0)
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="students.xlsx"
            )

        out = BytesIO()
        try:
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                for class_name, students_data in data_.items():
                    try:
                        safe_class_name = ''.join(c for c in str(class_name) if c.isalnum() or c in (' ', '_')).strip()
                        if not safe_class_name:
                            safe_class_name = 'Class_Unknown'
                        df = pd.DataFrame(students_data)
                        df.to_excel(writer, sheet_name=safe_class_name[:31], index=False)
                        worksheet = writer.sheets[safe_class_name[:31]]
                        for cell in worksheet["1:1"]:
                            cell.font = cell.font.copy(bold=True)
                        for col in worksheet.columns:
                            max_length = max(len(str(cell.value)) for cell in col if cell.value)
                            col_letter = col[0].column_letter
                            worksheet.column_dimensions[col_letter].width = max_length + 2
                    except Exception as e:
                        logging.error(f"Error writing Excel for class {class_name}: {str(e)}")
                        continue
            if out.tell() == 0:
                logging.error("No data written to Excel")
                return {'description': 'Ошибка: не удалось записать данные в Excel'}, 500
        except Exception as e:
            logging.error(f"Error generating Excel: {str(e)}")
            return {'description': f"Ошибка при создании Excel-файла: {str(e)}"}, 500

        out.seek(0)
        logging.info(f'Excel file generated successfully for search: {search_query}')
        return send_file(
            out,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="students.xlsx"
        )


class AdminTeachersExcelFile(Resource):
    """Класс api Excel файла учителей"""
    @admin_authorization_required('/api/admin/teachers/excel', 'GET')
    def get(self, username=None, search_query=''):
        logging.info(f"Generating Excel for teachers, search_query: '{search_query}'")
        filters = {'search': search_query} if search_query else {}

        admin_teachers_api = AdminAllTeachersAPI()
        response, status = admin_teachers_api.get(username=username, **filters)

        if status != 200:
            logging.error(f'GET /api/admin/teachers/excel - API error: {response}')
            return {'description': response.get('description', 'Ошибка при получении данных учителей')}, status

        teachers = response.get('teachers', [])
        if not teachers:
            logging.info(f'No teachers found for search: {search_query}')
            df = pd.DataFrame(columns=[
                'Teacher ID', 'User ID', 'Username', 'First Name', 'Last Name',
                'Email', 'Phone Number', 'Class Name', 'Position', 'Subjects'
            ])
            out = BytesIO()
            try:
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="No Teachers", index=False)
                    worksheet = writer.sheets["No Teachers"]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            except Exception as e:
                logging.error(f"Error generating empty Excel: {str(e)}")
                return {'description': f"Ошибка при создании пустого Excel-файла: {str(e)}"}, 500
            out.seek(0)
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="teachers.xlsx"
            )

        db_sess = db_session.create_session()
        flat_data = []
        for teacher in teachers:
            try:
                if not teacher['classes'] and not teacher['positions']:
                    flat_data.append({
                        'Teacher ID': teacher.get('teacher_id', ''),
                        'User ID': teacher.get('user_id', ''),
                        'Username': teacher.get('username', ''),
                        'First Name': teacher.get('first_name', ''),
                        'Last Name': teacher.get('last_name', ''),
                        'Email': teacher.get('email', ''),
                        'Phone Number': teacher.get('phone_number', ''),
                        'Class Name': None,
                        'Position': None,
                        'Subjects': None
                    })
                else:
                    for cls in teacher['classes'] or [{}]:
                        for pos in teacher['positions'] or [{}]:
                            subjects = pos.get('subjects', [])
                            subject_names = None
                            if subjects:
                                try:
                                    subject_names = ', '.join(
                                        subject['subject_name'] for subject in subjects if
                                        subject and subject.get('subject_name')
                                    )
                                except (TypeError, KeyError) as e:
                                    logging.warning(
                                        f"Error processing subjects for teacher {teacher.get('teacher_id')}: {str(e)}")
                                    subject_names = None
                            position_id = pos.get('position_id')
                            position_name = None
                            if position_id:
                                position_name = (db_sess.query(TeacherPosition.position_name)
                                                 .filter(TeacherPosition.position_id == position_id)
                                                 .scalar())
                            flat_data.append({
                                'Teacher ID': teacher.get('teacher_id', ''),
                                'User ID': teacher.get('user_id', ''),
                                'Username': teacher.get('username', ''),
                                'First Name': teacher.get('first_name', ''),
                                'Last Name': teacher.get('last_name', ''),
                                'Email': teacher.get('email', ''),
                                'Phone Number': teacher.get('phone_number', ''),
                                'Class Name': cls.get('class_name'),
                                'Position': position_name,
                                'Subjects': subject_names
                            })
            except Exception as e:
                logging.error(f"Error processing teacher {teacher.get('teacher_id', 'unknown')}: {str(e)}")
                continue

        db_sess.close()
        if not flat_data:
            logging.info(f'No teacher data found for search: {search_query}')
            df = pd.DataFrame(columns=[
                'Teacher ID', 'User ID', 'Username', 'First Name', 'Last Name',
                'Email', 'Phone Number', 'Class Name', 'Position', 'Subjects'
            ])
            out = BytesIO()
            try:
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="No Teachers", index=False)
                    worksheet = writer.sheets["No Teachers"]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            except Exception as e:
                logging.error(f"Error generating empty Excel: {str(e)}")
                return {'description': f"Ошибка при создании пустого Excel-файла: {str(e)}"}, 500
            out.seek(0)
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="teachers.xlsx"
            )

        df = pd.DataFrame(flat_data)
        out = BytesIO()
        try:
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Teachers", index=False)
                worksheet = writer.sheets["Teachers"]
                for cell in worksheet["1:1"]:
                    cell.font = cell.font.copy(bold=True)
                for col in worksheet.columns:
                    max_length = max(len(str(cell.value)) for cell in col if cell.value)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = max_length + 2
            if out.tell() == 0:
                logging.error("No data written to Excel")
                return {'description': 'Ошибка: не удалось записать данные в Excel'}, 500
        except Exception as e:
            logging.error(f"Error generating Excel: {str(e)}")
            return {'description': f"Ошибка при создании Excel-файла: {str(e)}"}, 500

        out.seek(0)
        logging.info(f'Excel file generated successfully for search: {search_query}')
        return send_file(
            out,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="teachers.xlsx"
        )


class AdminScheduleExcelFile(Resource):
    """Класс api Excel файла расписания"""
    @admin_authorization_required('/api/admin/schedules/excel', 'GET')
    def get(self, username=None):
        form = ScheduleSearchForm(request.args)
        filters = {}
        if form.validate():
            if form.teacher.data:
                filters['teacher'] = form.teacher.data.strip()
            if form.class_name.data:
                filters['class'] = form.class_name.data.strip()
            if form.subject.data:
                filters['subject'] = form.subject.data.strip()
            if form.time.data:
                filters['time'] = form.time.data.strip()
            if form.day.data:
                filters['day'] = form.day.data.strip()
        else:
            if request.args.get('teacher'):
                filters['teacher'] = request.args.get('teacher').strip()
            if request.args.get('class_name'):
                filters['class'] = request.args.get('class_name').strip()
            if request.args.get('subject'):
                filters['subject'] = request.args.get('subject').strip()
            if request.args.get('time'):
                filters['time'] = request.args.get('time').strip()
            if request.args.get('day'):
                filters['day'] = request.args.get('day').strip()

        admin_schedules_api = AdminAllSchedulesAPI()
        response, status = admin_schedules_api.get(username=username, **filters)

        if status != 200 or not response.get('schedules'):
            logging.info(f'GET /api/admin/schedules/excel - No schedules found by {username}')
            df = pd.DataFrame(columns=[
                'schedule_id', 'class_name', 'subject_name', 'teacher_name',
                'day_of_week', 'start_time', 'end_time'
            ])
            out = BytesIO()
            try:
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="No Schedules", index=False)
                    worksheet = writer.sheets["No Schedules"]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            except Exception as e:
                logging.error(f"Error generating empty Excel: {str(e)}")
                return {'description': f"Ошибка при создании пустого Excel-файла: {str(e)}"}, 500
            out.seek(0)
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="schedules.xlsx"
            )

        schedules = response['schedules']
        data_ = {}
        for schedule in schedules:
            class_name = schedule['class']['class_name']
            if not class_name:
                continue
            if class_name not in data_:
                data_[class_name] = []

            schedule_data = {
                'schedule_id': schedule['schedule_id'],
                'class_name': class_name,
                'subject_name': schedule['subject']['subject_name'],
                'teacher_name': f"{schedule['teacher']['first_name']} {schedule['teacher']['last_name']}",
                'day_of_week': schedule['day_of_week'],
                'start_time': schedule['start_time'],
                'end_time': schedule['end_time']
            }
            data_[class_name].append(schedule_data)

        if not data_:
            logging.info(f'GET /api/admin/schedules/excel - No data found by {username}')
            df = pd.DataFrame(columns=[
                'schedule_id', 'class_name', 'subject_name', 'teacher_name',
                'day_of_week', 'start_time', 'end_time'
            ])
            out = BytesIO()
            try:
                with pd.ExcelWriter(out, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="No Schedules", index=False)
                    worksheet = writer.sheets["No Schedules"]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            except Exception as e:
                logging.error(f"Error generating empty Excel: {str(e)}")
                return {'description': f"Ошибка при создании пустого Excel-файла: {str(e)}"}, 500
            out.seek(0)
            return send_file(
                out,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="schedules.xlsx"
            )

        out = BytesIO()
        try:
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                for class_name, schedule_data in data_.items():
                    safe_class_name = ''.join(c for c in str(class_name) if c.isalnum() or c in (' ', '_')).strip()
                    if not safe_class_name:
                        safe_class_name = 'Class_Unknown'
                    df = pd.DataFrame(schedule_data)
                    df.to_excel(writer, sheet_name=safe_class_name[:31], index=False)
                    worksheet = writer.sheets[safe_class_name[:31]]
                    for cell in worksheet["1:1"]:
                        cell.font = cell.font.copy(bold=True)
                    for col in worksheet.columns:
                        max_length = max(len(str(cell.value)) for cell in col if cell.value)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max_length + 2
            if out.tell() == 0:
                logging.error("No data written to Excel")
                return {'description': 'Ошибка: не удалось записать данные в Excel'}, 500
        except Exception as e:
            logging.error(f"Error generating Excel: {str(e)}")
            return {'description': f"Ошибка при создании Excel-файла: {str(e)}"}, 500

        out.seek(0)
        logging.info(f'Excel file generated successfully for schedules')
        return send_file(
            out,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="schedules.xlsx"
        )


class AdminSubjectsExcelFile(Resource):
    """Класс api Excel файла предметов"""
    @admin_authorization_required('/api/admin/subjects/excel', 'GET')
    def get(self, username=None):
        admin_subjects_api = AdminSubjectsApi()
        response, status = admin_subjects_api.get(username=username)

        if status != 200 or not response.get('subjects'):
            logging.error(f'GET /api/admin/subjects/excel - No subjects found by {username}')
            return {'description': 'Предметы не найдены'}, 404

        subjects = response['subjects']
        data = [
            {
                'Subject ID': subject['subject_id'],
                'Subject Name': subject['subject_name']
            }
            for subject in subjects
        ]

        if not data:
            logging.error(f'GET /api/admin/subjects/excel - No subject data found by {username}')
            return {'description': 'Данные о предметах не найдены'}, 404

        df = pd.DataFrame(data)
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Subjects", index=False)
            worksheet = writer.sheets["Subjects"]
            for cell in worksheet["1:1"]:
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
            download_name="subjects.xlsx"
        )
