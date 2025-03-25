from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from data import db_session
from data.user import User
from data.teacher import Teacher
from data.classes import Class
from data.teacher_position_assignment import TeacherPositionAssignment
from data.teacher_position import TeacherPosition
from flask_restful import Resource, reqparse, abort
from .authorization_admin import check_admin_authorization
import logging

# Настройка логирования
logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

# Парсеры для PATCH и POST запросов
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

one_teacher_post = reqparse.RequestParser()
one_teacher_post.add_argument('username', type=str, required=True)
one_teacher_post.add_argument('password', type=str, required=True)
one_teacher_post.add_argument('first_name', type=str, required=True)
one_teacher_post.add_argument('last_name', type=str, required=True)
one_teacher_post.add_argument('email', type=str, required=True)
one_teacher_post.add_argument('phone_number', type=str, required=True)


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Incorrect date format. Use YYYY-MM-DD")

class AdminOneTeacherAPI(Resource):
    @staticmethod
    def get(teacher_id):
        """Получение информации об одном учителе по teacher_id."""
        username = check_admin_authorization(f"/api/admin/teacher/{teacher_id}", method="GET")
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
                abort(404, description=f'Учитель {teacher_id} не найден.')
            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                abort(500, description="Ошибка: у учителя отсутствуют данные пользователя.")

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
                    'start_time': sched.start_time,
                    'end_time': sched.end_time
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
                    'classes': classes,
                    'schedules': schedules,
                    'positions': positions
                }
            }
            return teacher_data, 200

        finally:
            db_sess.close()

    @staticmethod
    def patch(teacher_id):
        """Обновление данных учителя и его должности по teacher_id."""
        username = check_admin_authorization(f"/api/admin/teacher/{teacher_id}", method="PATCH")
        db_sess = db_session.create_session()

        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .options(joinedload(Teacher.positions))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())

            if not teacher:
                logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Not found for user {username}")
                abort(404, description=f'Учитель {teacher_id} не найден.')
            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                abort(500, description="Ошибка: у учителя отсутствуют данные пользователя.")

            # Получаем данные из парсера
            args = one_teacher_patch.parse_args()

            # Обновляем данные пользователя, если они переданы
            user = teacher.user
            updated_fields = {}
            if args['username'] is not None:
                user.username = args['username']
                updated_fields['username'] = args['username']
            if args['password'] is not None:
                user.set_password(args['password'])
                updated_fields['password'] = 'updated'
            if args['first_name'] is not None:
                user.first_name = args['first_name']
                updated_fields['first_name'] = args['first_name']
            if args['last_name'] is not None:
                user.last_name = args['last_name']
                updated_fields['last_name'] = args['last_name']
            if args['email'] is not None:
                user.email = args['email']
                updated_fields['email'] = args['email']
            if args['phone_number'] is not None:
                user.phone_number = args['phone_number']
                updated_fields['phone_number'] = args['phone_number']
            if args['profile_picture'] is not None:
                user.profile_picture = args['profile_picture']
                updated_fields['profile_picture'] = args['profile_picture']

            # Обновляем или добавляем запись в TeacherPositionAssignment
            if args['position_id'] is not None:
                # Проверяем, существует ли указанная должность
                position_exists = db_sess.query(TeacherPosition).filter(TeacherPosition.position_id == args['position_id']).first()
                if not position_exists:
                    logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Position {args['position_id']} not found")
                    abort(400, description=f"Должность с ID {args['position_id']} не найдена.")

                # Проверяем, существует ли запись в TeacherPositionAssignment
                position_assignment = db_sess.query(TeacherPositionAssignment).filter(
                    TeacherPositionAssignment.teacher_id == teacher.teacher_id,
                    TeacherPositionAssignment.position_id == args['position_id']
                ).first()

                if position_assignment:
                    # Обновляем существующую запись
                    if args['class_id'] is not None:
                        class_exists = db_sess.query(Class).filter(Class.class_id == args['class_id']).first()
                        if not class_exists and args['class_id'] != 0:  # 0 допустим как null
                            logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Class {args['class_id']} not found")
                            abort(400, description=f"Класс с ID {args['class_id']} не найден.")
                        position_assignment.class_id = args['class_id'] if args['class_id'] != 0 else None
                    if args['subject_id'] is not None:
                        position_assignment.subject_id = args['subject_id'] if args['subject_id'] != 0 else None
                else:
                    # Создаем новую запись
                    class_id = args['class_id'] if args['class_id'] is not None and args['class_id'] != 0 else None
                    if class_id:
                        class_exists = db_sess.query(Class).filter(Class.class_id == class_id).first()
                        if not class_exists:
                            logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Class {class_id} not found")
                            abort(400, description=f"Класс с ID {class_id} не найден.")
                    subject_id = args['subject_id'] if args['subject_id'] is not None and args['subject_id'] != 0 else None
                    new_assignment = TeacherPositionAssignment(
                        teacher_id=teacher.teacher_id,
                        position_id=args['position_id'],
                        class_id=class_id,
                        subject_id=subject_id
                    )
                    db_sess.add(new_assignment)

                updated_fields['position_id'] = args['position_id']
                if args['class_id'] is not None:
                    updated_fields['class_id'] = args['class_id']
                if args['subject_id'] is not None:
                    updated_fields['subject_id'] = args['subject_id']

            # Фиксируем изменения в базе данных
            db_sess.commit()
            logging.info(f"PATCH /api/admin/teacher/{teacher_id} - Updated by user {username}")

            return {
                'message': f'Данные учителя {teacher_id} успешно обновлены.',
                'teacher_id': teacher.teacher_id,
                'updated_fields': updated_fields
            }, 200

        finally:
            db_sess.close()

    @staticmethod
    def post():
        """Создание нового учителя."""
        username = check_admin_authorization("/api/admin/teacher", method="POST")
        db_sess = db_session.create_session()

        try:
            # Получаем данные из парсера
            args = one_teacher_post.parse_args()

            # Проверяем уникальность username и email
            if db_sess.query(User).filter(User.username == args['username']).first():
                logging.error(f"POST /api/admin/teacher - Username {args['username']} already exists")
                abort(400, description=f"Пользователь с именем {args['username']} уже существует.")
            if db_sess.query(User).filter(User.email == args['email']).first():
                logging.error(f"POST /api/admin/teacher - Email {args['email']} already exists")
                abort(400, description=f"Email {args['email']} уже зарегистрирован.")

            # Создаем нового пользователя
            new_user = User(
                username=args['username'],
                first_name=args['first_name'],
                last_name=args['last_name'],
                email=args['email'],
                phone_number=args['phone_number'],
                profile_picture='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'
            )
            new_user.set_password(args['password'])  # Хешируем пароль

            db_sess.add(new_user)
            db_sess.flush()  # Получаем user_id до коммита

            # Создаем нового учителя
            new_teacher = Teacher(
                user_id=new_user.user_id,
                teacher_id=(db_sess.query(func.max(Teacher.teacher_id)).scalar() or 0) + 1
            )
            db_sess.add(new_teacher)

            # Фиксируем изменения в базе данных
            db_sess.commit()
            logging.info(f"POST /api/admin/teacher - Created teacher with user_id {new_user.user_id} by {username}")

            # Возвращаем данные о созданном учителе
            return {
                'message': 'Учитель успешно создан.',
                'teacher': {
                    'user_id': new_user.user_id,
                    'teacher_id': new_teacher.teacher_id,
                    'username': new_user.username,
                    'email': new_user.email,
                    'phone_number': new_user.phone_number,
                }
            }, 201

        finally:
            db_sess.close()

    @staticmethod
    def delete(teacher_id):
        username = check_admin_authorization(f"/api/admin/teacher/{teacher_id}", method="DELETE")
        db_sess = db_session.create_session()
        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())
            if not teacher:
                logging.error(f"DELETE /api/admin/teacher/{teacher_id} - Not found for user {username}")
                abort(404, description=f'Учитель {teacher_id} не найден.')
            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                abort(500, description="Ошибка: у учителя отсутствуют данные пользователя.")

            # Удаляем все записи из teacher_position_assignments для этого учителя
            db_sess.query(TeacherPositionAssignment).filter(
                TeacherPositionAssignment.teacher_id == teacher.teacher_id
            ).delete()

            # Удаляем учителя и связанного пользователя
            db_sess.delete(teacher.user)
            db_sess.delete(teacher)
            db_sess.commit()  # Строка 305
            logging.info(f"DELETE /api/admin/teacher/{teacher_id} - Deleted by user {username}")
            return {
                'message': f'Учитель {teacher_id} успешно удален.',
                'teacher_id': teacher_id
            }, 200
        finally:
            db_sess.close()


class AdminAllTeachersAPI(Resource):
    @staticmethod
    def get():
        """Получение списка всех учителей."""
        username = check_admin_authorization("/api/admin/teachers", method="GET")
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
                # Формируем данные о классах
                classes = [
                    {'class_id': cls.class_id, 'class_name': cls.class_name}
                    for cls in teacher.classes
                ]
                # Формируем данные о расписании
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
                # Формируем данные о должностях
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
                    'username': teacher.user.username,
                    'first_name': teacher.user.first_name,
                    'last_name': teacher.user.last_name,
                    'email': teacher.user.email if teacher.user else None,
                    'phone_number': teacher.user.phone_number if teacher.user else None,
                    'profile_picture': teacher.user.profile_picture if teacher.user else None,
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
            abort(500, description="Внутренняя ошибка сервера.")

        finally:
            db_sess.close()
