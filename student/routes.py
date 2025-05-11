from flask import render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user
from student import student_bp
from forms.login import LoginForm
from data import db_session
from data.user import User
from forms.user_settings import UserSettingsForm
from api.user_settings_api import UserSettingsAPI
from api.students.students_api import (StudentScheduleResource, StudentGradesAttendanceResource,
                                       StudentHomeworkResource, ClassmatesResource)
from data.student import Student
from decorators.login_decorator import blueprint_login_required
import base64
import logging


logging.basicConfig(
    filename='routes.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


@student_bp.route('/')
def index():
    return render_template('student/index.html')


@student_bp.route('/schedule')
@blueprint_login_required('student_bp')
def schedule():
    """Страница расписания уроков студента."""
    api = StudentScheduleResource()
    response, status_code = api.get()

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении расписания'), 'danger')
        return render_template('student/schedule.html', schedule=[])

    return render_template('student/schedule.html', schedule=response['data']['schedule'],
                           class_id=response['data']['class_id'])


@student_bp.route('/grades_attendance/<int:subject_id>')
@blueprint_login_required('student_bp')
def grades_attendance(subject_id):
    """Страница оценок и посещаемости студента по предмету."""
    api = StudentGradesAttendanceResource()
    response, status_code = api.get(subject_id=subject_id)

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении данных'), 'danger')
        return render_template('student/grades_attendance.html', grades=[], attendance=[], subject_name='')

    return render_template(
        'student/grades_attendance.html',
        grades=response['data']['grades'],
        attendance=response['data']['attendance'],
        subject_name=response['data']['subject_name'],
        average_grade=response['data']['average_grade']
    )


@student_bp.route('/classmates')
@blueprint_login_required('student_bp')
def classmates():
    """Страница просмотра одноклассников."""
    api = ClassmatesResource()
    response, status_code = api.get()

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении данных'), 'danger')
        return render_template('student/classmates.html', classmates=[])

    return render_template(
        'student/classmates.html',
        classmates=response['data']['classmates'],
        class_id=response['data']['class_id']
    )


@student_bp.route('/grades_attendance_select')
@blueprint_login_required('student_bp')
def grades_attendance_select():
    """Страница выбора предмета для просмотра оценок и посещаемости через API расписания."""
    api = StudentScheduleResource()
    response, status_code = api.get()

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении данных'), 'danger')
        return render_template('student/grades_attendance_select.html', subjects=[])

    # Извлекаем уникальные предметы из расписания
    schedule = response['data']['schedule']
    # Используем словарь для уникальности по subject_id
    subjects_dict = {s['subject_id']: {'subject_id': s['subject_id'], 'subject_name': s['subject_name']} for s in
                     schedule}
    subjects = list(subjects_dict.values())

    if not subjects:
        flash('Предметы не найдены.', 'warning')
        return render_template('student/grades_attendance_select.html', subjects=[])

    return render_template('student/grades_attendance_select.html', subjects=subjects)


@student_bp.route('/homework')
@blueprint_login_required('student_bp')
def homework():
    """Страница домашнего задания студента."""
    api = StudentHomeworkResource()
    response, status_code = api.get()

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении домашнего задания'), 'danger')
        return render_template('student/homework.html', homeworks=[])

    return render_template('student/homework.html', homeworks=response['data']['homeworks'],
                           class_id=response['data']['class_id'])


@student_bp.route('/settings', methods=['GET', 'POST'])
@blueprint_login_required('student_bp')
def settings():
    """Страница настроек аккаунта ученика."""
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
            return redirect('/student/')
        else:
            return render_template('student/settings.html', form=form,
                                   message=response.get('description', 'Ошибка при обновлении'))

    response, status_code = api.get(current_user.user_id, username=username)
    if status_code != 200:
        return render_template('student/settings.html', form=form,
                               message=response.get('description', 'Ошибка при получении данных профиля'))

    user_data = response['user']
    form.first_name.data = user_data['first_name']
    form.last_name.data = user_data['last_name']
    form.email.data = user_data['email']
    form.phone_number.data = user_data['phone_number']

    return render_template('student/settings.html', form=form)


@student_bp.route('/generate_api_key', methods=['POST'])
@blueprint_login_required('student_bp')
def generate_api_key():
    """Генерация API-ключа для учителя."""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            flash('Пользователь не найден.', 'danger')
            return redirect(url_for('student.settings'))

        api_key = user.generate_api_key()
        db_sess.commit()
        logging.info(f"API key generated for teacher user_id={user.user_id}")
        return render_template('student/settings.html', form=UserSettingsForm(), api_key=api_key)
    except Exception as e:
        db_sess.rollback()
        logging.error(f"Error generating API key for teacher user_id={current_user.user_id}: {str(e)}")
        flash(f'Ошибка при генерации API-ключа: {str(e)}', 'danger')
        return redirect(url_for('student.settings'))
    finally:
        db_sess.close()


@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница регистрации учителя"""
    db_sess = db_session.create_session()
    try:
        if current_user.is_authenticated and db_sess.query(Student).filter(
                Student.user_id == current_user.user_id).first():
            return redirect('/student/')

        form = LoginForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(User).join(Student, User.user_id == Student.user_id).filter(
                User.username == form.username.data
            ).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect('/student/')
            return render_template('student/login.html', form=form, message='Неверный логин или пароль')
        return render_template('student/login.html', form=form)

    finally:
        db_sess.close()


@student_bp.route('/logout')
@blueprint_login_required('student_bp')
def logout():
    """Выход из аккаунта учителя"""
    logout_user()
    return redirect('/student/')