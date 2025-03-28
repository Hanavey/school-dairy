from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from data import db_session
from data.teacher import Teacher
from data.user import User
from data.classes import Class
from data.teacher_position_assignment import TeacherPositionAssignment
from data.teacher_position import TeacherPosition
from flask_restful import Resource, reqparse, abort
from flask import request
from decorators.authorization_admin_decorator import admin_authorization_required
import logging
import base64

# Настройка логирования
logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Incorrect date format. Use YYYY-MM-DD")

class AdminOneTeacherAPI(Resource):
    # Парсер для PATCH-запросов
    one_teacher_patch = reqparse.RequestParser()
    one_teacher_patch.add_argument('username', type=str)
    one_teacher_patch.add_argument('password', type=str)
    one_teacher_patch.add_argument('first_name', type=str)
    one_teacher_patch.add_argument('last_name', type=str)
    one_teacher_patch.add_argument('email', type=str)
    one_teacher_patch.add_argument('phone_number', type=str)
    one_teacher_patch.add_argument('profile_picture', type=str)
    one_teacher_patch.add_argument('position_id', type=int)  # ID должности
    one_teacher_patch.add_argument('class_id', type=int)     # ID класса (может быть null)
    one_teacher_patch.add_argument('subject_id', type=int)   # ID предмета (может быть null)

    # Парсер для POST-запросов
    one_teacher_post = reqparse.RequestParser()
    one_teacher_post.add_argument('username', type=str, required=True)
    one_teacher_post.add_argument('password', type=str, required=True)
    one_teacher_post.add_argument('first_name', type=str, required=True)
    one_teacher_post.add_argument('last_name', type=str, required=True)
    one_teacher_post.add_argument('email', type=str, required=True)
    one_teacher_post.add_argument('phone_number', type=str, required=True)
    one_teacher_post.add_argument('position_id', type=int, required=True)
    one_teacher_post.add_argument('class_id', type=int)     # Необязательное поле
    one_teacher_post.add_argument('subject_id', type=int)   # Необязательное поле

    @admin_authorization_required("/api/admin/teacher/<teacher_id>", method="GET")
    def get(self, teacher_id, username=None):
        """Получение информации об одном учителе по teacher_id."""
        db_sess = db_session.create_session()
        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .options(joinedload(Teacher.classes))
                       .options(joinedload(Teacher.schedules))
                       .options(joinedload(Teacher.positions))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())

            if not teacher:
                logging.error(f"GET /api/admin/teacher/{teacher_id} - Not found for user {username}")
                return {'description': f'Учитель {teacher_id} не найден.'}, 404

            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                return {'description': "Ошибка: у учителя отсутствуют данные пользователя."}, 500

            # Формируем данные об учителе
            classes = [
                {'class_id': cls.class_id, 'class_name': cls.class_name}
                for cls in teacher.classes
            ]
            schedules = [
                {
                    'schedule_id': sched.schedule_id,
                    'class_id': sched.class_id,
                    'subject_id': sched.subject_id,
                    'day_of_week': sched.day_of_week,
                    'start_time': str(sched.start_time) if sched.start_time else None,
                    'end_time': str(sched.end_time) if sched.end_time else None
                }
                for sched in teacher.schedules
            ]
            positions = [
                {
                    'position_id': pos.position_id,
                    'class_id': pos.class_id,
                    'subject_id': pos.subject_id
                }
                for pos in teacher.positions
            ]

            teacher_data = {
                'Teacher': {
                    'user_id': teacher.user_id,
                    'teacher_id': teacher.teacher_id,
                    'username': teacher.user.username,
                    'first_name': teacher.user.first_name,
                    'last_name': teacher.user.last_name,
                    'email': teacher.user.email if teacher.user.email else None,
                    'phone_number': teacher.user.phone_number if teacher.user.phone_number else None,
                    'profile_picture': teacher.user.profile_picture,
                    'api_key': teacher.user.api_key,
                    'classes': classes,
                    'schedules': schedules,
                    'positions': positions
                }
            }
            logging.info(f"GET /api/admin/teacher/{teacher_id} - Retrieved by user {username}")
            return teacher_data, 200

        except Exception as e:
            logging.error(f"GET /api/admin/teacher/{teacher_id} - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных учителя: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/teacher", method="POST")
    def post(self, username=None, update_data=None):
        """Создание нового учителя."""
        db_sess = db_session.create_session()
        try:
            if update_data is not None:
                # Используем данные из аргумента update_data, если он передан
                username = update_data.get('username')
                password = update_data.get('password')
                first_name = update_data.get('first_name')
                last_name = update_data.get('last_name')
                email = update_data.get('email')
                phone_number = update_data.get('phone_number')
                position_id = update_data.get('position_id')
                class_id = update_data.get('class_id')
                subject_id = update_data.get('subject_id')
                profile_picture = update_data.get('profile_picture')

                # Валидация обязательных полей
                required_fields = {
                    'username': username,
                    'password': password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone_number': phone_number,
                    'position_id': position_id
                }
                for field_name, field_value in required_fields.items():
                    if not field_value:
                        return {'description': f'Field {field_name} is required'}, 400

                # Преобразуем position_id в int
                try:
                    position_id = int(position_id)
                except ValueError:
                    return {'description': 'position_id must be an integer'}, 400

                # Преобразуем class_id в int, если передан
                if class_id:
                    try:
                        class_id = int(class_id)
                    except ValueError:
                        return {'description': 'class_id must be an integer'}, 400

                # Преобразуем subject_id в int, если передан
                if subject_id:
                    try:
                        subject_id = int(subject_id)
                    except ValueError:
                        return {'description': 'subject_id must be an integer'}, 400

            else:
                # Проверяем Content-Type запроса
                content_type = request.headers.get('Content-Type', '')

                if 'multipart/form-data' in content_type:
                    # Обработка multipart/form-data (для формы)
                    data = request.form
                    username = data.get('username')
                    password = data.get('password')
                    first_name = data.get('first_name')
                    last_name = data.get('last_name')
                    email = data.get('email')
                    phone_number = data.get('phone_number')
                    position_id = data.get('position_id')
                    class_id = data.get('class_id')
                    subject_id = data.get('subject_id')
                    profile_picture = None

                    # Проверяем, есть ли файл в запросе
                    if 'profile_picture' in request.files:
                        file = request.files['profile_picture']
                        if file and file.filename:
                            # Читаем файл и конвертируем в Base64
                            file_content = file.read()
                            profile_picture = base64.b64encode(file_content).decode('utf-8')

                    # Валидация обязательных полей
                    required_fields = ['username', 'password', 'first_name', 'last_name', 'email', 'phone_number',
                                       'position_id']
                    for field in required_fields:
                        if not data.get(field):
                            return {'description': f'Field {field} is required'}, 400

                    # Преобразуем position_id в int
                    try:
                        position_id = int(position_id)
                    except ValueError:
                        return {'description': 'position_id must be an integer'}, 400

                    # Преобразуем class_id в int, если передан
                    if class_id:
                        try:
                            class_id = int(class_id)
                        except ValueError:
                            return {'description': 'class_id must be an integer'}, 400

                    # Преобразуем subject_id в int, если передан
                    if subject_id:
                        try:
                            subject_id = int(subject_id)
                        except ValueError:
                            return {'description': 'subject_id must be an integer'}, 400

                else:
                    # Обработка application/json (для сторонних обращений)
                    args = self.one_teacher_post.parse_args()
                    username = args['username']
                    password = args['password']
                    first_name = args['first_name']
                    last_name = args['last_name']
                    email = args['email']
                    phone_number = args['phone_number']
                    position_id = args['position_id']
                    class_id = args.get('class_id')
                    subject_id = args.get('subject_id')
                    profile_picture = args.get('profile_picture')  # Для JSON это необязательное поле

            # Проверяем, существует ли должность
            position = db_sess.query(TeacherPosition).filter(TeacherPosition.position_id == position_id).first()
            if not position:
                return {'description': f'Position with position_id {position_id} does not exist'}, 400

            # Проверяем, существует ли класс, если передан class_id
            if class_id:
                class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
                if not class_:
                    return {'description': f'Class with class_id {class_id} does not exist'}, 400

            # Проверяем, не существует ли уже пользователь с таким username или email
            existing_user = db_sess.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            if existing_user:
                return {'description': 'User with this username or email already exists'}, 400

            # Генерируем teacher_id (максимальный + 1)
            max_teacher_id = db_sess.query(func.max(Teacher.teacher_id)).scalar() or 0
            new_teacher_id = max_teacher_id + 1

            # Создаем нового пользователя
            with open('static/images/base.png', 'rb') as f:
                file_content = f.read()
                base_picture = base64.b64encode(file_content).decode('utf-8')

            new_user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                profile_picture=profile_picture if profile_picture else base_picture
            )
            new_user.set_password(password)
            db_sess.add(new_user)
            db_sess.flush()  # Получаем user_id

            # Создаем нового учителя
            new_teacher = Teacher(
                user_id=new_user.user_id,
                teacher_id=new_teacher_id
            )
            db_sess.add(new_teacher)
            db_sess.flush()  # Получаем teacher_id

            # Создаем запись в TeacherPositionAssignment
            new_assignment = TeacherPositionAssignment(
                teacher_id=new_teacher.teacher_id,
                position_id=position_id,
                class_id=class_id if class_id else None,
                subject_id=subject_id if subject_id else None
            )
            db_sess.add(new_assignment)
            db_sess.commit()

            # Логируем успешное создание
            logging.info(f"POST /api/admin/teacher - Teacher {new_teacher.teacher_id} created by user {username}")

            # Возвращаем данные о созданном учителе
            return {
                'message': 'Учитель успешно создан.',
                'teacher': {
                    'user_id': new_user.user_id,
                    'teacher_id': new_teacher.teacher_id,
                    'username': new_user.username,
                    'email': new_user.email,
                    'position_id': position_id,
                    'class_id': class_id,
                    'subject_id': subject_id
                }
            }, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/admin/teacher - Error: {str(e)}")
            return {'description': f"Ошибка при создании учителя: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/teacher/<teacher_id>", method="PATCH")
    def patch(self, teacher_id, username=None, update_data=None):
        """Обновление данных учителя и его должности по teacher_id."""
        db_sess = db_session.create_session()
        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .options(joinedload(Teacher.positions))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())

            if not teacher:
                logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Not found for user {username}")
                return {'description': f'Учитель {teacher_id} не найден.'}, 404

            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                return {'description': "Ошибка: у учителя отсутствуют данные пользователя."}, 500

            # Если update_data передано (например, из маршрута), используем его
            if update_data is not None:
                args = update_data
            else:
                # Иначе проверяем Content-Type и обрабатываем запрос
                content_type = request.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    args = self.one_teacher_patch.parse_args()
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

            # Обновляем данные пользователя, если они переданы
            user = teacher.user
            updated_fields = {}
            if args.get('username') is not None:
                # Проверяем, не занят ли новый username
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
                # Проверяем, не занят ли новый email
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

            # Обновляем или добавляем запись в TeacherPositionAssignment
            if args.get('position_id') is not None:
                # Проверяем, существует ли указанная должность
                position_exists = db_sess.query(TeacherPosition).filter(
                    TeacherPosition.position_id == args['position_id']).first()
                if not position_exists:
                    logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Position {args['position_id']} not found")
                    return {'description': f"Должность с ID {args['position_id']} не найдена."}, 400

                # Проверяем, существует ли запись в TeacherPositionAssignment
                position_assignment = db_sess.query(TeacherPositionAssignment).filter(
                    TeacherPositionAssignment.teacher_id == teacher.teacher_id,
                    TeacherPositionAssignment.position_id == args['position_id']
                ).first()

                if position_assignment:
                    # Обновляем существующую запись
                    if args.get('class_id') is not None:
                        class_id = args['class_id']
                        if class_id:
                            class_exists = db_sess.query(Class).filter(Class.class_id == class_id).first()
                            if not class_exists:
                                logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Class {class_id} not found")
                                return {'description': f"Класс с ID {class_id} не найден."}, 400
                        position_assignment.class_id = class_id if class_id else None
                    if args.get('subject_id') is not None:
                        position_assignment.subject_id = args['subject_id'] if args['subject_id'] else None
                else:
                    # Создаем новую запись
                    class_id = args.get('class_id')
                    if class_id:
                        class_exists = db_sess.query(Class).filter(Class.class_id == class_id).first()
                        if not class_exists:
                            logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Class {class_id} not found")
                            return {'description': f"Класс с ID {class_id} не найден."}, 400
                    subject_id = args.get('subject_id')
                    new_assignment = TeacherPositionAssignment(
                        teacher_id=teacher.teacher_id,
                        position_id=args['position_id'],
                        class_id=class_id,
                        subject_id=subject_id
                    )
                    db_sess.add(new_assignment)

                updated_fields['position_id'] = args['position_id']
                if args.get('class_id') is not None:
                    updated_fields['class_id'] = args['class_id']
                if args.get('subject_id') is not None:
                    updated_fields['subject_id'] = args['subject_id']

            # Фиксируем изменения в базе данных
            db_sess.commit()
            logging.info(f"PATCH /api/admin/teacher/{teacher_id} - Updated by user {username}: {updated_fields}")

            return {
                'message': f'Данные учителя {teacher_id} успешно обновлены.',
                'teacher_id': teacher.teacher_id,
                'updated_fields': updated_fields
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Error: {str(e)}")
            return {'description': f"Ошибка при обновлении учителя: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/teacher/<teacher_id>", method="DELETE")
    def delete(self, teacher_id, username=None):
        """Удаление учителя по teacher_id."""
        db_sess = db_session.create_session()
        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())

            if not teacher:
                logging.error(f"DELETE /api/admin/teacher/{teacher_id} - Not found for user {username}")
                return {'description': f'Учитель {teacher_id} не найден.'}, 404

            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                return {'description': "Ошибка: у учителя отсутствуют данные пользователя."}, 500

            # Удаляем все записи из teacher_position_assignments для этого учителя
            db_sess.query(TeacherPositionAssignment).filter(
                TeacherPositionAssignment.teacher_id == teacher.teacher_id
            ).delete()

            # Удаляем учителя и связанного пользователя
            db_sess.delete(teacher.user)  # Удаляем пользователя (каскадно удалит учителя, если настроено)
            db_sess.delete(teacher)  # Удаляем учителя напрямую для надежности
            db_sess.commit()

            logging.info(f"DELETE /api/admin/teacher/{teacher_id} - Deleted by user {username}")
            return {
                'message': f'Учитель {teacher_id} успешно удален.',
                'teacher_id': teacher_id
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"DELETE /api/admin/teacher/{teacher_id} - Error: {str(e)}")
            return {'description': f"Ошибка при удалении учителя: {str(e)}"}, 500

        finally:
            db_sess.close()

