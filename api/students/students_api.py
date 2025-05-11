from flask_restful import Resource
import logging
from data import db_session
from data.student import Student
from data.user import User
from data.schedule import Schedule
from data.subject import Subject
from data.grade import Grade
from data.attendance import Attendance
from data.homework import Homework
from decorators.autorization_student_decorator import student_authorization_required
from sqlalchemy import case


class StudentScheduleResource(Resource):
    """API для получения расписания уроков студента по student_id через class_id."""

    @student_authorization_required('/api/student/schedule', method='GET')
    def get(self, username):
        """Получение расписания уроков для студента, сортировка по дню недели."""
        db_sess = db_session.create_session()
        try:
            # Находим студента
            student = db_sess.query(Student).join(User).filter(User.username == username).first()
            if not student:
                logging.error(f"GET /api/student/schedule - Student {username} not found")
                return {"status": "error", "description": "Студент не найден"}, 404

            # Определяем порядок дней недели
            day_order = {
                'Понедельник': 1,
                'Вторник': 2,
                'Среда': 3,
                'Четверг': 4,
                'Пятница': 5,
                'Суббота': 6,
                'Воскресенье': 7
            }

            # Получение расписания для класса студента с сортировкой по дню недели и subject_id
            schedule = (
                db_sess.query(Schedule)
                .join(Subject)
                .filter(Schedule.class_id == student.class_id)
                .order_by(
                    case(day_order, value=Schedule.day_of_week),
                    Schedule.subject_id
                )
                .all()
            )
            if not schedule:
                logging.info(f"GET /api/student/schedule - No schedule found for class_id {student.class_id}")
                return {"status": "success", "data": {"schedule": []}}, 200

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
                    "class_id": student.class_id,
                    "schedule": schedule_data
                }
            }, 200

        finally:
            db_sess.close()


class StudentGradesAttendanceResource(Resource):
    """API для получения оценок и посещаемости студента по предмету."""

    @student_authorization_required('/api/student/grades_attendance', method='GET')
    def get(self, username, subject_id):
        """Получение оценок, посещаемости и среднего балла по subject_id для студента."""
        db_sess = db_session.create_session()
        try:
            # Находим студента
            student = db_sess.query(Student).join(User).filter(User.username == username).first()
            if not student:
                logging.error(f"GET /api/student/grades_attendance - Student {username} not found")
                return {"status": "error", "description": "Студент не найден"}, 404

            # Проверяем существование предмета
            subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
            if not subject:
                logging.error(f"GET /api/student/grades_attendance - Subject {subject_id} not found")
                return {"status": "error", "description": "Предмет не найден"}, 404

            # Получение оценок
            grades = (
                db_sess.query(Grade)
                .filter(Grade.student_id == student.user_id, Grade.subject_id == subject_id)
                .all()
            )
            grades_data = [
                {
                    'grade_id': g.grade_id,
                    'grade': g.grade,
                    'date': g.date.strftime('%Y-%m-%d') if g.date else None
                }
                for g in grades
            ]

            # Расчет среднего балла
            average_grade = None
            if grades:
                average_grade = sum(g.grade for g in grades) / len(grades)
                average_grade = round(average_grade, 2)  # Округляем до 2 знаков после запятой

            # Получение посещаемости
            attendance = (
                db_sess.query(Attendance)
                .filter(Attendance.student_id == student.user_id)
                .all()
            )
            attendance_data = [
                {
                    'attendance_id': a.attendance_id,
                    'date': a.date.strftime('%Y-%m-%d') if a.date else None,
                    'status': a.status
                }
                for a in attendance
            ]

            return {
                "status": "success",
                "data": {
                    "student_id": student.student_id,
                    "subject_id": subject_id,
                    "subject_name": subject.subject_name,
                    "grades": grades_data,
                    "average_grade": average_grade,
                    "attendance": attendance_data
                }
            }, 200

        finally:
            db_sess.close()


class StudentHomeworkResource(Resource):
    """API для получения домашнего задания по class_id."""

    @student_authorization_required('/api/student/homework', method='GET')
    def get(self, username):
        """Получение домашнего задания для класса студента."""
        db_sess = db_session.create_session()
        try:
            # Находим студента
            student = db_sess.query(Student).join(User).filter(User.username == username).first()
            if not student:
                logging.error(f"GET /api/student/homework - Student {username} not found")
                return {"status": "error", "description": "Студент не найден"}, 404

            # Получение домашнего задания для класса
            homeworks = (
                db_sess.query(Homework)
                .join(Subject)
                .filter(Homework.class_id == student.class_id)
                .all()
            )
            if not homeworks:
                logging.info(f"GET /api/student/homework - No homework found for class_id {student.class_id}")
                return {"status": "success", "data": {"homeworks": []}}, 200

            homework_data = [
                {
                    'homework_id': h.homework_id,
                    'subject_id': h.subject_id,
                    'subject_name': h.subject.subject_name,
                    'task': h.task,
                    'due_date': h.due_date.strftime('%Y-%m-%d') if h.due_date else None
                }
                for h in homeworks
            ]

            return {
                "status": "success",
                "data": {
                    "class_id": student.class_id,
                    "homeworks": homework_data
                }
            }, 200

        finally:
            db_sess.close()


class ClassmatesResource(Resource):
    """API для получения списка одноклассников студента."""

    @student_authorization_required('/api/student/classmates', method='GET')
    def get(self, username):
        """Получение списка одноклассников (имя, фамилия, телефон, email) для студента."""
        db_sess = db_session.create_session()
        try:
            # Находим текущего студента
            current_student = db_sess.query(Student).join(User).filter(User.username == username).first()
            if not current_student:
                logging.error(f"GET /api/student/classmates - Student {username} not found")
                return {"status": "error", "description": "Студент не найден"}, 404

            # Получаем всех студентов из того же класса, исключая текущего
            classmates = (
                db_sess.query(Student)
                .join(User)
                .filter(Student.class_id == current_student.class_id, Student.user_id != current_student.user_id)
                .all()
            )

            classmates_data = [
                {
                    'user_id': student.user_id,
                    'first_name': student.user.first_name,
                    'last_name': student.user.last_name,
                    'phone_number': student.user.phone_number,
                    'email': student.user.email
                }
                for student in classmates
            ]

            return {
                "status": "success",
                "data": {
                    "class_id": current_student.class_id,
                    "classmates": classmates_data
                }
            }, 200

        finally:
            db_sess.close()
