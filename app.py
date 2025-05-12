from flask import Flask, render_template
from flask_restful import Api
from flask_login import LoginManager
from flask_migrate import Migrate
from data import db_session
from data.user import User
from student import student_bp
from teacher import teacher_bp
from admin import admin_bp
from api.admin.admin_students_api import AdminOneStudentAPI, AdminAllStudentsAPI
from api.admin.admin_teachers_api import AdminOneTeacherAPI, AdminAllTeachersAPI
from api.admin.admin_schedules_api import AdminOneScheduleAPI, AdminAllSchedulesAPI
from api.admin.admin_subjects_api import AdminSubjectApi, AdminSubjectsApi
from api.admin.admin_excel_files import (AdminStudentsExcelFile, AdminTeachersExcelFile, AdminSubjectsExcelFile,
                                         AdminScheduleExcelFile)
from api.teacher.teacher_classes_api import TeacherClassesAPI
from api.teacher.teacher_list_api import TeacherListAPI
from api.user_settings_api import UserSettingsAPI
from api.teacher.class_teacher_api import ClassTeacherResource
from api.teacher.teacher_excel_files import ClassExcelReportResource, ClassFullReportResource, TeacherScheduleExcelResource
from api.teacher.teacher_grades_homework_attendance_api import GradeResource, AttendanceResource, HomeworkResource
from api.teacher.teacher_schedule_api import TeacherScheduleResource
from api.teacher.teacher_subjects_api import TeacherSubjectsAPI
from api.students.students_api import (StudentHomeworkResource, StudentScheduleResource,
                                       StudentGradesAttendanceResource, ClassmatesResource)
from forms.adress_form import AddressSearchForm
import urllib
import requests


app = Flask(__name__)
app.config['SECRET_KEY'] = 'Dairy_SeCrEt_KeY_7634_9723_9872_0909'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/school_diary.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db_session.global_init("db/school_diary.db")

migrate = Migrate(app, db_session.get_engine(), render_as_batch=True)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(int(user_id))

app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(admin_bp, url_prefix='/admin')


api = Api(app)
api.add_resource(AdminOneStudentAPI, '/api/admin/student/<int:student_id>', '/api/admin/student')
api.add_resource(AdminAllStudentsAPI, '/api/admin/students/<string:search>', '/api/admin/students')
api.add_resource(AdminOneTeacherAPI, '/api/admin/teacher/<int:teacher_id>', '/api/admin/teacher')
api.add_resource(AdminAllTeachersAPI, '/api/admin/teachers/<string:search>', '/api/admin/teachers')
api.add_resource(AdminOneScheduleAPI, '/api/admin/schedule/<int:schedule_id>', '/api/admin/schedule')
api.add_resource(AdminAllSchedulesAPI, '/api/admin/schedules')
api.add_resource(AdminSubjectApi, '/api/admin/subject/<int:subject_id>', '/api/admin/subject')
api.add_resource(AdminSubjectsApi, '/api/admin/subjects')
api.add_resource(UserSettingsAPI, '/api/user/settings')
api.add_resource(AdminStudentsExcelFile, '/api/admin/students/excel/<string:search_query>', '/api/admin/students/excel')
api.add_resource(AdminTeachersExcelFile, '/api/admin/teachers/excel/<string:search_query>', '/api/admin/teachers/excel')
api.add_resource(AdminScheduleExcelFile, '/api/admin/schedules/excel')
api.add_resource(AdminSubjectsExcelFile, '/api/admin/subjects/excel')

api.add_resource(TeacherClassesAPI, '/api/teachers/classes', '/api/teachers/classes/<int:class_id>')
api.add_resource(TeacherListAPI, '/api/teachers/free-teachers')
api.add_resource(ClassTeacherResource, '/api/teachers/my-class')
api.add_resource(GradeResource, '/api/teachers/classes/<int:class_id>/grades', '/api/teachers/grades', '/api/teachers/grades/<int:grade_id>')
api.add_resource(HomeworkResource, '/api/teachers/classes/<int:class_id>/homework', '/api/teachers/homework')
api.add_resource(AttendanceResource, '/api/teachers/classes/<int:class_id>/attendance', '/api/teachers/attendance')
api.add_resource(TeacherScheduleResource, '/api/teachers/schedule')
api.add_resource(TeacherSubjectsAPI, '/api/teachers/classes/<int:class_id>/subjects')
api.add_resource(ClassExcelReportResource, '/api/teachers/classes/<int:class_id>/<int:subject_id>/excel')
api.add_resource(ClassFullReportResource, '/api/teachers/my-class/excel')
api.add_resource(TeacherScheduleExcelResource, '/api/teachers/schedule/excel')

api.add_resource(StudentScheduleResource, '/api/student/schedule')
api.add_resource(StudentGradesAttendanceResource, '/api/student/grades_attendance/<int:subject_id>')
api.add_resource(StudentHomeworkResource, '/api/student/homework')
api.add_resource(ClassmatesResource, '/api/student/classmates')


@app.route('/', methods=['GET', 'POST'])
def index():
    form = AddressSearchForm()

    default_center = '37.6173,55.7558'
    default_address = 'Москва, центр'
    default_coords = default_center
    map_url = f"https://static-maps.yandex.ru/1.x/?ll={default_center}&z=15&l=map&size=600,400&pt={default_center},pm2rdm&apikey=81b63ec7-b5bf-4e94-97fd-5645a56b1305"

    if form.validate_on_submit():
        address = form.address.data
        try:
            geocoder_url = f"https://geocode-maps.yandex.ru/1.x/?apikey=191ba092-d250-414d-b5ec-bf6ac8d9a224&geocode={urllib.parse.quote(address)}&format=json"
            response = requests.get(geocoder_url)
            response.raise_for_status()
            geocoder_data = response.json()

            feature = geocoder_data['response']['GeoObjectCollection']['featureMember']
            if feature:
                point = feature[0]['GeoObject']['Point']['pos']
                longitude, latitude = point.split()
                default_coords = f"{longitude},{latitude}"
                default_address = feature[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['text']

                map_url = f"https://static-maps.yandex.ru/1.x/?ll={default_coords}&z=15&l=map&size=600,400&pt={default_coords},pm2rdm&apikey=81b63ec7-b5bf-4e94-97fd-5645a56b1305"
            else:
                default_address = "Адрес не найден"
                map_url = None
        except Exception as e:
            default_address = f"Ошибка при поиске адреса: {str(e)}"

    return render_template(
        'index.html',
        form=form,
        map_url=map_url,
        address=default_address,
        coords=default_coords
    )


@app.errorhandler(404)
def not_found(error):
    return render_template('error_404.html')


if __name__ == '__main__':
    app.run(debug=True)