# teacher/teacher_schedule_api.py
from flask_restful import Resource
from flask import request
from data import db_session
from data.schedule import Schedule
from data.subject import Subject
from data.classes import Class
from data.teacher import Teacher
from data.user import User
from decorators.authorization_teacher_decorator import teacher_authorization_required
import logging

logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

# Определяем порядок дней недели
DAY_ORDER = {
    'Понедельник': 1,
    'Вторник': 2,
    'Среда': 3,
    'Четверг': 4,
    'Пятница': 5,
    'Суббота': 6,
    'Воскресенье': 7
}

class TeacherScheduleResource(Resource):
    """API для получения расписания учителя."""

    @teacher_authorization_required('/api/teacher_schedule', method='GET')
    def get(self, username, position_name):
        """Получение расписания уроков учителя, отсортированного по дню недели и времени."""
        db_sess = db_session.create_session()
        try:
            # Находим учителя
            teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
            if not teacher:
                logging.error(f"GET /api/teacher_schedule - Teacher {username} not found")
                return {"status": "error", "description": "Учитель не найден"}, 404

            # Получение расписания учителя
            schedule = db_sess.query(Schedule).join(Subject).join(Class).filter(Schedule.teacher_id == teacher.teacher_id).all()
            schedule_data = [
                {
                    'schedule_id': s.schedule_id,
                    'class_id': s.class_id,
                    'class_name': s.class_.class_name,
                    'subject_id': s.subject_id,
                    'subject_name': s.subject.subject_name,
                    'day_of_week': s.day_of_week,
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'day_order': DAY_ORDER.get(s.day_of_week, 8)  # Для неизвестных дней
                }
                for s in schedule
            ]

            # Сортировка по дню недели и времени начала
            schedule_data.sort(key=lambda x: (x['day_order'], x['start_time']))

            return {
                "status": "success",
                "data": {
                    "teacher_id": teacher.teacher_id,
                    "schedule": schedule_data
                }
            }, 200

        finally:
            db_sess.close()