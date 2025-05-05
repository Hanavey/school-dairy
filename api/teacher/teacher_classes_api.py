from flask_restful import Resource
from decorators.authorization_teacher_decorator import teacher_authorization_required
from data import db_session
from data.teacher import Teacher
from data.user import User
from data.teacher_position import TeacherPosition
from data.teacher_position_assignment import TeacherPositionAssignment


class TeacherOneClassApi(Resource):
    @teacher_authorization_required('/api/teacher/class/<int:class_id>', method='GET')
    def get(self, class_id, username=None):
        db_sess = db_session.create_session()
        try:
            is_head_teacher = True if (db_sess.query(TeacherPosition.position_name)
                .join(TeacherPositionAssignment, TeacherPositionAssignment.position_id == TeacherPosition.position_id)
                .join(Teacher, Teacher.teacher_id == TeacherPositionAssignment.teacher_id)
                .join(User, User.user_id == Teacher.user_id)
                .filter(User.username == username)
                .first())[0] == 'Завуч' else False

            if not is_head_teacher:


        finally:
            db_sess.close()
