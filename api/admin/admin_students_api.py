from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from data import db_session
from data.student import Student
from data.user import User
from data.classes import Class
from flask_restful import Resource, reqparse, abort
from flask import request
from decorators.authorization_admin_decorator import admin_authorization_required
import logging
import base64


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


def parse_date(value):
    """Функция для парсинга даты"""
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Incorrect date format. Use YYYY-MM-DD")


class AdminOneStudentAPI(Resource):
    """Класс для api одного студента"""
    one_student_patch = reqparse.RequestParser()
    one_student_patch.add_argument('username', type=str)
    one_student_patch.add_argument('password', type=str)
    one_student_patch.add_argument('first_name', type=str)
    one_student_patch.add_argument('last_name', type=str)
    one_student_patch.add_argument('email', type=str)
    one_student_patch.add_argument('phone_number', type=str)
    one_student_patch.add_argument('profile_picture', type=str)
    one_student_patch.add_argument('class_id', type=str)
    one_student_patch.add_argument('birth_date', type=str)
    one_student_patch.add_argument('address', type=str)

    one_student_post = reqparse.RequestParser()
    one_student_post.add_argument('username', type=str, required=True)
    one_student_post.add_argument('password', type=str, required=True)
    one_student_post.add_argument('first_name', type=str, required=True)
    one_student_post.add_argument('last_name', type=str, required=True)
    one_student_post.add_argument('email', type=str, required=True)
    one_student_post.add_argument('phone_number', type=str, required=True)
    one_student_post.add_argument('class_id', type=str, required=True)
    one_student_post.add_argument('birth_date', type=str, required=True)
    one_student_post.add_argument('address', type=str, required=True)

    @admin_authorization_required("/api/admin/student/<student_id>", method="GET")
    def get(self, student_id, username=None):
        db_sess = db_session.create_session()
        try:
            logging.info(f"Fetching student with student_id={student_id} for user={username}")
            student = (db_sess.query(Student)
                       .options(joinedload(Student.user))
                       .options(joinedload(Student.class_))
                       .options(joinedload(Student.grades))
                       .options(joinedload(Student.attendance))
                       .filter(Student.student_id == student_id)
                       .first())

            if not student:
                logging.error(f"GET /api/admin/student/{student_id} - Not found for user {username}")
                return {'description': 'Not found'}, 404

            logging.info(
                f"Student found: student_id={student_id}, user_id={student.user_id}, class_id={student.class_id}")
            if not student.user:
                logging.error(f"Student {student_id} has no associated User")
                return {'description': 'Ошибка: у студента отсутствуют данные пользователя.'}, 500
            if not student.class_:
                logging.error(f"Student {student_id} has no associated Class")
                return {'description': 'Ошибка: у студента отсутствует класс.'}, 500

            birth_date = str(student.birth_date) if student.birth_date else None
            grades = [
                grade.to_dict(only=('grade_id', 'subject_id', 'grade', 'date'))
                for grade in student.grades
            ]
            attendance = [
                attendance.to_dict(only=('attendance_id', 'date', 'status'))
                for attendance in student.attendance
            ]

            student_data = {
                'Student': {
                    'user_id': student.user_id,
                    'student_id': student.student_id,
                    'username': student.user.username,
                    'first_name': student.user.first_name,
                    'last_name': student.user.last_name,
                    'email': student.user.email,
                    'phone_number': student.user.phone_number,
                    'profile_picture': student.user.profile_picture,
                    'api_key': student.user.api_key,
                    'class': {
                        'class_id': student.class_.class_id,
                        'class_name': student.class_.class_name,
                        'teacher_id': student.class_.teacher_id
                    },
                    'birth_date': birth_date,
                    'address': student.address,
                    'grades': grades,
                    'attendance': attendance
                }
            }
            logging.info(f"GET /api/admin/student/{student_id} - Retrieved by user {username}: {student_data}")
            return student_data, 200

        except Exception as e:
            logging.error(f"GET /api/admin/student/{student_id} - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных студента: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/student", method="POST")
    def post(self, username=None, update_data=None):
        db_sess = db_session.create_session()
        try:
            if update_data is not None:
                username_student = update_data.get('username')
                password = update_data.get('password')
                first_name = update_data.get('first_name')
                last_name = update_data.get('last_name')
                email = update_data.get('email')
                phone_number = update_data.get('phone_number')
                class_id = update_data.get('class_id')
                birth_date = update_data.get('birth_date')
                address = update_data.get('address')
                profile_picture = update_data.get('profile_picture')

                required_fields = {
                    'username': username_student,
                    'password': password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone_number': phone_number,
                    'class_id': class_id,
                    'birth_date': birth_date,
                    'address': address
                }
                for field_name, field_value in required_fields.items():
                    if not field_value:
                        return {'description': f'Field {field_name} is required'}, 400

                try:
                    class_id = int(class_id)
                except ValueError:
                    return {'description': 'class_id must be an integer'}, 400

                birth_date = parse_date(birth_date)

            else:
                content_type = request.headers.get('Content-Type', '')
                if 'multipart/form-data' in content_type:
                    data = request.form
                    username_student = data.get('username')
                    password = data.get('password')
                    first_name = data.get('first_name')
                    last_name = data.get('last_name')
                    email = data.get('email')
                    phone_number = data.get('phone_number')
                    class_id = data.get('class_id')
                    birth_date = data.get('birth_date')
                    address = data.get('address')
                    profile_picture = None

                    if 'profile_picture' in request.files:
                        file = request.files['profile_picture']
                        if file and file.filename:
                            file_content = file.read()
                            profile_picture = base64.b64encode(file_content).decode('utf-8')

                    required_fields = ['username', 'password', 'first_name', 'last_name', 'email', 'phone_number',
                                       'class_id', 'birth_date', 'address']
                    for field in required_fields:
                        if not data.get(field):
                            return {'description': f'Field {field} is required'}, 400

                    try:
                        class_id = int(class_id)
                    except ValueError:
                        return {'description': 'class_id must be an integer'}, 400

                    birth_date = parse_date(birth_date)

                else:
                    try:
                        args = self.one_student_post.parse_args()
                        username_student = args['username']
                        password = args['password']
                        first_name = args['first_name']
                        last_name = args['last_name']
                        email = args['email']
                        phone_number = args['phone_number']
                        class_id = args['class_id']
                        birth_date = parse_date(args['birth_date'])
                        address = args['address']
                        profile_picture = args.get('profile_picture')
                    except Exception as e:
                        return {'description': f'Validation error: {str(e)}'}, 400

            class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
            if not class_:
                return {'description': f'Class with class_id {class_id} does not exist'}, 400

            existing_user = db_sess.query(User).filter(
                (User.username == username_student) | (User.email == email)
            ).first()
            if existing_user:
                return {'description': 'User with this username or email already exists'}, 400

            max_student_id = db_sess.query(func.max(Student.student_id)).scalar() or 0
            new_student_id = max_student_id + 1

            with open('static/images/base.png', 'rb') as f:
                file_content = f.read()
                base_picture = base64.b64encode(file_content).decode('utf-8')

            new_user = User(
                username=username_student,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                profile_picture=profile_picture if profile_picture else base_picture
            )
            new_user.set_password(password)
            new_user.generate_api_key()
            db_sess.add(new_user)
            db_sess.flush()

            new_student = Student(
                user_id=new_user.user_id,
                student_id=new_student_id,
                class_id=class_id,
                birth_date=birth_date,
                address=address
            )
            db_sess.add(new_student)
            db_sess.commit()

            classes = {'class_id': class_.class_id, 'class_name': class_.class_name}
            logging.info(f"POST /api/admin/student - Student {new_student.student_id} created by user {username}")
            return {
                'message': 'Студент успешно создан.',
                'student': {
                    'user_id': new_user.user_id,
                    'student_id': new_student.student_id,
                    'username': new_user.username,
                    'email': new_user.email,
                    'api_key': new_user.api_key,
                    'class': classes,
                    'birth_date': str(new_student.birth_date)
                }
            }, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/admin/student - Error: {str(e)}")
            return {'description': f"Ошибка при создании студента: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/student/<student_id>", method="PATCH")
    def patch(self, student_id, username=None, update_data=None):
        db_sess = db_session.create_session()
        try:
            student = (db_sess.query(Student)
                       .options(joinedload(Student.user))
                       .options(joinedload(Student.class_))
                       .filter(Student.student_id == student_id)
                       .first())

            if not student:
                logging.error(f"PATCH /api/admin/student/{student_id} - Not found for user {username}")
                return {'description': f'Ученик {student_id} не найден.'}, 404

            if not student.user:
                logging.error(f"Student {student_id} has no associated User")
                return {'description': "Ошибка: у студента отсутствуют данные пользователя."}, 500

            if update_data is not None:
                args = update_data
            else:
                content_type = request.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    args = self.one_student_patch.parse_args()
                elif 'multipart/form-data' in content_type:
                    args = {}
                    for key in request.form:
                        args[key] = request.form[key]
                    if 'profile_picture' in request.files:
                        file = request.files['profile_picture']
                        if file and file.filename:
                            args['profile_picture'] = base64.b64encode(file.read()).decode('utf-8')
                else:
                    return {
                        'description': "Unsupported Content-Type. Use 'application/json' or 'multipart/form-data'."}, 415

            user = student.user
            updated_fields = {}
            if args.get('username') is not None:
                existing_user = db_sess.query(User).filter(
                    User.username == args['username'],
                    User.user_id != user.user_id
                ).first()
                if existing_user:
                    return {'description': 'Username already taken'}, 400
                user.username = args['username']
                updated_fields['username'] = user.username
            if args.get('password') is not None:
                user.set_password(args['password'])
                updated_fields['password'] = 'updated'
            if args.get('first_name') is not None:
                user.first_name = args['first_name']
                updated_fields['first_name'] = user.first_name
            if args.get('last_name') is not None:
                user.last_name = args['last_name']
                updated_fields['last_name'] = user.last_name
            if args.get('email') is not None:
                existing_user = db_sess.query(User).filter(
                    User.email == args['email'],
                    User.user_id != user.user_id
                ).first()
                if existing_user:
                    return {'description': 'Email already taken'}, 400
                user.email = args['email']
                updated_fields['email'] = user.email
            if args.get('phone_number') is not None:
                user.phone_number = args['phone_number']
                updated_fields['phone_number'] = user.phone_number
            if args.get('profile_picture') is not None:
                user.profile_picture = args['profile_picture']
                updated_fields['profile_picture'] = 'updated'
            if args.get('class_id') is not None:
                try:
                    class_id = int(args['class_id'])
                except ValueError:
                    return {'description': 'class_id must be an integer'}, 400
                class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
                if not class_:
                    return {'description': f'Class with class_id {class_id} does not exist'}, 400
                student.class_id = class_id
                updated_fields['class_id'] = student.class_id
            if args.get('birth_date') is not None:
                student.birth_date = parse_date(args['birth_date'])
                updated_fields['birth_date'] = str(student.birth_date)
            if args.get('address') is not None:
                student.address = args['address']
                updated_fields['address'] = student.address

            db_sess.commit()
            logging.info(f"PATCH /api/admin/student/{student_id} - Updated by user {username}: {updated_fields}")
            return {
                'message': f'Данные студента {student_id} успешно обновлены.',
                'student_id': student.student_id,
                'updated_fields': updated_fields
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PATCH /api/admin/student/{student_id} - Error: {str(e)}")
            return {'description': f"Ошибка при обновлении студента: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/student/<student_id>", method="DELETE")
    def delete(self, student_id, username=None):
        db_sess = db_session.create_session()
        try:
            student = (db_sess.query(Student)
                       .options(joinedload(Student.user))
                       .filter(Student.student_id == student_id)
                       .first())

            if not student:
                logging.error(f"DELETE /api/admin/student/{student_id} - Not found for user {username}")
                return {'description': f'Ученик {student_id} не найден.'}, 404

            if not student.user:
                logging.error(f"Student {student_id} has no associated User")
                return {'description': "Ошибка: у студента отсутствуют данные пользователя."}, 500

            db_sess.delete(student.user)
            db_sess.delete(student)
            db_sess.commit()

            logging.info(f"DELETE /api/admin/student/{student_id} - Deleted by user {username}")
            return {
                'message': f'Студент {student_id} успешно удален.',
                'student_id': student_id
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"DELETE /api/admin/student/{student_id} - Error: {str(e)}")
            return {'description': f"Ошибка при удалении студента: {str(e)}"}, 500

        finally:
            db_sess.close()


class AdminAllStudentsAPI(Resource):
    """Класс для api всех студентов"""
    @admin_authorization_required("/api/admin/students/<string:search_query>", method="GET")
    def get(self, username=None, search=None):
        db_sess = db_session.create_session()
        try:
            logging.info(
                f"Received search query in AdminAllStudentsAPI: '{search}' (type: {type(search)}, raw: {repr(search)})")
            query = (db_sess.query(Student)
                     .options(joinedload(Student.user))
                     .options(joinedload(Student.class_)))

            if search and search.strip():
                search_term = f"%{search.strip()}%"
                logging.info(f"Applying search filter with term: '{search_term}'")
                query = query.join(User).join(Class).filter(
                    (User.first_name.ilike(search_term)) |
                    (User.last_name.ilike(search_term)) |
                    (func.concat(User.first_name, ' ', User.last_name).ilike(search_term)) |
                    (User.username.ilike(search_term)) |
                    (Class.class_name.ilike(search_term))
                )
                logging.info(f"Generated SQL query: {str(query)}")
            else:
                logging.info("No valid search query provided, returning all students")

            students = query.all()
            logging.info(f"Found {len(students)} students for search: '{search}'")

            if not students:
                logging.info(f"GET /api/admin/students - No students found by {username} with search='{search}'")
                return {
                    'message': 'Список студентов пуст.',
                    'students': []
                }, 200

            students_list = []
            for student in students:
                if not student.user or not student.class_:
                    logging.warning(f"Student {student.student_id} has incomplete associated data")
                    continue
                classes = {
                    'class_id': student.class_.class_id,
                    'class_name': student.class_.class_name,
                    'teacher_id': student.class_.teacher_id
                } if student.class_ else {'class_id': None, 'class_name': 'Без класса', 'teacher_id': None}
                student_data = {
                    'student_id': student.student_id,
                    'user_id': student.user_id,
                    'username': student.user.username if student.user else None,
                    'first_name': student.user.first_name if student.user else None,
                    'last_name': student.user.last_name if student.user else None,
                    'email': student.user.email if student.user else None,
                    'phone_number': student.user.phone_number if student.user else None,
                    'profile_picture': student.user.profile_picture if student.user else None,
                    'class': classes,
                    'birth_date': student.birth_date.strftime('%Y-%m-%d') if student.birth_date else None,
                    'address': student.address
                }
                students_list.append(student_data)

            logging.info(
                f"GET /api/admin/students - Retrieved {len(students)} students by {username} with search='{search}'")
            return {
                'message': f'Найдено {len(students)} студентов.',
                'students': students_list
            }, 200

        except Exception as e:
            logging.error(f"GET /api/admin/students - Error: {str(e)}")
            return {'description': f"Внутренняя ошибка сервера: {str(e)}"}, 500

        finally:
            db_sess.close()
