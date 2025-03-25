from admin import admin_bp
from data import db_session
from data.user import User
from data.admin import Admin
from flask_login import login_required, current_user, login_user, logout_user
from flask import render_template, redirect
from forms.admin import LoginForm
from api.admin_students_api import AdminOneStudentAPI, AdminAllStudentsAPI


@admin_bp.route('/')
def index():
    return render_template('admin/index.html')


@admin_bp.route('/students')
def students():
    print('\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
    api = AdminAllStudentsAPI()
    response, status = api.get()
    return render_template('admin/students_list.html', students=response['students'], message=response['message'])


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    db_sess = db_session.create_session()
    if current_user.is_authenticated and db_sess.query(Admin).filter(user=current_user).first():
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


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/admin/')
