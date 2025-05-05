from admin import admin_bp
from data import db_session
from data.user import User
from data.admin import Admin
from flask_login import current_user, login_user, logout_user
from flask import render_template, redirect, request, url_for, flash, Response
from forms.login import LoginForm
from forms.admin_students import CreateStudentForm, EditStudentForm, StudentSearchForm
from forms.admin_teachers import CreateTeacherForm, EditTeacherForm, TeacherSearchForm
from forms.admin_schedules import CreateScheduleForm, EditScheduleForm, ScheduleSearchForm
from forms.admin_subjects import CreateSubjectForm, EditSubjectForm
from forms.user_settings import UserSettingsForm
from api.admin.admin_students_api import AdminOneStudentAPI, AdminAllStudentsAPI
from api.admin.admin_teachers_api import AdminOneTeacherAPI, AdminAllTeachersAPI
from api.admin.admin_schedules_api import AdminAllSchedulesAPI, AdminOneScheduleAPI
from api.admin.admin_subjects_api import AdminSubjectApi, AdminSubjectsApi
from api.admin.admin_excel_files import (AdminStudentsExcelFile, AdminTeachersExcelFile, AdminScheduleExcelFile,
                                         AdminSubjectsExcelFile)
from api.user_settings_api import UserSettingsAPI
from decorators.login_decorator import blueprint_login_required
import base64
import logging
from datetime import datetime