class AdminAllTeachersAPI(Resource):
    @admin_authorization_required("/api/admin/teachers", method="GET")
    def get(self, username=None):
        """Получение списка всех учителей."""
        db_sess = db_session.create_session()
        try:
            # Запрашиваем всех учителей с подгрузкой связанных данных
            teachers = (db_sess.query(Teacher)
                        .options(joinedload(Teacher.user))
                        .options(joinedload(Teacher.classes))
                        .options(joinedload(Teacher.schedules))
                        .options(joinedload(Teacher.positions))
                        .all())

            if not teachers:
                logging.info(f"GET /api/admin/teachers - No teachers found by {username}")
                return {
                    'message': 'Список учителей пуст.',
                    'teachers': []
                }, 200

            # Формируем список учителей для ответа
            teachers_list = []
            for teacher in teachers:
                classes = [
                    {'class_id': cls.class_id, 'class_name': cls.class_name}
                    for cls in teacher.classes
                ]
                schedules = [
                    {
                        'schedule_id': sched.schedule_id,
                        'class_id': sched.class_id,
                        'subject_id': sched.subject_id,
                        'day_of_week': sched.day_of_week,
                        'start_time': str(sched.start_time) if sched.start_time else None,
                        'end_time': str(sched.end_time) if sched.end_time else None
                    }
                    for sched in teacher.schedules
                ]
                positions = [
                    {
                        'position_id': pos.position_id,
                        'class_id': pos.class_id,
                        'subject_id': pos.subject_id
                    }
                    for pos in teacher.positions
                ]

                teacher_data = {
                    'teacher_id': teacher.teacher_id,
                    'user_id': teacher.user_id,
                    'username': teacher.user.username if teacher.user else None,
                    'first_name': teacher.user.first_name if teacher.user else None,
                    'last_name': teacher.user.last_name if teacher.user else None,
                    'email': teacher.user.email if teacher.user else None,
                    'phone_number': teacher.user.phone_number if teacher.user else None,
                    'profile_picture': teacher.user.profile_picture if teacher.user else None,
                    'api_key': teacher.user.api_key if teacher.user else None,
                    'classes': classes,
                    'schedules': schedules,
                    'positions': positions
                }
                teachers_list.append(teacher_data)

            logging.info(f"GET /api/admin/teachers - Retrieved {len(teachers)} teachers by {username}")
            return {
                'message': f'Найдено {len(teachers)} учителей.',
                'teachers': teachers_list
            }, 200

        except Exception as e:
            logging.error(f"GET /api/admin/teachers - Error: {str(e)}")
            return {'description': f"Внутренняя ошибка сервера: {str(e)}"}, 500

        finally:
            db_sess.close()
