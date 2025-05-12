from flask_restful import Resource
from flask import request
from data import db_session
from data.grade import Grade
from data.homework import Homework
from data.attendance import Attendance
from data.schedule import Schedule
from data.student import Student
from data.subject import Subject
from data.classes import Class
from data.teacher import Teacher
from data.user import User
from decorators.authorization_teacher_decorator import teacher_authorization_required
from datetime import datetime
import logging

logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

def validate_date(date_str):
    """Валидация строки даты в формате YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

class GradeResource(Resource):
    """API для управления оценками (GET, POST, PUT, DELETE)."""

    @teacher_authorization_required('/api/teacher/<int:class_id>/grades', method='GET')
    def get(self, username, position_name, class_id=None):
        """Получение всех оценок для указанного класса."""
        if not class_id:
            logging.error(f"GET /api/grades - Missing class_id parameter for user {username}")
            return {"status": "error", "description": "Не указан class_id"}, 400

        db_sess = db_session.create_session()
        try:
            if not db_sess.query(Class).filter(Class.class_id == class_id).first():
                logging.error(f"GET /api/grades - Class {class_id} not found for user {username}")
                return {"status": "error", "description": "Класс не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"GET /api/grades - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"GET /api/grades - Teacher {username} not authorized for class {class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            grades = db_sess.query(Grade).join(Student).filter(Student.class_id == class_id).all()
            grades_data = [
                {
                    'grade_id': grade.grade_id,
                    'student_id': grade.student_id,
                    'subject_id': grade.subject_id,
                    'grade': grade.grade,
                    'date': grade.date.strftime('%Y-%m-%d') if grade.date else None
                }
                for grade in grades
            ]
            return {"status": "success", "data": grades_data}, 200

        finally:
            db_sess.close()

    @teacher_authorization_required('/api/grades', method='POST')
    def post(self, username, position_name):
        """Добавление новой оценки."""
        data = request.get_json()
        required_fields = ['student_id', 'subject_id', 'grade', 'date']
        if not all(field in data for field in required_fields):
            logging.error(f"POST /api/grades - Missing required fields for user {username}")
            return {"status": "error", "description": "Отсутствуют обязательные поля"}, 400

        if not isinstance(data['grade'], int) or data['grade'] < 2 or data['grade'] > 5:
            logging.error(f"POST /api/grades - Invalid grade value: {data['grade']} for user {username}")
            return {"status": "error", "description": "Оценка должна быть целым числом от 2 до 5"}, 400
        if not validate_date(data['date']):
            logging.error(f"POST /api/grades - Invalid date format: {data['date']} for user {username}")
            return {"status": "error", "description": "Дата должна быть в формате YYYY-MM-DD"}, 400

        db_sess = db_session.create_session()
        try:
            student = db_sess.query(Student).filter(Student.user_id == data['student_id']).first()
            if not student:
                logging.error(f"POST /api/grades - Student {data['student_id']} not found for user {username}")
                return {"status": "error", "description": "Студент не найден"}, 404
            if not db_sess.query(Subject).filter(Subject.subject_id == data['subject_id']).first():
                logging.error(f"POST /api/grades - Subject {data['subject_id']} not found for user {username}")
                return {"status": "error", "description": "Предмет не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"POST /api/grades - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == student.class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"POST /api/grades - Teacher {username} not authorized for class {student.class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            grade = Grade(
                student_id=data['student_id'],
                subject_id=data['subject_id'],
                grade=data['grade'],
                date=datetime.strptime(data['date'], '%Y-%m-%d')
            )
            db_sess.add(grade)
            db_sess.commit()
            logging.info(f"POST /api/grades - Grade added for student {data['student_id']} by {username}")
            grade_data = {
                'grade_id': grade.grade_id,
                'student_id': grade.student_id,
                'subject_id': grade.subject_id,
                'grade': grade.grade,
                'date': grade.date.strftime('%Y-%m-%d') if grade.date else None
            }
            return {"status": "success", "description": "Оценка добавлена", "data": grade_data}, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/grades - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()

    @teacher_authorization_required('/api/grades', method='PUT')
    def put(self, username, position_name):
        """Изменение существующей оценки."""
        data = request.get_json()
        required_fields = ['grade_id', 'student_id', 'subject_id', 'grade', 'date']
        if not all(field in data for field in required_fields):
            logging.error(f"PUT /api/grades - Missing required fields for user {username}")
            return {"status": "error", "description": "Отсутствуют обязательные поля"}, 400

        if not isinstance(data['grade'], int) or data['grade'] < 2 or data['grade'] > 5:
            logging.error(f"PUT /api/grades - Invalid grade value: {data['grade']} for user {username}")
            return {"status": "error", "description": "Оценка должна быть целым числом от 2 до 5"}, 400
        if not validate_date(data['date']):
            logging.error(f"PUT /api/grades - Invalid date format: {data['date']} for user {username}")
            return {"status": "error", "description": "Дата должна быть в формате YYYY-MM-DD"}, 400

        db_sess = db_session.create_session()
        try:
            grade = db_sess.query(Grade).filter(Grade.grade_id == data['grade_id']).first()
            if not grade:
                logging.error(f"PUT /api/grades - Grade {data['grade_id']} not found for user {username}")
                return {"status": "error", "description": "Оценка не найдена"}, 404

            student = db_sess.query(Student).filter(Student.user_id == data['student_id']).first()
            if not student:
                logging.error(f"PUT /api/grades - Student {data['student_id']} not found for user {username}")
                return {"status": "error", "description": "Студент не найден"}, 404
            if not db_sess.query(Subject).filter(Subject.subject_id == data['subject_id']).first():
                logging.error(f"PUT /api/grades - Subject {data['subject_id']} not found for user {username}")
                return {"status": "error", "description": "Предмет не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"PUT /api/grades - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == student.class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"PUT /api/grades - Teacher {username} not authorized for class {student.class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            grade.student_id = data['student_id']
            grade.subject_id = data['subject_id']
            grade.grade = data['grade']
            grade.date = datetime.strptime(data['date'], '%Y-%m-%d')
            db_sess.commit()
            logging.info(f"PUT /api/grades - Grade {data['grade_id']} updated by {username}")
            grade_data = {
                'grade_id': grade.grade_id,
                'student_id': grade.student_id,
                'subject_id': grade.subject_id,
                'grade': grade.grade,
                'date': grade.date.strftime('%Y-%m-%d') if grade.date else None
            }
            return {"status": "success", "description": "Оценка обновлена", "data": grade_data}, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PUT /api/grades - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()

    @teacher_authorization_required('/api/grades', method='DELETE')
    def delete(self, username, position_name, grade_id=None):
        """Удаление оценки."""
        if not grade_id:
            logging.error(f"DELETE /api/grades - Missing grade_id parameter for user {username}")
            return {"status": "error", "description": "Не указан grade_id"}, 400

        db_sess = db_session.create_session()
        try:
            grade = db_sess.query(Grade).filter(Grade.grade_id == grade_id).first()
            if not grade:
                logging.error(f"DELETE /api/grades - Grade {grade_id} not found for user {username}")
                return {"status": "error", "description": "Оценка не найдена"}, 404

            student = db_sess.query(Student).filter(Student.user_id == grade.student_id).first()
            if not student:
                logging.error(f"DELETE /api/grades - Student {grade.student_id} not found for user {username}")
                return {"status": "error", "description": "Студент не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"DELETE /api/grades - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == student.class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"DELETE /api/grades - Teacher {username} not authorized for class {student.class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            db_sess.delete(grade)
            db_sess.commit()
            logging.info(f"DELETE /api/grades - Grade {grade_id} deleted by {username}")
            return {"status": "success", "description": "Оценка удалена"}, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"DELETE /api/grades - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()

class HomeworkResource(Resource):
    """API для управления домашним заданием (GET, POST)."""

    @teacher_authorization_required('/api/homework', method='GET')
    def get(self, username, position_name, class_id=None):
        """Получение всех домашних заданий для указанного класса."""
        if not class_id:
            logging.error(f"GET /api/homework - Missing class_id parameter for user {username}")
            return {"status": "error", "description": "Не указан class_id"}, 400

        db_sess = db_session.create_session()
        try:
            if not db_sess.query(Class).filter(Class.class_id == class_id).first():
                logging.error(f"GET /api/homework - Class {class_id} not found for user {username}")
                return {"status": "error", "description": "Класс не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"GET /api/homework - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"GET /api/homework - Teacher {username} not authorized for class {class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            homeworks = db_sess.query(Homework).filter(Homework.class_id == class_id).all()
            homeworks_data = [
                {
                    'homework_id': homework.homework_id,
                    'subject_id': homework.subject_id,
                    'class_id': homework.class_id,
                    'task': homework.task,
                    'due_date': homework.due_date.strftime('%Y-%m-%d') if homework.due_date else None
                }
                for homework in homeworks
            ]
            return {"status": "success", "data": homeworks_data}, 200

        finally:
            db_sess.close()

    @teacher_authorization_required('/api/homework', method='POST')
    def post(self, username, position_name):
        """Добавление нового домашнего задания."""
        data = request.get_json()
        required_fields = ['subject_id', 'class_id', 'task', 'due_date']
        if not all(field in data for field in required_fields):
            logging.error(f"POST /api/homework - Missing required fields for user {username}")
            return {"status": "error", "description": "Отсутствуют обязательные поля"}, 400

        if not validate_date(data['due_date']):
            logging.error(f"POST /api/homework - Invalid date format: {data['due_date']} for user {username}")
            return {"status": "error", "description": "Дата должна быть в формате YYYY-MM-DD"}, 400

        db_sess = db_session.create_session()
        try:
            if not db_sess.query(Class).filter(Class.class_id == data['class_id']).first():
                logging.error(f"POST /api/homework - Class {data['class_id']} not found for user {username}")
                return {"status": "error", "description": "Класс не найден"}, 404
            if not db_sess.query(Subject).filter(Subject.subject_id == data['subject_id']).first():
                logging.error(f"POST /api/homework - Subject {data['subject_id']} not found for user {username}")
                return {"status": "error", "description": "Предмет не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"POST /api/homework - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == data['class_id'],
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"POST /api/homework - Teacher {username} not authorized for class {data['class_id']}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            homework = Homework(
                subject_id=data['subject_id'],
                class_id=data['class_id'],
                task=data['task'],
                due_date=datetime.strptime(data['due_date'], '%Y-%m-%d')
            )
            db_sess.add(homework)
            db_sess.commit()
            logging.info(f"POST /api/homework - Homework added for class {data['class_id']} by {username}")
            homework_data = {
                'homework_id': homework.homework_id,
                'subject_id': homework.subject_id,
                'class_id': homework.class_id,
                'task': homework.task,
                'due_date': homework.due_date.strftime('%Y-%m-%d') if homework.due_date else None
            }
            return {"status": "success", "description": "Домашнее задание добавлено", "data": homework_data}, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/homework - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()

class AttendanceResource(Resource):
    """API для управления посещаемостью (GET, POST, PUT)."""

    @teacher_authorization_required('/api/attendance', method='GET')
    def get(self, username, position_name, class_id=None):
        """Получение всех записей посещаемости для указанного класса."""
        if not class_id:
            logging.error(f"GET /api/attendance - Missing class_id parameter for user {username}")
            return {"status": "error", "description": "Не указан class_id"}, 400

        db_sess = db_session.create_session()
        try:
            if not db_sess.query(Class).filter(Class.class_id == class_id).first():
                logging.error(f"GET /api/attendance - Class {class_id} not found for user {username}")
                return {"status": "error", "description": "Класс не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"GET /api/attendance - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"GET /api/attendance - Teacher {username} not authorized for class {class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            attendance = db_sess.query(Attendance).join(Student).filter(Student.class_id == class_id).all()
            attendance_data = [
                {
                    'attendance_id': record.attendance_id,
                    'student_id': record.student_id,
                    'date': record.date.strftime('%Y-%m-%d') if record.date else None,
                    'status': record.status
                }
                for record in attendance
            ]
            return {"status": "success", "data": attendance_data}, 200

        finally:
            db_sess.close()

    @teacher_authorization_required('/api/attendance', method='POST')
    def post(self, username, position_name):
        """Добавление новой записи посещаемости."""
        data = request.get_json()
        required_fields = ['student_id', 'date', 'status']
        if not all(field in data for field in required_fields):
            logging.error(f"POST /api/attendance - Missing required fields for user {username}")
            return {"status": "error", "description": "Отсутствуют обязательные поля"}, 400

        if data['status'] not in ['присутствовал', 'отсутствовал']:
            logging.error(f"POST /api/attendance - Invalid status: {data['status']} for user {username}")
            return {"status": "error", "description": "Статус должен быть 'присутствовал' или 'отсутствовал'"}, 400
        if not validate_date(data['date']):
            logging.error(f"POST /api/attendance - Invalid date format: {data['date']} for user {username}")
            return {"status": "error", "description": "Дата должна быть в формате YYYY-MM-DD"}, 400

        db_sess = db_session.create_session()
        try:
            student = db_sess.query(Student).filter(Student.user_id == data['student_id']).first()
            if not student:
                logging.error(f"POST /api/attendance - Student {data['student_id']} not found for user {username}")
                return {"status": "error", "description": "Студент не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"POST /api/attendance - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == student.class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"POST /api/attendance - Teacher {username} not authorized for class {student.class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            attendance = Attendance(
                student_id=data['student_id'],
                date=datetime.strptime(data['date'], '%Y-%m-%d'),
                status=data['status']
            )
            db_sess.add(attendance)
            db_sess.commit()
            logging.info(f"POST /api/attendance - Attendance added for student {data['student_id']} by {username}")
            attendance_data = {
                'attendance_id': attendance.attendance_id,
                'student_id': attendance.student_id,
                'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else None,
                'status': attendance.status
            }
            return {"status": "success", "description": "Запись посещаемости добавлена", "data": attendance_data}, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/attendance - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()

    @teacher_authorization_required('/api/attendance', method='PUT')
    def put(self, username, position_name):
        """Изменение существующей записи посещаемости."""
        data = request.get_json()
        required_fields = ['attendance_id', 'student_id', 'date', 'status']
        if not all(field in data for field in required_fields):
            logging.error(f"PUT /api/attendance - Missing required fields for user {username}")
            return {"status": "error", "description": "Отсутствуют обязательные поля"}, 400

        if data['status'] not in ['присутствовал', 'отсутствовал']:
            logging.error(f"PUT /api/attendance - Invalid status: {data['status']} for user {username}")
            return {"status": "error", "description": "Статус должен быть 'присутствовал' или 'отсутствовал'"}, 400
        if not validate_date(data['date']):
            logging.error(f"PUT /api/attendance - Invalid date format: {data['date']} for user {username}")
            return {"status": "error", "description": "Дата должна быть в формате YYYY-MM-DD"}, 400

        db_sess = db_session.create_session()
        try:
            attendance = db_sess.query(Attendance).filter(Attendance.attendance_id == data['attendance_id']).first()
            if not attendance:
                logging.error(f"PUT /api/attendance - Attendance {data['attendance_id']} not found for user {username}")
                return {"status": "error", "description": "Запись посещаемости не найдена"}, 404

            student = db_sess.query(Student).filter(Student.user_id == data['student_id']).first()
            if not student:
                logging.error(f"PUT /api/attendance - Student {data['student_id']} not found for user {username}")
                return {"status": "error", "description": "Студент не найден"}, 404

            if position_name != "Завуч":
                teacher = db_sess.query(Teacher).join(User).filter(User.username == username).first()
                if not teacher:
                    logging.error(f"PUT /api/attendance - Teacher {username} not found")
                    return {"status": "error", "description": "Учитель не найден"}, 404
                teacher_schedule = db_sess.query(Schedule).filter(
                    Schedule.class_id == student.class_id,
                    Schedule.teacher_id == teacher.teacher_id
                ).first()
                if not teacher_schedule:
                    logging.error(f"PUT /api/attendance - Teacher {username} not authorized for class {student.class_id}")
                    return {"status": "error", "description": "Нет доступа к этому классу"}, 403

            attendance.student_id = data['student_id']
            attendance.date = datetime.strptime(data['date'], '%Y-%m-%d')
            attendance.status = data['status']
            db_sess.commit()
            logging.info(f"PUT /api/attendance - Attendance {data['attendance_id']} updated by {username}")
            attendance_data = {
                'attendance_id': attendance.attendance_id,
                'student_id': attendance.student_id,
                'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else None,
                'status': attendance.status
            }
            return {"status": "success", "description": "Запись посещаемости обновлена", "data": attendance_data}, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PUT /api/attendance - Error: {str(e)} for user {username}")
            return {"status": "error", "description": f"Ошибка: {str(e)}"}, 500
        finally:
            db_sess.close()