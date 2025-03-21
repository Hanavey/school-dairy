from flask import Flask, render_template, request, session, redirect, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import datetime
from data import db_session
from data.user import User
from forms.user import LoginForm

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'SCHOOL_diary_KeY_5509_8970_1345_6245'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

@app.route('/')
def index():
    return render_template('index.html', current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template('login.html', form=form, message='Неверный логин или пароль')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required #Защищенный маршрут! гарантирует, что пользователь авторизован
def logout():
    logout_user() #пользователь выходит из системы,
    # Flask-Login удаляет его идентификатор из сессии
    return redirect("/")


if __name__ == '__main__':
    db_session.global_init("db/school_dairy.db")
    app.run(port=8080, host='127.0.0.1', debug=True)
