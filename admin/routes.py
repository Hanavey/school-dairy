from admin import admin_bp
from data import db_session
from data.user import User
from data.admin import Admin
from flask_login import current_user, login_user, logout_user
from flask import render_template, redirect, request, jsonify
from forms.admin_login import LoginForm
from forms.admin_students import CreateStudentForm, EditStudentForm
from forms.admin_teachers import CreateTeacherForm, EditTeacherForm
from forms.admin_schedules import CreateScheduleForm, EditScheduleForm
from forms.admin_subjects import CreateSubjectForm, EditSubjectForm
from forms.user_settings import UserSettingsForm
from api.admin.admin_students_api import AdminOneStudentAPI, AdminAllStudentsAPI
from api.admin.admin_teachers_api import AdminOneTeacherAPI, AdminAllTeachersAPI
from api.admin.admin_schedules_api import AdminAllSchedulesAPI, AdminOneScheduleAPI
from api.admin.admin_subjects_api import AdminSubjectApi, AdminSubjectsApi
from api.admin.admin_excel_files import (AdminStudentsExcelFile, AdminTeachersExcelFile, AdminScheduleExcelFile,
                                         AdminSubjectsExcelFile)
from api.user_settings_api import UserSettingsAPI
from sqlalchemy.orm import joinedload
from data.student import Student
from data.classes import Class
from data.teacher import Teacher
from data.teacher_position import TeacherPosition
from data.subject import Subject
from data.schedule import Schedule
from decorators.login_decorator import blueprint_login_required
import base64


@admin_bp.route('/')
def index():
    return render_template('admin/index.html')


@admin_bp.route('/students')
@blueprint_login_required('admin_bp')
def students():
    api = AdminAllStudentsAPI()
    response, status = api.get()
    return render_template('admin/students_list.html', students=response['students'], message=response['message'])


@admin_bp.route('/students/excel')
@blueprint_login_required('admin_bp')
def students_excel():
    api = AdminStudentsExcelFile()
    return api.get()


