from flask import jsonify
from flask_restful import Resource, abort
from flask_login import login_required, current_user
from data import db_session
from data.schedule import Schedule
from data.grade import Grade


class StudentScheduleAPI(Resource):
    @login_required
    def get(self, student_id):
        if current_user.id != student_id or current_user.role != 'student':
            abort(403, message="Доступ запрещен.")
        db_sess = db_session.create_session()
        schedules = db_sess.query(Schedule).filter(Schedule.student_id == student_id).all()
        return jsonify({"schedules": [schedule.to_dict() for schedule in schedules]})


class StudentGradesAPI(Resource):
    @login_required
    def get(self, student_id):
        if current_user.id != student_id or current_user.role != 'student':
            abort(403, message="Доступ запрещен.")
        db_sess = db_session.create_session()
        grades = db_sess.query(Grade).filter(Grade.student_id == student_id).all()
        return jsonify({"grades": [grade.to_dict() for grade in grades]})
