from flask import render_template, redirect, flash, url_for
from flask_login import current_user, login_user, logout_user
from teacher import teacher_bp
from data import db_session
from api.user_settings_api import UserSettingsAPI
from forms.user_settings import UserSettingsForm
from decorators.login_decorator import blueprint_login_required
from forms.login import LoginForm
from data.teacher import Teacher
from data.user import User
import base64
import logging


logging.basicConfig(
    filename='routes.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


@teacher_bp.route('/')
def index():
    """Базовая страница учителя"""
    return render_template('teacher/index.html')


@teacher_bp.route('/settings', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def settings():
    """Страница настроек аккаунта учителя."""
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
            return redirect('/teacher/')
        else:
            return render_template('teacher/settings.html', form=form, message=response.get('description', 'Ошибка при обновлении'))

    response, status_code = api.get(current_user.user_id, username=username)
    if status_code != 200:
        return render_template('teacher/settings.html', form=form, message=response.get('description', 'Ошибка при получении данных профиля'))

    user_data = response['user']
    form.first_name.data = user_data['first_name']
    form.last_name.data = user_data['last_name']
    form.email.data = user_data['email']
    form.phone_number.data = user_data['phone_number']

    return render_template('teacher/settings.html', form=form)


@teacher_bp.route('/generate_api_key', methods=['POST'])
@blueprint_login_required('teacher_bp')
def generate_api_key():
    """Генерация API-ключа для учителя."""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            flash('Пользователь не найден.', 'danger')
            return redirect(url_for('teacher.settings'))

        api_key = user.generate_api_key()
        db_sess.commit()
        logging.info(f"API key generated for teacher user_id={user.user_id}")
        return render_template('teacher/settings.html', form=UserSettingsForm(), api_key=api_key)
    except Exception as e:
        db_sess.rollback()
        logging.error(f"Error generating API key for teacher user_id={current_user.user_id}: {str(e)}")
        flash(f'Ошибка при генерации API-ключа: {str(e)}', 'danger')
        return redirect(url_for('teacher.settings'))
    finally:
        db_sess.close()


@teacher_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница регистрации учителя"""
    db_sess = db_session.create_session()
    try:
        if current_user.is_authenticated and db_sess.query(Teacher).filter(Teacher.user_id == current_user.user_id).first():
            return redirect('/teacher/')

        form = LoginForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(User).join(Teacher, User.user_id == Teacher.user_id).filter(
                User.username == form.username.data
            ).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect('/teacher/')
            return render_template('teacher/login.html', form=form, message='Неверный логин или пароль')
        return render_template('teacher/login.html', form=form)

    finally:
        db_sess.close()


@teacher_bp.route('/logout')
@blueprint_login_required('teacher_bp')
def logout():
    """Выход из аккаунта учителя"""
    logout_user()
    return redirect('/teacher/')