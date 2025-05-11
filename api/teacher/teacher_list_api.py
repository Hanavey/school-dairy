from flask_restful import Resource
from sqlalchemy.orm import joinedload
from data import db_session
from data.teacher import Teacher
from data.user import User
from data.classes import Class
from decorators.authorization_teacher_decorator import teacher_authorization_required
import logging

logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


class TeacherListAPI(Resource):
    """Класс для API получения списка свободных учителей (без классного руководства)"""

    @teacher_authorization_required("/api/teacher/teachers", method="GET")
    def get(self, username=None, position_name=None):
        if position_name != 'Завуч':
            logging.error(f"GET /api/teacher/teachers - Access denied for user {username} (not a head teacher)")
            return {"status": "error",
                    "description": "Доступ запрещен: только завуч может просматривать список учителей"}, 403

        db_sess = db_session.create_session()
        try:
            teachers = (db_sess.query(Teacher)
                        .join(User, Teacher.user_id == User.user_id)
                        .outerjoin(Class, Teacher.teacher_id == Class.teacher_id)
                        .filter(Class.teacher_id == None)
                        .options(joinedload(Teacher.user))
                        .all())

            teachers_data = [
                {
                    "teacher_id": teacher.teacher_id,
                    "user_id": teacher.user_id,
                    "username": teacher.user.username,
                    "first_name": teacher.user.first_name,
                    "last_name": teacher.user.last_name,
                    "email": teacher.user.email
                } for teacher in teachers
            ]

            logging.info(f"GET /api/teacher/teachers - Retrieved {len(teachers)} free teachers by user {username}")
            return {
                "status": "success",
                "message": f"Найдено {len(teachers)} свободных учителей",
                "data": teachers_data
            }, 200

        except Exception as e:
            logging.error(f"GET /api/teacher/teachers - Error: {str(e)}")
            return {"status": "error", "description": f"Ошибка при получении списка учителей: {str(e)}"}, 500

        finally:
            db_sess.close()