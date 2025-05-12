from flask_restful import Resource
from data import db_session
from data.student import Student
from data.user import User
from data.grade import Grade
from data.attendance import Attendance
from data.schedule import Schedule
from data.subject import Subject
from data.classes import Class
from data.teacher import Teacher
from decorators.authorization_teacher_decorator import teacher_authorization_required
import logging


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


class ClassTeacherResource(Resource):
    """API для классного руководителя: просмотр информации об учениках и расписании класса."""

    @teacher_authorization_required('/api/teacher/my_class', method='GET')
    def get(self, username, position_name):
        """Получение информации об учениках и расписании класса, где пользователь является классным руководителем."""
        db_sess = db_session.create_session()
        try:
            teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
            if not teacher:
                logging.error(f"GET /api/class_teacher - Teacher {username} not found")
                return {"status": "error", "description": "Учитель не найден"}, 404

            class_ = db_sess.query(Class).filter(Class.teacher_id == teacher.teacher_id).first()
            if not class_:
                logging.error(f"GET /api/class_teacher - No class found for teacher {username}")
                return {"status": "error", "description": "Вы не являетесь классным руководителем ни одного класса"}, 404

            students = db_sess.query(Student).join(User).filter(Student.class_id == class_.class_id).all()
            students_data = [
                {
                    'user_id': student.user_id,
                    'student_id': student.student_id,
                    'first_name': student.user.first_name,
                    'last_name': student.user.last_name,
                    'birth_date': student.birth_date.strftime('%Y-%m-%d') if student.birth_date else None,
                    'address': student.address,
                    'email': student.user.email,
                    'phone_number': student.user.phone_number,
                    'grades': [
                        {
                            'grade_id': grade.grade_id,
                            'subject_id': grade.subject_id,
                            'subject_name': grade.subject.subject_name,
                            'grade': grade.grade,
                            'date': grade.date.strftime('%Y-%m-%d') if grade.date else None
                        }
                        for grade in db_sess.query(Grade).filter(Grade.student_id == student.user_id).all()
                    ],
                    'attendance': [
                        {
                            'attendance_id': record.attendance_id,
                            'date': record.date.strftime('%Y-%m-%d') if record.date else None,
                            'status': record.status
                        }
                        for record in db_sess.query(Attendance).filter(Attendance.student_id == student.user_id).all()
                    ]
                }
                for student in students
            ]

            schedule = db_sess.query(Schedule).join(Subject).filter(Schedule.class_id == class_.class_id).all()
            schedule_data = [
                {
                    'schedule_id': s.schedule_id,
                    'subject_id': s.subject_id,
                    'subject_name': s.subject.subject_name,
                    'teacher_id': s.teacher_id,
                    'teacher_name': f"{s.teacher.user.first_name} {s.teacher.user.last_name}",
                    'day_of_week': s.day_of_week,
                    'start_time': s.start_time,
                    'end_time': s.end_time
                }
                for s in schedule
            ]

            return {
                "status": "success",
                "data": {
                    "class_id": class_.class_id,
                    "class_name": class_.class_name,
                    "students": students_data,
                    "schedule": schedule_data
                }
            }, 200

        finally:
            db_sess.close()