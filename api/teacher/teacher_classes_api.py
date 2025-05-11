from flask_restful import Resource, reqparse
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from data import db_session
from data.classes import Class
from data.schedule import Schedule
from data.student import Student
from data.user import User
from data.homework import Homework
from data.grade import Grade
from data.attendance import Attendance
from data.teacher import Teacher
from decorators.authorization_teacher_decorator import teacher_authorization_required
import logging
import base64
from datetime import datetime


logging.basicConfig(
    filename='api_access.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


def parse_date(value):
    """Функция для парсинга даты"""
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Incorrect date format. Use YYYY-MM-DD")


class TeacherClassesAPI(Resource):
    """Класс для API управления классами"""
    class_post_parser = reqparse.RequestParser()
    class_post_parser.add_argument('class_name', type=str, required=True, help="Class name is required")
    class_post_parser.add_argument('teacher_id', type=int, required=True, help="Teacher ID is required")
    class_post_parser.add_argument('students', type=dict, action='append', required=False, help="List of students")

    class_patch_parser = reqparse.RequestParser()
    class_patch_parser.add_argument('students', type=dict, action='append', required=True, help="List of students is required")

    @teacher_authorization_required("/api/teacher/classes", method="GET")
    def get(self, username=None, position_name=None):
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.username == username).first()
            if not user or not user.teacher:
                logging.error(f"GET /api/teacher/classes - User {username} is not a teacher")
                return {"status": "error", "description": "Пользователь не является учителем"}, 403

            if position_name == 'Завуч':
                classes = (db_sess.query(Class)
                           .options(joinedload(Class.teacher))
                           .all())
            else:  # Предметник
                classes = (db_sess.query(Class)
                           .join(Schedule, Class.class_id == Schedule.class_id)
                           .filter(Schedule.teacher_id == user.teacher.teacher_id)
                           .distinct()
                           .all())

            classes_data = [
                {
                    "class_id": cls.class_id,
                    "class_name": cls.class_name,
                } for cls in classes
            ]
            logging.info(
                f"GET /api/teacher/classes - Retrieved {len(classes)} classes by user {username} (role: {position_name})")
            return {
                "status": "success",
                "message": f"Найдено {len(classes)} классов",
                "data": classes_data,
                "teacher_role": position_name
            }, 200

        except Exception as e:
            logging.error(f"GET /api/teacher/classes - Error: {str(e)}")
            return {"status": "error", "description": f"Ошибка при получении классов: {str(e)}"}, 500

        finally:
            db_sess.close()

    @teacher_authorization_required("/api/teacher/classes", method="POST")
    def post(self, username=None, position_name=None):
        if position_name != 'Завуч':
            logging.error(f"POST /api/teacher/classes - Access denied for user {username} (not a head teacher)")
            return {"status": "error", "description": "Доступ запрещен: только завуч может создавать классы"}, 403

        db_sess = db_session.create_session()
        try:
            args = self.class_post_parser.parse_args()
            class_name = args['class_name']
            teacher_id = args['teacher_id']
            students = args.get('students', [])

            teacher = db_sess.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
            if not teacher:
                return {"status": "error", "description": f"Учитель с ID {teacher_id} не найден"}, 404

            if db_sess.query(Class).filter(Class.class_name == class_name).first():
                return {"status": "error", "description": f"Класс с именем {class_name} уже существует"}, 400

            new_class = Class(class_name=class_name, teacher_id=teacher_id)
            db_sess.add(new_class)
            db_sess.flush()

            max_student_id = db_sess.query(func.max(Student.student_id)).scalar() or 0
            with open('static/images/base.png', 'rb') as f:
                base_picture = base64.b64encode(f.read()).decode('utf-8')

            for student_data in students:
                required_fields = ['username', 'first_name', 'last_name', 'email', 'password']
                for field in required_fields:
                    if field not in student_data or not student_data[field]:
                        return {"status": "error", "description": f"Поле {field} обязательно для студента"}, 400

                if db_sess.query(User).filter(
                        (User.username == student_data['username']) | (User.email == student_data['email'])
                ).first():
                    return {"status": "error",
                            "description": f"Пользователь с username {student_data['username']} или email {student_data['email']} уже существует"}, 400

                birth_date = None
                if student_data.get('birth_date'):
                    try:
                        birth_date = parse_date(student_data['birth_date'])
                    except ValueError:
                        return {"status": "error",
                                "description": "Неверный формат birth_date. Используйте YYYY-MM-DD"}, 400

                new_user = User(
                    username=student_data['username'],
                    first_name=student_data['first_name'],
                    last_name=student_data['last_name'],
                    email=student_data['email'],
                    phone_number=student_data.get('phone_number'),
                    profile_picture=student_data.get('profile_picture', base_picture)
                )
                new_user.set_password(student_data['password'])
                new_user.generate_api_key()
                db_sess.add(new_user)
                db_sess.flush()

                max_student_id += 1
                new_student = Student(
                    user_id=new_user.user_id,
                    student_id=max_student_id,
                    class_id=new_class.class_id,
                    birth_date=birth_date,
                    address=student_data.get('address')
                )
                db_sess.add(new_student)

            db_sess.commit()
            logging.info(
                f"POST /api/teacher/classes - Class {class_name} created by user {username} with {len(students)} students")
            return {
                "status": "success",
                "message": f"Класс {class_name} успешно создан",
                "data": {
                    "class_id": new_class.class_id,
                    "class_name": new_class.class_name,
                    "teacher_id": new_class.teacher_id,
                    "students_count": len(students)
                }
            }, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/teacher/classes - Error: {str(e)}")
            return {"status": "error", "description": f"Ошибка при создании класса: {str(e)}"}, 500

        finally:
            db_sess.close()

    @teacher_authorization_required("/api/teacher/classes/<class_id>", method="PATCH")
    def patch(self, class_id, username=None, position_name=None):
        if position_name != 'Завуч':
            logging.error(
                f"PATCH /api/teacher/classes/{class_id} - Access denied for user {username} (not a head teacher)")
            return {"status": "error",
                    "description": "Доступ запрещен: только завуч может добавлять учеников в класс"}, 403

        db_sess = db_session.create_session()
        try:
            class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
            if not class_:
                logging.error(f"PATCH /api/teacher/classes/{class_id} - Class not found by user {username}")
                return {"status": "error", "description": f"Класс с ID {class_id} не найден"}, 404

            args = self.class_patch_parser.parse_args()
            students = args['students']
            logging.debug(f"PATCH /api/teacher/classes/{class_id} - Received student data: {students}")

            max_student_id = db_sess.query(func.max(Student.student_id)).scalar() or 0
            with open('static/images/base.png', 'rb') as f:
                base_picture = base64.b64encode(f.read()).decode('utf-8')

            for student_data in students:
                required_fields = ['username', 'first_name', 'last_name', 'email', 'password']
                for field in required_fields:
                    if field not in student_data or not student_data[field]:
                        logging.error(f"PATCH /api/teacher/classes/{class_id} - Missing required field: {field}")
                        return {"status": "error", "description": f"Поле {field} обязательно для студента"}, 400

                if db_sess.query(User).filter(
                        (User.username == student_data['username']) | (User.email == student_data['email'])
                ).first():
                    logging.error(
                        f"PATCH /api/teacher/classes/{class_id} - User already exists: {student_data['username']}")
                    return {"status": "error",
                            "description": f"Пользователь с username {student_data['username']} или email {student_data['email']} уже существует"}, 400

                birth_date = None
                if student_data.get('birth_date'):
                    try:
                        birth_date = parse_date(student_data['birth_date'])
                    except ValueError:
                        logging.error(
                            f"PATCH /api/teacher/classes/{class_id} - Invalid birth_date format: {student_data['birth_date']}")
                        return {"status": "error",
                                "description": "Неверный формат birth_date. Используйте YYYY-MM-DD"}, 400

                new_user = User(
                    username=student_data['username'],
                    first_name=student_data['first_name'],
                    last_name=student_data['last_name'],
                    email=student_data['email'],
                    phone_number=student_data.get('phone_number'),
                    profile_picture=student_data.get('profile_picture', base_picture)
                )
                new_user.set_password(student_data['password'])
                new_user.generate_api_key()
                db_sess.add(new_user)
                db_sess.flush()

                max_student_id += 1
                new_student = Student(
                    user_id=new_user.user_id,
                    student_id=max_student_id,
                    class_id=class_.class_id,
                    birth_date=birth_date,
                    address=student_data.get('address')
                )
                db_sess.add(new_student)

            db_sess.commit()
            logging.info(
                f"PATCH /api/teacher/classes/{class_id} - Added {len(students)} students to class {class_id} by user {username}")
            return {
                "status": "success",
                "message": f"Успешно добавлено {len(students)} учеников в класс {class_.class_name}",
                "data": {
                    "class_id": class_.class_id,
                    "class_name": class_.class_name,
                    "students_added": len(students)
                }
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PATCH /api/teacher/classes/{class_id} - Error: {str(e)}")
            return {"status": "error", "description": f"Ошибка при добавлении учеников: {str(e)}"}, 500

        finally:
            db_sess.close()

    @teacher_authorization_required("/api/teacher/classes/<class_id>", method="DELETE")
    def delete(self, class_id, username=None, position_name=None):
        if position_name != 'Завуч':
            logging.error(
                f"DELETE /api/teacher/classes/{class_id} - Access denied for user {username} (not a head teacher)")
            return {"status": "error", "description": "Доступ запрещен: только завуч может удалять классы"}, 403

        db_sess = db_session.create_session()
        try:
            class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
            if not class_:
                logging.error(f"DELETE /api/teacher/classes/{class_id} - Class not found by user {username}")
                return {"status": "error", "description": f"Класс с ID {class_id} не найден"}, 404

            logging.debug(f"Starting deletion of class {class_id} with name {class_.class_name}")

            students = db_sess.query(Student).filter(Student.class_id == class_id).all()
            user_ids = [student.user_id for student in students]

            logging.debug(f"Found {len(students)} students to delete for class {class_id}")

            if user_ids:
                logging.debug(f"Deleting grades and attendance for user_ids: {user_ids}")
                db_sess.query(Grade).filter(Grade.student_id.in_(user_ids)).delete(synchronize_session=False)
                db_sess.query(Attendance).filter(Attendance.student_id.in_(user_ids)).delete(synchronize_session=False)

                logging.debug(f"Deleting students of class {class_id}")
                db_sess.query(Student).filter(Student.class_id == class_id).delete(synchronize_session=False)

                logging.debug(f"Deleting users for user_ids: {user_ids}")
                db_sess.query(User).filter(User.user_id.in_(user_ids)).delete(synchronize_session=False)

            logging.debug(f"Deleting students of class {class_id}")
            db_sess.query(Student).filter(Student.class_id == class_id).delete(synchronize_session=False)

            logging.debug(f"Deleting schedule and homework for class {class_id}")
            db_sess.query(Schedule).filter(Schedule.class_id == class_id).delete(synchronize_session=False)
            db_sess.query(Homework).filter(Homework.class_id == class_id).delete(synchronize_session=False)

            logging.debug(f"Deleting class {class_id}")
            db_sess.delete(class_)

            db_sess.commit()
            logging.info(f"DELETE /api/teacher/classes/{class_id} - Class {class_id} deleted by user {username}")
            return {
                "status": "success",
                "message": f"Класс {class_id} и все связанные записи успешно удалены"
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"DELETE /api/teacher/classes/{class_id} - Error: {str(e)}")
            return {"status": "error", "description": f"Ошибка при удалении класса: {str(e)}"}, 500

        finally:
            db_sess.close()