@admin_bp.route('/student/<int:student_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_student(student_id):
    db_sess = db_session.create_session()
    try:
        # Получаем данные ученика
        student = (db_sess.query(Student)
                   .options(joinedload(Student.user))
                   .options(joinedload(Student.class_))
                   .filter(Student.student_id == student_id)
                   .first())

        if not student:
            return "Ученик не найден", 404

        # Получаем список всех классов
        classes = db_sess.query(Class).all()
        class_choices = [(cls.class_id, cls.class_name) for cls in classes]

        # Создаем форму
        form = EditStudentForm()
        form.class_id.choices = class_choices

        if form.validate_on_submit():
            # Формируем словарь с данными для передачи в patch
            update_data = {
                'username': form.username.data,
                'password': form.password.data if form.password.data else None,
                'first_name': form.first_name.data,
                'last_name': form.last_name.data,
                'email': form.email.data,
                'phone_number': form.phone_number.data,
                'class_id': form.class_id.data,
                'birth_date': form.birth_date.data.strftime('%Y-%m-%d'),
                'address': form.address.data,
            }

            # Обработка фото, если загружено
            if form.profile_picture.data:
                file = form.profile_picture.data
                image_data = base64.b64encode(file.read()).decode('utf-8')
                update_data['profile_picture'] = image_data

            # Создаем экземпляр API-класса
            api = AdminOneStudentAPI()

            # Вызываем метод patch напрямую, передавая update_data
            try:
                response, status_code = api.patch(student_id, update_data=update_data)
                if status_code == 200:
                    return redirect('/admin/students')  # Перенаправление вместо JSON
                else:
                    return render_template('admin/edit_student.html', student=student, form=form,
                                         message=response.get('description', 'Ошибка при обновлении'))
            except Exception as e:
                return render_template('admin/edit_student.html', student=student, form=form,
                                     message=str(e))

        # Заполняем форму текущими данными ученика для GET-запроса
        if request.method == 'GET':
            form.username.data = student.user.username
            form.first_name.data = student.user.first_name
            form.last_name.data = student.user.last_name
            form.email.data = student.user.email
            form.phone_number.data = student.user.phone_number
            form.class_id.data = student.class_.class_id
            form.birth_date.data = student.birth_date
            form.address.data = student.address

        return render_template('admin/edit_student.html', student=student, form=form)

    finally:
        db_sess.close()


@admin_bp.route('/student/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_student():
    db_sess = db_session.create_session()
    try:
        classes = db_sess.query(Class).all()
        class_choices = [(cls.class_id, cls.class_name) for cls in classes]

        form = CreateStudentForm()
        form.class_id.choices = class_choices

        if form.validate_on_submit():
            # Формируем данные для API
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
            }

            # Обработка фото, если загружено
            if form.profile_picture.data:
                file = form.profile_picture.data
                image_data = base64.b64encode(file.read()).decode('utf-8')
                data['profile_picture'] = image_data

            # Создаем экземпляр API-класса
            api = AdminOneStudentAPI()

            # Вызываем метод post напрямую
            try:
                response, status_code = api.post(update_data=data)
                print(f"API response: {response}, Status: {status_code}")
                if status_code == 201:
                    return redirect('/admin/students')
                else:
                    return render_template('admin/new_student.html', form=form, message=response.get('description', 'Ошибка при создании'))
            except Exception as e:
                return render_template('admin/new_student.html', form=form, message=str(e))

        return render_template('admin/new_student.html', form=form)

    finally:
        db_sess.close()


@admin_bp.route('/student/<int:student_id>/delete', methods=['POST'])
@blueprint_login_required('admin_bp')
def delete_student(student_id):
    db_sess = db_session.create_session()
    try:
        # Проверяем, существует ли ученик
        student = db_sess.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            return jsonify({'message': 'Ученик не найден.'}), 404

        # Вызываем метод delete из AdminOneStudentAPI
        api = AdminOneStudentAPI()
        response, status = api.delete(student_id)
        if status == 200:
            response['redirect'] = '/admin/students'  # Добавляем redirect в JSON
        return jsonify(response), status

    finally:
        db_sess.close()


@admin_bp.route('/teachers')
@blueprint_login_required('admin_bp')
def teachers():
    api = AdminAllTeachersAPI()
    response, status = api.get()
    return render_template('admin/teachers_list.html', teachers=response['teachers'], message=response['message'])


@admin_bp.route('/teachers/excel')
@blueprint_login_required('admin_bp')
def teachers_excel():
    api = AdminTeachersExcelFile()
    return api.get()


@admin_bp.route('/teacher/<int:teacher_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_teacher(teacher_id):
    db_sess = db_session.create_session()
    try:
        # Получаем данные учителя
        teacher = (db_sess.query(Teacher)
                   .options(joinedload(Teacher.user))
                   .options(joinedload(Teacher.classes))
                   .options(joinedload(Teacher.positions))
                   .filter(Teacher.teacher_id == teacher_id)
                   .first())

        if not teacher:
            return "Учитель не найден", 404

        # Получаем списки для выпадающих меню
        classes = db_sess.query(Class).all()
        positions = db_sess.query(TeacherPosition).all()
        subjects = db_sess.query(Subject).all()

        class_choices = [(0, 'Без класса')] + [(cls.class_id, cls.class_name) for cls in classes]
        position_choices = [(pos.position_id, pos.position_name) for pos in positions]
        subject_choices = [(0, 'Без предмета')] + [(sub.subject_id, sub.subject_name) for sub in subjects]

        # Создаем форму
        form = EditTeacherForm()
        form.class_id.choices = class_choices
        form.position_id.choices = position_choices
        form.subject_id.choices = subject_choices

        if form.validate_on_submit():
            # Формируем словарь с данными для передачи в patch
            update_data = {
                'username': form.username.data,
                'password': form.password.data if form.password.data else None,
                'first_name': form.first_name.data,
                'last_name': form.last_name.data,
                'email': form.email.data,
                'phone_number': form.phone_number.data,
                'position_id': form.position_id.data,
                'class_id': form.class_id.data if form.class_id.data != 0 else None,
                'subject_id': form.subject_id.data if form.subject_id.data != 0 else None,
            }

            # Обработка фото, если загружено
            if form.profile_picture.data:
                file = form.profile_picture.data
                image_data = base64.b64encode(file.read()).decode('utf-8')
                update_data['profile_picture'] = image_data

            # Создаем экземпляр API-класса
            api = AdminOneTeacherAPI()

            # Вызываем метод patch напрямую, передавая update_data
            response, status_code = api.patch(teacher_id, update_data=update_data)
            if status_code == 200:
                return redirect('/admin/teachers')  # Перенаправляем вместо JSON
            else:
                return render_template('admin/edit_teacher.html', teacher=teacher, form=form,
                                     message=response.get('description', 'Ошибка при обновлении'))

        # Заполняем форму текущими данными учителя для GET-запроса
        if request.method == 'GET':
            form.username.data = teacher.user.username
            form.first_name.data = teacher.user.first_name
            form.last_name.data = teacher.user.last_name
            form.email.data = teacher.user.email
            form.phone_number.data = teacher.user.phone_number
            form.position_id.data = teacher.positions[0].position_id if teacher.positions else position_choices[0][0]
            form.class_id.data = teacher.positions[0].class_id if teacher.positions and teacher.positions[0].class_id else 0
            form.subject_id.data = teacher.positions[0].subject_id if teacher.positions and teacher.positions[0].subject_id else 0

        return render_template('admin/edit_teacher.html', teacher=teacher, form=form)

    finally:
        db_sess.close()


@admin_bp.route('/teacher/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_teacher():
    db_sess = db_session.create_session()
    try:
        classes = db_sess.query(Class).all()
        positions = db_sess.query(TeacherPosition).all()
        subjects = db_sess.query(Subject).all()

        class_choices = [(0, 'Без класса')] + [(cls.class_id, cls.class_name) for cls in classes]
        position_choices = [(pos.position_id, pos.position_name) for pos in positions]
        subject_choices = [(0, 'Без предмета')] + [(sub.subject_id, sub.subject_name) for sub in subjects]

        form = CreateTeacherForm()
        form.class_id.choices = class_choices
        form.position_id.choices = position_choices
        form.subject_id.choices = subject_choices

        if form.validate_on_submit():
            # Формируем данные для API
            data = {
                'username': form.username.data,
                'password': form.password.data,
                'first_name': form.first_name.data,
                'last_name': form.last_name.data,
                'email': form.email.data,
                'phone_number': form.phone_number.data,
                'position_id': form.position_id.data,
                'class_id': form.class_id.data if form.class_id.data != 0 else None,
                'subject_id': form.subject_id.data if form.subject_id.data != 0 else None,
            }

            # Обработка фото, если загружено
            if form.profile_picture.data:
                file = form.profile_picture.data
                image_data = base64.b64encode(file.read()).decode('utf-8')
                data['profile_picture'] = image_data

            # Создаем экземпляр API-класса
            api = AdminOneTeacherAPI()

            # Вызываем метод post напрямую
            try:
                response, status_code = api.post(update_data=data)
                if status_code == 201:
                    return redirect('/admin/teachers')
                else:
                    return render_template('admin/new_teacher.html', form=form, message=response.get('description', 'Ошибка при создании'))
            except Exception as e:
                return render_template('admin/new_teacher.html', form=form, message=str(e))

        return render_template('admin/new_teacher.html', form=form)

    finally:
        db_sess.close()


@admin_bp.route('/teacher/<int:teacher_id>/delete', methods=['POST'])
@blueprint_login_required('admin_bp')
def delete_teacher(teacher_id):
    db_sess = db_session.create_session()
    try:
        # Проверяем, существует ли учитель
        teacher = db_sess.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
        if not teacher:
            return jsonify({'message': 'Учитель не найден.'}), 404

        # Вызываем метод delete из AdminOneTeacherAPI
        api = AdminOneTeacherAPI()
        response, status = api.delete(teacher_id)
        if status == 200:
            response['redirect'] = '/admin/teachers'  # Добавляем redirect
        return jsonify(response), status

    finally:
        db_sess.close()


@admin_bp.route('/schedules', methods=['GET'])
@blueprint_login_required('admin_bp')
def schedules():
    # Получаем параметры фильтрации из запроса
    teacher_filter = request.args.get('teacher', '').strip()
    class_filter = request.args.get('class', '').strip()
    time_filter = request.args.get('time', '').strip()
    day_filter = request.args.get('day', '').strip()

    api = AdminAllSchedulesAPI()
    response, status = api.get()

    if status != 200:
        return render_template('admin/schedules_list.html', schedules=[], message=response.get('description', 'Ошибка при получении расписания'))

    schedules = response['schedules']

    # Применяем фильтры
    filtered_schedules = schedules

    # Фильтр по учителю (поиск по объединённой строке "Имя Фамилия")
    if teacher_filter:
        filtered_schedules = [
            s for s in filtered_schedules
            if teacher_filter.lower() in f"{s['teacher']['first_name'] or ''} {s['teacher']['last_name'] or ''}".lower()
        ]

    # Фильтр по классу (поиск по названию класса)
    if class_filter:
        filtered_schedules = [
            s for s in filtered_schedules
            if class_filter.lower() in (s['class']['class_name'] or '').lower()
        ]

    # Фильтр по времени (поиск по времени начала)
    if time_filter:
        filtered_schedules = [
            s for s in filtered_schedules
            if time_filter.lower() in (s['start_time'] or '').lower()
        ]

    # Фильтр по дню недели
    if day_filter:
        filtered_schedules = [
            s for s in filtered_schedules
            if day_filter.lower() in (s['day_of_week'] or '').lower()
        ]

    # Формируем сообщение
    if not filtered_schedules:
        message = 'Нет записей, соответствующих критериям поиска.'
    else:
        message = f'Найдено {len(filtered_schedules)} записей расписания.'

    return render_template('admin/schedules_list.html', schedules=filtered_schedules, message=message,
                         teacher_filter=teacher_filter, class_filter=class_filter,
                         time_filter=time_filter, day_filter=day_filter)


@admin_bp.route('/schedules/excel', methods=['GET'])
@blueprint_login_required('admin_bp')
def excel_schedules():
    api = AdminScheduleExcelFile()
    return api.get()


@admin_bp.route('/schedule/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_schedule():
    db_sess = db_session.create_session()
    try:
        # Получаем данные для выпадающих списков
        classes = db_sess.query(Class).all()
        subjects = db_sess.query(Subject).all()
        teachers = db_sess.query(Teacher).options(joinedload(Teacher.user)).all()

        form = CreateScheduleForm()
        form.class_id.choices = [(cls.class_id, cls.class_name) for cls in classes]
        form.subject_id.choices = [(sub.subject_id, sub.subject_name) for sub in subjects]
        form.teacher_id.choices = [(t.teacher_id, f"{t.user.first_name} {t.user.last_name}") for t in teachers]

        if form.validate_on_submit():
            # Формируем данные для API
            data = {
                'class_id': form.class_id.data,
                'subject_id': form.subject_id.data,
                'teacher_id': form.teacher_id.data,
                'day_of_week': form.day_of_week.data,
                'start_time': form.start_time.data,
                'end_time': form.end_time.data
            }

            # Создаем экземпляр API-класса
            api = AdminOneScheduleAPI()

            # Вызываем метод post напрямую
            response, status_code = api.post(update_data=data)
            if status_code == 201:
                return redirect('/admin/schedules')
            else:
                return render_template('admin/new_schedule.html', form=form, message=response.get('description', 'Ошибка при создании'))

        return render_template('admin/new_schedule.html', form=form)

    finally:
        db_sess.close()


@admin_bp.route('/schedule/<int:schedule_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_schedule(schedule_id):
    db_sess = db_session.create_session()
    try:
        # Получаем данные расписания
        schedule = (db_sess.query(Schedule)
                    .options(joinedload(Schedule.class_))
                    .options(joinedload(Schedule.subject))
                    .options(joinedload(Schedule.teacher).joinedload(Teacher.user))
                    .filter(Schedule.schedule_id == schedule_id)
                    .first())

        if not schedule:
            return "Запись расписания не найдена", 404

        # Получаем данные для выпадающих списков
        classes = db_sess.query(Class).all()
        subjects = db_sess.query(Subject).all()
        teachers = db_sess.query(Teacher).options(joinedload(Teacher.user)).all()

        # Создаем форму
        form = EditScheduleForm()
        form.class_id.choices = [(cls.class_id, cls.class_name) for cls in classes]
        form.subject_id.choices = [(sub.subject_id, sub.subject_name) for sub in subjects]
        form.teacher_id.choices = [(t.teacher_id, f"{t.user.first_name} {t.user.last_name}") for t in teachers]

        if form.validate_on_submit():
            # Формируем словарь с данными для передачи в patch
            update_data = {
                'class_id': form.class_id.data,
                'subject_id': form.subject_id.data,
                'teacher_id': form.teacher_id.data,
                'day_of_week': form.day_of_week.data,
                'start_time': form.start_time.data,
                'end_time': form.end_time.data
            }

            # Создаем экземпляр API-класса
            api = AdminOneScheduleAPI()

            # Вызываем метод patch напрямую
            response, status_code = api.patch(schedule_id, update_data=update_data)
            if status_code == 200:
                return redirect('/admin/schedules')
            else:
                return render_template('admin/edit_schedule.html', schedule=schedule, form=form,
                                     message=response.get('description', 'Ошибка при обновлении'))

        # Заполняем форму текущими данными расписания для GET-запроса
        if request.method == 'GET':
            form.class_id.data = schedule.class_id
            form.subject_id.data = schedule.subject_id
            form.teacher_id.data = schedule.teacher_id
            form.day_of_week.data = schedule.day_of_week
            form.start_time.data = schedule.start_time
            form.end_time.data = schedule.end_time

        return render_template('admin/edit_schedule.html', schedule=schedule, form=form)

    finally:
        db_sess.close()


@admin_bp.route('/schedule/<int:schedule_id>/delete', methods=['POST'])
@blueprint_login_required('admin_bp')
def delete_schedule(schedule_id):
    db_sess = db_session.create_session()
    try:
        # Проверяем, существует ли запись
        schedule = db_sess.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()
        if not schedule:
            return jsonify({'message': 'Запись расписания не найдена.'}), 404

        # Вызываем метод delete из AdminOneScheduleAPI
        api = AdminOneScheduleAPI()
        response, status = api.delete(schedule_id)
        if status == 200:
            response['redirect'] = '/admin/schedules'  # Добавляем redirect в JSON
        return jsonify(response), status

    finally:
        db_sess.close()


# Новые маршруты для предметов

@admin_bp.route('/subjects', methods=['GET'])
@blueprint_login_required('admin_bp')
def subjects():
    """Отображение списка всех предметов."""
    api = AdminSubjectsApi()
    response, status = api.get()

    if status != 200:
        return render_template('admin/subjects_list.html', subjects=[], message=response.get('description', 'Ошибка при получении списка предметов'))

    subjects = response['subjects']
    message = response['message']
    return render_template('admin/subjects_list.html', subjects=subjects, message=message)


@admin_bp.route('/subjects/excel', methods=['GET'])
@blueprint_login_required('admin_bp')
def subjects_excel():
    api = AdminSubjectsExcelFile()
    return api.get()


@admin_bp.route('/subject/new', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def new_subject():
    """Создание нового предмета."""
    form = CreateSubjectForm()

    if form.validate_on_submit():
        # Формируем данные для API
        data = {
            'subject_name': form.subject_name.data
        }

        # Создаем экземпляр API-класса
        api = AdminSubjectApi()

        # Вызываем метод post напрямую
        response, status_code = api.post(subject_name=data['subject_name'])
        if status_code == 201:
            return redirect('/admin/subjects')
        else:
            return render_template('admin/new_subject.html', form=form, message=response.get('description', 'Ошибка при создании предмета'))

    return render_template('admin/new_subject.html', form=form)


@admin_bp.route('/subject/<int:subject_id>', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def edit_subject(subject_id):
    """Редактирование предмета."""
    db_sess = db_session.create_session()
    try:
        # Получаем данные предмета
        subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
        if not subject:
            return "Предмет не найден", 404

        form = EditSubjectForm()

        if form.validate_on_submit():
            # Формируем данные для API
            update_data = {
                'subject_name': form.subject_name.data
            }

            # Создаем экземпляр API-класса
            api = AdminSubjectApi()

            # Вызываем метод patch напрямую
            response, status_code = api.patch(subject_id, update_data=update_data)
            if status_code == 200:
                return redirect('/admin/subjects')
            else:
                return render_template('admin/edit_subject.html', subject=subject, form=form,
                                     message=response.get('description', 'Ошибка при обновлении'))

        # Заполняем форму текущими данными предмета для GET-запроса
        if request.method == 'GET':
            form.subject_name.data = subject.subject_name

        return render_template('admin/edit_subject.html', subject=subject, form=form)

    finally:
        db_sess.close()


@admin_bp.route('/subject/<int:subject_id>/delete', methods=['POST'])
@blueprint_login_required('admin_bp')
def delete_subject(subject_id):
    """Удаление предмета."""
    db_sess = db_session.create_session()
    try:
        # Проверяем, существует ли предмет
        subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
        if not subject:
            return jsonify({'message': 'Предмет не найден.'}), 404

        # Вызываем метод delete из AdminSubjectApi
        api = AdminSubjectApi()
        response, status = api.delete(subject_id)
        if status == 200:
            response['redirect'] = '/admin/subjects'  # Добавляем redirect в JSON
        return jsonify(response), status

    finally:
        db_sess.close()


@admin_bp.route('/settings', methods=['GET', 'POST'])
@blueprint_login_required('admin_bp')
def settings():
    """Страница настроек администратора."""
    form = UserSettingsForm()
    api = UserSettingsAPI()

    # Определяем username текущего пользователя
    username = current_user.username

    if form.validate_on_submit():
        # Формируем данные для обновления
        update_data = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
        }

        # Обработка фото, если загружено
        if form.profile_picture.data:
            file = form.profile_picture.data
            image_data = base64.b64encode(file.read()).decode('utf-8')
            update_data['profile_picture'] = image_data

        # Обновление пароля, если указан
        if form.password.data:
            update_data['password'] = form.password.data

        # Вызываем метод PATCH из API
        response, status_code = api.patch(current_user.user_id, username=username, update_data=update_data)
        if status_code == 200:
            return redirect('/admin/')
        else:
            return render_template('admin/settings.html', form=form, message=response.get('description', 'Ошибка при обновлении'))

    # Для GET-запроса получаем данные профиля через API
    response, status_code = api.get(current_user.user_id, username=username)
    if status_code != 200:
        return render_template('admin/settings.html', form=form, message=response.get('description', 'Ошибка при получении данных профиля'))

    # Заполняем форму данными из API
    user_data = response['user']
    form.first_name.data = user_data['first_name']
    form.last_name.data = user_data['last_name']
    form.email.data = user_data['email']
    form.phone_number.data = user_data['phone_number']

    return render_template('admin/settings.html', form=form)


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
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
    logout_user()
    return redirect('/admin/')
