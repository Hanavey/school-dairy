from flask_restful import Resource
from flask_login import login_required, current_user
from data import db_session
from data.schedule import Schedule
from data.grade import Grade

class TeacherScheduleAPI(Resource):
    @login_required
    def get(self, teacher_id):
        if current_user.id != teacher_id or current_user.role != 'teacher':
            return {"message": "Доступ запрещен"}, 403
        db_sess = db_session.create_session()
        schedules = db_sess.query(Schedule).filter(Schedule.teacher_id == teacher_id).all()
        return {"schedules": [schedule.to_dict() for schedule in schedules]}, 200

class TeacherGradesAPI(Resource):
    @login_required
    def get(self, teacher_id):
        if current_user.id != teacher_id or current_user.role != 'teacher':
            return {"message": "Доступ запрещен"}, 403
        db_sess = db_session.create_session()
        grades = db_sess.query(Grade).filter(Grade.teacher_id == teacher_id).all()
        return {"grades": [grade.to_dict() for grade in grades]}, 200