logging.basicConfig(
    filename='routes.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


@admin_bp.route('/')
def index():
    """Базовая страница Администратора"""
    return render_template('admin/index.html')


@admin_bp.route('/students', defaults={'search_query': ''}, methods=['GET', 'POST'])
@admin_bp.route('/students/<string:search_query>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def students(search_query=''):
    """Страница со списком студентов"""
    form = StudentSearchForm()

    if form.validate_on_submit():
        search_query = form.search.data.strip()
        return redirect(url_for('admin.students', search_query=search_query))

    if request.method == 'GET' and not search_query and 'search' in request.args:
        search_query = request.args.get('search', '').strip()
        if search_query:
            return redirect(url_for('admin.students', search_query=search_query))

    if search_query:
        form.search.data = search_query

    api = AdminAllStudentsAPI()
    response = api.get(search=search_query)

    if isinstance(response, tuple):
        students, status = response
        students = students.get('students', []) if isinstance(students, dict) else []
    else:
        flash('Ошибка при получении списка учеников.', 'danger')
        students = []

    return render_template(
        'admin/students_list.html',
        form=form,
        students=students,
        search_query=search_query
    )


@admin_bp.route('/students/excel', defaults={'search_query': ''}, methods=['GET'])
@admin_bp.route('/students/excel/<string:search_query>', methods=['GET'])
@blueprint_login_required('admin_bp')
def students_excel(search_query=''):
    """Скачивание Excel файла со списком всех студентов"""
    if not search_query and 'search' in request.args:
        search_query = request.args.get('search', '').strip()
        logging.info(f"Retrieved search_query from query string: '{search_query}'")
    else:
        logging.info(f"Using search_query from path: '{search_query}'")

    logging.info(f"Exporting students to Excel with search_query: '{search_query}' (raw: {repr(search_query)})")
    excel_resource = AdminStudentsExcelFile()
    response = excel_resource.get(search_query=search_query)
    logging.info(f"Excel response generated for search_query: '{search_query}'")
    return response


@admin_bp.route('/student/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_student():
    """Страница для создания нового студента"""
    form = CreateStudentForm()
    if form.validate_on_submit():
        api = AdminOneStudentAPI()
        data = {
            'username': form.username.data,
            'password': form.password.data,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
            'class_id': form.class_id.data,
            'birth_date': form.birth_date.data.strftime('%Y-%m-%d'),
            'address': form.address.data,
            'profile_picture': base64.b64encode(form.profile_picture.data.read()).decode('utf-8') if
            form.profile_picture.data else None
        }
        response = api.post(update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 201:
                logging.info(f"Student created via API by admin")
                flash('Ученик успешно создан.', 'success')
                return redirect(url_for('admin.students'))
            else:
                flash(result.get('description', 'Ошибка при создании ученика.'), 'danger')
        else:
            flash('Ошибка при создании ученика.', 'danger')
    return render_template('admin/new_student.html', form=form)


@admin_bp.route('/student/<int:student_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_student(student_id):
    """Страница для редактирования информации о студенте"""
    api = AdminOneStudentAPI()
    response = api.get(student_id=student_id)
    logging.info(f"edit_student: Response for student_id={student_id}: {response}")

    if isinstance(response, tuple):
        student_data, status = response
        if status == 200:
            student = student_data.get('Student', {})
            if not student:
                logging.warning(f"edit_student: Empty student data for student_id={student_id}")
                flash('Данные студента пусты.', 'danger')
                return redirect(url_for('admin.students'))
        else:
            logging.error(f"edit_student: API error for student_id={student_id}, status={status}, response={student_data}")
            flash(student_data.get('description', 'Ошибка при получении данных студента.'), 'danger')
            return redirect(url_for('admin.students'))
    else:
        logging.error(f"edit_student: Invalid response for student_id={student_id}: {response}")
        flash('Ошибка при получении данных студента.', 'danger')
        return redirect(url_for('admin.students'))

    if 'birth_date' in student and student['birth_date']:
        try:
            student['birth_date'] = datetime.strptime(student['birth_date'], '%Y-%m-%d').date()
        except ValueError as e:
            logging.error(f"edit_student: Invalid birth_date format for student_id={student_id}: {student['birth_date']}, error: {e}")
            flash('Ошибка: некорректный формат даты рождения.', 'danger')
            return redirect(url_for('admin.students'))

    logging.info(f"edit_student: Student data for student_id={student_id}: {student}")

    form = EditStudentForm(data=student)
    if form.validate_on_submit():
        data = {
            'username': form.username.data,
            'password': form.password.data or None,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
            'class_id': form.class_id.data,
            'birth_date': form.birth_date.data.strftime('%Y-%m-%d'),
            'address': form.address.data,
            'profile_picture': base64.b64encode(form.profile_picture.data.read()).decode('utf-8') if form.profile_picture.data else None
        }
        response = api.patch(student_id, update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Student {student_id} updated via API by admin")
                flash('Данные ученика обновлены.', 'success')
                return redirect(url_for('admin.students'))
            else:
                flash(result.get('description', 'Ошибка при обновлении ученика.'), 'danger')
        else:
            flash('Ошибка при обновлении ученика.', 'danger')

    return render_template('admin/edit_student.html', form=form, student=student)


@admin_bp.route('/confirm_delete/student/<int:student_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def confirm_delete_student(student_id):
    """Страница для подтверждения удаления студента"""
    if request.method == 'POST':
        api = AdminOneStudentAPI()
        response = api.delete(student_id)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Student {student_id} deleted via API by admin")
                flash('Ученик удален.', 'success')
            else:
                flash(result.get('description', 'Ошибка при удалении ученика.'), 'danger')
        else:
            flash('Ошибка при удалении ученика.', 'danger')
        return redirect(url_for('admin.students'))
    return render_template('admin/confirm_delete.html', entity='Ученик', id=student_id,
                           delete_url=url_for('admin.confirm_delete_student', student_id=student_id),
                           list_url=url_for('admin.students'))


@admin_bp.route('/teachers', defaults={'search_query': ''}, methods=['GET', 'POST'])
@admin_bp.route('/teachers/<string:search_query>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def teachers(search_query=''):
    """Страница для просмотра списка учителей"""
    form = TeacherSearchForm()

    if form.validate_on_submit():
        search_query = form.search.data.strip()
        return redirect(url_for('admin.teachers', search_query=search_query))

    if request.method == 'GET' and not search_query and 'search' in request.args:
        search_query = request.args.get('search', '').strip()
        if search_query:
            return redirect(url_for('admin.teachers', search_query=search_query))

    if search_query:
        form.search.data = search_query

    api = AdminAllTeachersAPI()
    response = api.get(search=search_query)

    if isinstance(response, tuple):
        teachers, status = response
        teachers = teachers.get('teachers', []) if isinstance(teachers, dict) else []
    else:
        flash('Ошибка при получении списка учителей.', 'danger')
        teachers = []

    if not teachers:
        logging.info(f"No teachers found for search_query: '{search_query}'")

    return render_template(
        'admin/teachers_list.html',
        form=form,
        teachers=teachers,
        search_query=search_query
    )


@admin_bp.route('/teacher/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_teacher():
    """Страница создания нового учителя"""
    form = CreateTeacherForm()
    if form.validate_on_submit():
        api = AdminOneTeacherAPI()
        try:
            profile_picture = base64.b64encode(form.profile_picture.data.read()).decode('utf-8') if form.profile_picture.data else None
        except Exception as e:
            logging.error(f"Error encoding profile picture: {str(e)}")
            flash('Ошибка при загрузке фото профиля.', 'danger')
            return render_template('admin/new_teacher.html', form=form)

        subject_ids = [sid for sid in form.subject_ids.data if sid != 0]

        data = {
            'username': form.username.data,
            'password': form.password.data,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
            'position_id': form.position_id.data,
            'class_id': form.class_id.data if form.class_id.data else None,
            'subject_ids': subject_ids,
            'profile_picture': profile_picture
        }
        logging.info(f"Creating new teacher with data: {data}")
        response = api.post(update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 201:
                logging.info(f"Teacher created via API by admin")
                flash('Учитель успешно создан.', 'success')
                return redirect(url_for('admin.teachers'))
            else:
                flash(result.get('description', 'Ошибка при создании учителя.'), 'danger')
        else:
            flash('Ошибка при создании учителя.', 'danger')
    return render_template('admin/new_teacher.html', form=form)


@admin_bp.route('/teacher/<int:teacher_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_teacher(teacher_id):
    """Страница изменения информации об учителе"""
    api = AdminOneTeacherAPI()
    response = api.get(teacher_id=teacher_id)
    logging.info(f"edit_teacher: Response for teacher_id={teacher_id}: {response}")

    if isinstance(response, tuple):
        teacher_data, status = response
        if status == 200:
            teacher = teacher_data.get('Teacher', {})
            if not teacher:
                logging.warning(f"edit_teacher: Empty teacher data for teacher_id={teacher_id}")
                flash('Данные учителя пусты.', 'danger')
                return redirect(url_for('admin.teachers'))
        else:
            logging.error(f"edit_teacher: API error for teacher_id={teacher_id}, status={status}, response={teacher_data}")
            flash(teacher_data.get('description', 'Ошибка при получении данных учителя.'), 'danger')
            return redirect(url_for('admin.teachers'))
    else:
        logging.error(f"edit_teacher: Invalid response for teacher_id={teacher_id}: {response}")
        flash('Ошибка при получении данных учителя.', 'danger')
        return redirect(url_for('admin.teachers'))

    logging.info(f"edit_teacher: Teacher data for teacher_id={teacher_id}: {teacher}")

    current_subject_ids = []
    current_position_id = None
    for position in teacher.get('positions', []):
        current_position_id = position.get('position_id')
        for subject in position.get('subjects', []):
            subject_id = subject.get('subject_id')
            if subject_id and subject_id not in current_subject_ids:
                current_subject_ids.append(subject_id)

    form_data = {
        'username': teacher.get('username'),
        'first_name': teacher.get('first_name'),
        'last_name': teacher.get('last_name'),
        'email': teacher.get('email'),
        'phone_number': teacher.get('phone_number'),
        'position_id': current_position_id,
        'class_id': teacher.get('classes', [{}])[0].get('class_id') if teacher.get('classes') else None,
        'subject_ids': current_subject_ids
    }

    form = EditTeacherForm(data=form_data)
    form.subject_ids.data = current_subject_ids

    if form.validate_on_submit():
        try:
            profile_picture = base64.b64encode(form.profile_picture.data.read()).decode('utf-8') if form.profile_picture.data else None
        except Exception as e:
            logging.error(f"Error encoding profile picture: {str(e)}")
            flash('Ошибка при загрузке фото профиля.', 'danger')
            return render_template('admin/edit_teacher.html', form=form, teacher=teacher)

        subject_ids = [sid for sid in form.subject_ids.data if sid != 0]

        data = {
            'username': form.username.data,
            'password': form.password.data or None,
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
            'position_id': form.position_id.data,
            'class_id': form.class_id.data if form.class_id.data else None,
            'subject_ids': subject_ids,
            'profile_picture': profile_picture
        }
        logging.info(f"Updating teacher {teacher_id} with data: {data}")
        response = api.patch(teacher_id, update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Teacher {teacher_id} updated via API by admin")
                flash('Данные учителя обновлены.', 'success')
                return redirect(url_for('admin.teachers'))
            else:
                flash(result.get('description', 'Ошибка при обновлении учителя.'), 'danger')
        else:
            flash('Ошибка при обновлении учителя.', 'danger')

    return render_template('admin/edit_teacher.html', form=form, teacher=teacher)


@admin_bp.route('/confirm_delete/teacher/<int:teacher_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def confirm_delete_teacher(teacher_id):
    """Страница для подтверждения удаления учителя"""
    if request.method == 'POST':
        api = AdminOneTeacherAPI()
        response = api.delete(teacher_id)
        logging.info(f"Delete teacher {teacher_id}: Response={response}")
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Teacher {teacher_id} deleted via API by admin")
                flash('Учитель удален.', 'success')
            else:
                flash(result.get('description', 'Ошибка при удалении учителя.'), 'danger')
        else:
            flash('Ошибка при удалении учителя.', 'danger')
        return redirect(url_for('admin.teachers'))
    return render_template('admin/confirm_delete.html', entity='Учитель', id=teacher_id,
                           delete_url=url_for('admin.confirm_delete_teacher', teacher_id=teacher_id),
                           list_url=url_for('admin.teachers'))


@admin_bp.route('/teachers/excel', defaults={'search_query': ''}, methods=['GET'])
@admin_bp.route('/teachers/excel/<string:search_query>', methods=['GET'])
@blueprint_login_required('admin_bp')
def teachers_excel(search_query=''):
    """Скачивание списка учителей в Excel"""
    if not search_query and 'search' in request.args:
        search_query = request.args.get('search', '').strip()
        logging.info(f"Retrieved search_query from query string: '{search_query}'")
    else:
        logging.info(f"Using search_query from path: '{search_query}'")

    logging.info(f"Exporting teachers to Excel with search_query: '{search_query}' (raw: {repr(search_query)})")
    excel_resource = AdminTeachersExcelFile()
    response = excel_resource.get(search_query=search_query)
    logging.info(f"Excel response generated for search_query: '{search_query}'")

    if not isinstance(response, Response):
        logging.error(f"Unexpected response from AdminTeachersExcelFile: {response}")
        flash('Ошибка при экспорте в Excel.', 'danger')
        return redirect(url_for('admin.teachers'))
    return response


@admin_bp.route('/schedules', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def schedules():
    """Страница просмотра списка расписания"""
    form = ScheduleSearchForm()
    filters = {}

    if request.method == 'POST' and form.validate_on_submit():
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
        logging.debug(f"POST filters applied: {filters}")
        query_string = '&'.join(f"{key}={value}" for key, value in filters.items())
        return redirect(url_for('admin.schedules') + (f"?{query_string}" if query_string else ""))

    if request.args:
        filters = {
            'teacher': request.args.get('teacher', '').strip(),
            'class': request.args.get('class_name', '').strip(),
            'subject': request.args.get('subject', '').strip(),
            'time': request.args.get('time', '').strip(),
            'day': request.args.get('day', '').strip()
        }
        form.teacher.data = filters['teacher']
        form.class_name.data = filters['class']
        form.subject.data = filters['subject']
        form.time.data = filters['time']
        form.day.data = filters['day']
        logging.debug(f"GET filters applied: {filters}")

    api = AdminAllSchedulesAPI()
    response = api.get(**filters)
    if isinstance(response, tuple):
        result, status = response
        if status == 200:
            schedules = result.get('schedules', []) if isinstance(result, dict) else []
            logging.debug(f"Schedules retrieved: {len(schedules)} items")
        else:
            error_message = result.get('description', 'Неизвестная ошибка') if isinstance(result, dict) else 'Неизвестная ошибка'
            flash(f'Ошибка при получении списка расписания: {error_message}', 'danger')
            logging.error(f"API error: {error_message}")
            schedules = []
    else:
        flash('Ошибка при получении списка расписания: Неверный формат ответа API.', 'danger')
        logging.error(f"Invalid API response format: {response}")
        schedules = []

    return render_template('admin/schedules_list.html', form=form, schedules=schedules)


@admin_bp.route('/schedule/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_schedule():
    """Страница для создания записи расписания"""
    form = CreateScheduleForm()
    if form.validate_on_submit():
        api = AdminOneScheduleAPI()
        data = {
            'class_id': form.class_id.data,
            'subject_id': form.subject_id.data,
            'teacher_id': form.teacher_id.data,
            'day_of_week': form.day_of_week.data,
            'start_time': form.start_time.data,
            'end_time': form.end_time.data
        }
        response = api.post(update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 201:
                logging.info(f"Schedule created via API by admin")
                flash('Запись расписания создана.', 'success')
                return redirect(url_for('admin.schedules'))
            else:
                flash(result.get('description', 'Ошибка при создании записи расписания.'), 'danger')
        else:
            flash('Ошибка при создании записи расписания.', 'danger')
    return render_template('admin/new_schedule.html', form=form)


@admin_bp.route('/schedule/<int:schedule_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_schedule(schedule_id):
    """Страница для изменения записи расписания"""
    api = AdminOneScheduleAPI()
    response = api.get(schedule_id=schedule_id)
    if isinstance(response, tuple):
        schedule, status = response
        schedule = schedule.get('schedule', {}) if isinstance(schedule, dict) else {}
    else:
        flash('Запись расписания не найдена.', 'danger')
        return redirect(url_for('admin.schedules'))

    form_data = {
        'class_id': schedule.get('class', {}).get('class_id'),
        'subject_id': schedule.get('subject', {}).get('subject_id'),
        'teacher_id': schedule.get('teacher', {}).get('teacher_id'),
        'day_of_week': schedule.get('day_of_week'),
        'start_time': schedule.get('start_time'),
        'end_time': schedule.get('end_time')
    }

    form = EditScheduleForm(data=form_data)
    if form.validate_on_submit():
        data = {
            'class_id': form.class_id.data,
            'subject_id': form.subject_id.data,
            'teacher_id': form.teacher_id.data,
            'day_of_week': form.day_of_week.data,
            'start_time': form.start_time.data,
            'end_time': form.end_time.data
        }
        response = api.patch(schedule_id, update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Schedule {schedule_id} updated via API by admin")
                flash('Запись расписания обновлена.', 'success')
                return redirect(url_for('admin.schedules'))
            else:
                flash(result.get('description', 'Ошибка при обновлении записи расписания.'), 'danger')
        else:
            flash('Ошибка при обновлении записи расписания.', 'danger')
    return render_template('admin/edit_schedule.html', form=form, schedule=schedule)


@admin_bp.route('/confirm_delete/schedule/<int:schedule_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def confirm_delete_schedule(schedule_id):
    """Страница подтверждения удаления записи расписания"""
    if request.method == 'POST':
        api = AdminOneScheduleAPI()
        response = api.delete(schedule_id)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Schedule {schedule_id} deleted via API by admin")
                flash('Запись расписания удалена.', 'success')
            else:
                flash(result.get('description', 'Ошибка при удалении записи расписания.'), 'danger')
        else:
            flash('Ошибка при удалении записи расписания.', 'danger')
        return redirect(url_for('admin.schedules'))
    return render_template('admin/confirm_delete.html', entity='Запись расписания', id=schedule_id,
                           delete_url=url_for('admin.confirm_delete_schedule', schedule_id=schedule_id),
                           list_url=url_for('admin.schedules'))


@admin_bp.route('/subjects', methods=['GET'])
@blueprint_login_required('admin_bp')
def subjects():
    """Страница для просмотра списка предметов"""
    api = AdminSubjectsApi()
    response = api.get()
    if isinstance(response, tuple):
        subjects, status = response
        subjects = subjects.get('subjects', []) if isinstance(subjects, dict) else []
    else:
        flash('Ошибка при получении списка предметов.', 'danger')
        subjects = []
    return render_template('admin/subjects_list.html', subjects=subjects)


@admin_bp.route('/subject/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_subject():
    """Страница для создания нового предмета"""
    form = CreateSubjectForm()
    if form.validate_on_submit():
        api = AdminSubjectApi()
        data = {'subject_name': form.subject_name.data}
        response = api.post(subject_name=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 201:
                logging.info(f"Subject created via API by admin")
                flash('Предмет создан.', 'success')
                return redirect(url_for('admin.subjects'))
            else:
                flash(result.get('description', 'Ошибка при создании предмета.'), 'danger')
        else:
            flash('Ошибка при создании предмета.', 'danger')
    return render_template('admin/new_subject.html', form=form)


@admin_bp.route('/subject/<int:subject_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_subject(subject_id):
    """Страница для изменения названия предмета"""
    api = AdminSubjectApi()
    response = api.get(subject_id=subject_id)
    if isinstance(response, tuple):
        subject_data, status = response
        subject = subject_data.get('Subject', {}) if isinstance(subject_data, dict) else {}
    else:
        flash('Предмет не найден.', 'danger')
        return redirect(url_for('admin.subjects'))

    form = EditSubjectForm(data=subject)
    if form.validate_on_submit():
        data = {'subject_name': form.subject_name.data}
        response = api.patch(subject_id, update_data=data)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Subject {subject_id} updated via API by admin")
                flash('Предмет обновлен.', 'success')
                return redirect(url_for('admin.subjects'))
            else:
                flash(result.get('description', 'Ошибка при обновлении предмета.'), 'danger')
        else:
            flash('Ошибка при обновлении предмета.', 'danger')
    return render_template('admin/edit_subject.html', form=form, subject=subject)


@admin_bp.route('/confirm_delete/subject/<int:subject_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def confirm_delete_subject(subject_id):
    """Подтверждение удаления предмета"""
    if request.method == 'POST':
        api = AdminSubjectApi()
        response = api.delete(subject_id)
        if isinstance(response, tuple):
            result, status = response
            if status == 200:
                logging.info(f"Subject {subject_id} deleted via API by admin")
                flash('Предмет удален.', 'success')
            else:
                flash(result.get('description', 'Ошибка при удалении предмета.'), 'danger')
        else:
            flash('Ошибка при удалении предмета.', 'danger')
        return redirect(url_for('admin.subjects'))
    return render_template('admin/confirm_delete.html', entity='Предмет', id=subject_id,
                           delete_url=url_for('admin.confirm_delete_subject', subject_id=subject_id),
                           list_url=url_for('admin.subjects'))


@admin_bp.route('/schedules/excel', methods=['GET'])
@blueprint_login_required('admin_bp')
def schedules_excel():
    """Скачивание списка расписания в Excel"""
    excel_resource = AdminScheduleExcelFile()
    response = excel_resource.get()
    return response


@admin_bp.route('/subjects/excel', methods=['GET'])
@blueprint_login_required('admin_bp')
def subjects_excel():
    """Скачивание списка предметов в Excel"""
    excel_resource = AdminSubjectsExcelFile()
    response = excel_resource.get()
    return response


@admin_bp.route('/settings', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def settings():
    """Страница настроек аккаунта администратора."""
    form = UserSettingsForm()
    api = UserSettingsAPI()

    username = current_user.username

    if form.validate_on_submit():
        update_data = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
        }

        if form.profile_picture.data:
            file = form.profile_picture.data
            image_data = base64.b64encode(file.read()).decode('utf-8')
            update_data['profile_picture'] = image_data

        if form.password.data:
            update_data['password'] = form.password.data

        response, status_code = api.patch(current_user.user_id, username=username, update_data=update_data)
        if status_code == 200:
            return redirect('/admin/')
        else:
            return render_template('admin/settings.html', form=form, message=response.get('description', 'Ошибка при обновлении'))

    response, status_code = api.get(current_user.user_id, username=username)
    if status_code != 200:
        return render_template('admin/settings.html', form=form, message=response.get('description', 'Ошибка при получении данных профиля'))

    user_data = response['user']
    form.first_name.data = user_data['first_name']
    form.last_name.data = user_data['last_name']
    form.email.data = user_data['email']
    form.phone_number.data = user_data['phone_number']

    return render_template('admin/settings.html', form=form)


@admin_bp.route('/generate_api_key', methods=['POST'])
@blueprint_login_required('admin_bp')
def generate_api_key():
    """Генерация API-ключа для администратора."""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            flash('Пользователь не найден.', 'danger')
            return redirect(url_for('admin.settings'))

        api_key = user.generate_api_key()
        db_sess.commit()
        logging.info(f"API key generated for admin user_id={user.user_id}")
        return render_template('admin/settings.html', form=UserSettingsForm(), api_key=api_key)
    except Exception as e:
        db_sess.rollback()
        logging.error(f"Error generating API key for admin user_id={current_user.user_id}: {str(e)}")
        flash(f'Ошибка при генерации API-ключа: {str(e)}', 'danger')
        return redirect(url_for('admin.settings'))
    finally:
        db_sess.close()


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница регистрации администратора"""
    db_sess = db_session.create_session()
    try:
        if current_user.is_authenticated and db_sess.query(Admin).filter(Admin.user_id == current_user.user_id).first():
            return redirect('/admin/')

        form = LoginForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(User).join(Admin, User.user_id == Admin.user_id).filter(
                User.username == form.username.data
            ).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect('/admin/')
            return render_template('admin/login.html', form=form, message='Неверный логин или пароль')
        return render_template('admin/login.html', form=form)

    finally:
        db_sess.close()


@admin_bp.route('/logout')
@blueprint_login_required('admin_bp')
def logout():
    """Выход из аккаунта администратора"""
    logout_user()
    return redirect('/admin/')
