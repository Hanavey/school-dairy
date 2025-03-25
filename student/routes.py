from flask import render_template, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from student import student_bp
from forms.students import LoginForm
from data import db_session
from data.user import User
from data.student import Student


@student_bp.route('/')
def index():
    return render_template('student/index.html')


@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    db_sess = db_session.create_session()
    if current_user.is_authenticated and db_sess.query(Student).filter(user=current_user).first():
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


@student_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/student/')
