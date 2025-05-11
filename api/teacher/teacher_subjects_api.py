from flask_restful import Resource
from data import db_session
from data.subject import Subject
from data.schedule import Schedule
from data.teacher import Teacher
from data.user import User
from data.teacher_position import TeacherPosition
from data.teacher_position_assignment import TeacherPositionAssignment
from decorators.authorization_teacher_decorator import teacher_authorization_required
import logging

logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

class TeacherSubjectsAPI(Resource):
    """Класс для API получения списка предметов для учителя по классу"""

    @teacher_authorization_required("/api/teacher/class/<class_id>/subjects", method="GET")
    def get(self, class_id, username=None, position_name=None):
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.username == username).first()
            if not user or not user.teacher:
                logging.error(f"GET /api/teacher/class/{class_id}/subjects - User {username} is not a teacher")
                return {"status": "error", "description": "Пользователь не является учителем"}, 403

            is_head_teacher = False
            teacher = db_sess.query(Teacher).filter(Teacher.user_id == user.user_id).first()
            if teacher:
                position = db_sess.query(TeacherPosition).join(TeacherPositionAssignment).filter(
                    TeacherPositionAssignment.teacher_id == teacher.teacher_id,
                    TeacherPosition.position_name == 'Завуч'
                ).first()
                is_head_teacher = bool(position)

            if is_head_teacher:
                subjects = (db_sess.query(Subject)
                            .join(Schedule, Schedule.subject_id == Subject.subject_id)
                            .filter(Schedule.class_id == class_id)
                            .distinct()
                            .all())
            else:
                subjects = (db_sess.query(Subject)
                            .join(Schedule, Schedule.subject_id == Subject.subject_id)
                            .filter(Schedule.class_id == class_id,
                                    Schedule.teacher_id == user.teacher.teacher_id)
                            .distinct()
                            .all())

            subjects_data = [
                {
                    "subject_id": subject.subject_id,
                    "subject_name": subject.subject_name
                } for subject in subjects
            ]

            logging.info(f"GET /api/teacher/class/{class_id}/subjects - Retrieved {len(subjects)} subjects by user {username}")
            return {
                "status": "success",
                "message": f"Найдено {len(subjects)} предметов",
                "data": subjects_data
            }, 200

        except Exception as e:
            logging.error(f"GET /api/teacher/class/{class_id}/subjects - Error: {str(e)}")
            return {"status": "error", "description": f"Ошибка при получении предметов: {str(e)}"}, 500

        finally:
            db_sess.close()