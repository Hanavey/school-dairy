from flask import Flask
from flask_restful import Api
from flask_login import LoginManager
from flask_migrate import Migrate
from data import db_session
from data.user import User
from student import student_bp
from teacher import teacher_bp
from admin import admin_bp
from api.student_api import StudentScheduleAPI, StudentGradesAPI
from api.teacher_api import TeacherScheduleAPI, TeacherGradesAPI
from api.admin.admin_students_api import AdminOneStudentAPI, AdminAllStudentsAPI
from api.admin.admin_teachers_api import AdminOneTeacherAPI, AdminAllTeachersAPI
from api.admin.admin_schedules_api import AdminOneScheduleAPI, AdminAllSchedulesAPI
from api.admin.admin_subjects_api import AdminSubjectApi, AdminSubjectsApi
from api.admin.admin_excel_files import (AdminStudentsExcelFile, AdminTeachersExcelFile, AdminSubjectsExcelFile,
                                         AdminScheduleExcelFile)
from api.user_settings_api import UserSettingsAPI


app = Flask(__name__)
app.config['SECRET_KEY'] = 'Dairy_SeCrEt_KeY_7634_9723_9872_0909'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/school_diary.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Инициализация базы данных
db_session.global_init("db/school_diary.db")

# Инициализация Flask-Migrate
# Мы передаём только app, а движок и metadata настроим в migrations/env.py
migrate = Migrate(app, db_session.get_engine(), render_as_batch=True)  # render_as_batch=True для SQLite

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin.login'

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(int(user_id))

# Регистрация blueprints
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Инициализация Flask-RESTful API
api = Api(app)
api.add_resource(StudentScheduleAPI, '/api/student/schedule/<int:student_id>')
api.add_resource(StudentGradesAPI, '/api/student/grades/<int:student_id>')
api.add_resource(TeacherScheduleAPI, '/api/teacher/schedule/<int:teacher_id>')
api.add_resource(TeacherGradesAPI, '/api/teacher/grades/<int:teacher_id>')
api.add_resource(AdminOneStudentAPI, '/api/admin/student/<int:student_id>', '/api/admin/student')
api.add_resource(AdminAllStudentsAPI, '/api/admin/students')
api.add_resource(AdminOneTeacherAPI, '/api/admin/teacher/<int:teacher_id>', '/api/admin/teacher')
api.add_resource(AdminAllTeachersAPI, '/api/admin/teachers')
api.add_resource(AdminOneScheduleAPI, '/api/admin/schedule/<int:schedule_id>', '/api/admin/schedule')
api.add_resource(AdminAllSchedulesAPI, '/api/admin/schedules')
api.add_resource(AdminSubjectApi, '/api/admin/subject/<int:subject_id>', '/api/admin/subject')
api.add_resource(AdminSubjectsApi, '/api/admin/subjects')
api.add_resource(UserSettingsAPI, '/api/user/settings')
api.add_resource(AdminStudentsExcelFile, '/api/admin/students/excel')
api.add_resource(AdminTeachersExcelFile, '/api/admin/teachers/excel')
api.add_resource(AdminScheduleExcelFile, '/api/admin/schedules/excel')
api.add_resource(AdminSubjectsExcelFile, '/api/admin/subjects/excel')


# Простая главная страница (опционально)
@app.route('/')
def index():
    return "Добро пожаловать в школьный дневник! Выберите приложение: <a href='/student'>Для учеников</a> | <a href='/teacher'>Для учителей</a>"


if __name__ == '__main__':
    app.run(debug=True)