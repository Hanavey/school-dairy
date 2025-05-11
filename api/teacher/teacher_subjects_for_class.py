from flask_restful import Resource
from decorators.authorization_teacher_decorator import teacher_authorization_required
from data import db_session
from data.subject import Subject
from data.schedule import Schedule
from data.teacher import Teacher
from data.user import User


class TeacherSubjectsForClass(Resource):
    @teacher_authorization_required('/api/teacher/<class_id>', method='GET')
    def get(self, class_id, username=None, position_name=None):
        db_sess = db_session.create_session()
        try:
            if position_name != 'Завуч':
                subjects = (db_sess.query(Subject.subject_id, Subject.subject_name)
                        .join(Schedule, Schedule.subject_id == Subject.subject_id)
                        .join(Teacher, Teacher.teacher_id == Schedule.teacher_id)
                        .join(User, User.user_id == Teacher.user_id)
                        .filter(User.username == username, Schedule.class_id == class_id)
                        .distinct()
                        .all())
            else:
                subjects = (db_sess.query(Subject.subject_id, Subject.subject_name)
                            .join(Schedule, Schedule.subject_id == Subject.subject_id)
                            .filter(Schedule.class_id == class_id)
                            .distinct()
                            .all())
            return {'subjects': sorted(subjects, key=lambda x: x[0])}, 200
        finally:
            db_sess.close()