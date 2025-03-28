from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from data import db_session
from data.schedule import Schedule
from data.classes import Class
from data.subject import Subject
from data.teacher import Teacher
from data.user import User
from flask_restful import Resource, reqparse, abort
from flask import request
from decorators.authorization_admin_decorator import admin_authorization_required
import logging


# Настройка логирования
logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


def validate_time_format(time_str):
    """Проверка формата времени (HH:MM)."""
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False


class AdminOneScheduleAPI(Resource):
    # Парсер для PATCH-запросов
    one_schedule_patch = reqparse.RequestParser()
    one_schedule_patch.add_argument('class_id', type=int)
    one_schedule_patch.add_argument('subject_id', type=int)
    one_schedule_patch.add_argument('teacher_id', type=int)
    one_schedule_patch.add_argument('day_of_week', type=str)
    one_schedule_patch.add_argument('start_time', type=str)
    one_schedule_patch.add_argument('end_time', type=str)

    # Парсер для POST-запросов
    one_schedule_post = reqparse.RequestParser()
    one_schedule_post.add_argument('class_id', type=int, required=True)
    one_schedule_post.add_argument('subject_id', type=int, required=True)
    one_schedule_post.add_argument('teacher_id', type=int, required=True)
    one_schedule_post.add_argument('day_of_week', type=str, required=True)
    one_schedule_post.add_argument('start_time', type=str, required=True)
    one_schedule_post.add_argument('end_time', type=str, required=True)

    @admin_authorization_required("/api/admin/schedule/<schedule_id>", method="GET")
    def get(self, schedule_id, username=None):
        """Получение информации об одной записи расписания по schedule_id."""
        db_sess = db_session.create_session()
        try:
            schedule = (db_sess.query(Schedule)
                        .options(joinedload(Schedule.class_))
                        .options(joinedload(Schedule.subject))
                        .options(joinedload(Schedule.teacher).joinedload(Teacher.user))
                        .filter(Schedule.schedule_id == schedule_id)
                        .first())

            if not schedule:
                logging.error(f"GET /api/admin/schedule/{schedule_id} - Not found for user {username}")
                return {'description': f'Запись расписания {schedule_id} не найдена.'}, 404

            schedule_data = {
                'Schedule': {
                    'schedule_id': schedule.schedule_id,
                    'class': {
                        'class_id': schedule.class_.class_id,
                        'class_name': schedule.class_.class_name
                    },
                    'subject': {
                        'subject_id': schedule.subject.subject_id,
                        'subject_name': schedule.subject.subject_name
                    },
                    'teacher': {
                        'teacher_id': schedule.teacher.teacher_id,
                        'username': schedule.teacher.user.username if schedule.teacher.user else None,
                        'first_name': schedule.teacher.user.first_name if schedule.teacher.user else None,
                        'last_name': schedule.teacher.user.last_name if schedule.teacher.user else None
                    },
                    'day_of_week': schedule.day_of_week,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time
                }
            }
            logging.info(f"GET /api/admin/schedule/{schedule_id} - Retrieved by user {username}")
            return schedule_data, 200

        except Exception as e:
            logging.error(f"GET /api/admin/schedule/{schedule_id} - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных расписания: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/schedule", method="POST")
    def post(self, username=None, update_data=None):
        """Создание новой записи расписания."""
        db_sess = db_session.create_session()
        try:
            if update_data is not None:
                # Используем данные из аргумента update_data, если он передан
                class_id = update_data.get('class_id')
                subject_id = update_data.get('subject_id')
                teacher_id = update_data.get('teacher_id')
                day_of_week = update_data.get('day_of_week')
                start_time = update_data.get('start_time')
                end_time = update_data.get('end_time')

                # Валидация обязательных полей
                required_fields = {
                    'class_id': class_id,
                    'subject_id': subject_id,
                    'teacher_id': teacher_id,
                    'day_of_week': day_of_week,
                    'start_time': start_time,
                    'end_time': end_time
                }
                for field_name, field_value in required_fields.items():
                    if field_value is None:
                        return {'description': f'Field {field_name} is required'}, 400

            else:
                # Проверяем Content-Type запроса
                content_type = request.headers.get('Content-Type', '')

                if 'multipart/form-data' in content_type:
                    # Обработка multipart/form-data (для формы)
                    data = request.form
                    class_id = data.get('class_id')
                    subject_id = data.get('subject_id')
                    teacher_id = data.get('teacher_id')
                    day_of_week = data.get('day_of_week')
                    start_time = data.get('start_time')
                    end_time = data.get('end_time')

                    # Валидация обязательных полей
                    required_fields = ['class_id', 'subject_id', 'teacher_id', 'day_of_week', 'start_time', 'end_time']
                    for field in required_fields:
                        if not data.get(field):
                            return {'description': f'Field {field} is required'}, 400

                    # Преобразуем поля в int
                    try:
                        class_id = int(class_id)
                        subject_id = int(subject_id)
                        teacher_id = int(teacher_id)
                    except ValueError:
                        return {'description': 'class_id, subject_id, and teacher_id must be integers'}, 400

                else:
                    # Обработка application/json (для сторонних обращений)
                    args = self.one_schedule_post.parse_args()
                    class_id = args['class_id']
                    subject_id = args['subject_id']
                    teacher_id = args['teacher_id']
                    day_of_week = args['day_of_week']
                    start_time = args['start_time']
                    end_time = args['end_time']

            # Проверяем формат времени
            if not validate_time_format(start_time) or not validate_time_format(end_time):
                return {'description': 'start_time and end_time must be in HH:MM format'}, 400

            # Проверяем, существует ли класс
            class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
            if not class_:
                return {'description': f'Class with class_id {class_id} does not exist'}, 400

            # Проверяем, существует ли предмет
            subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
            if not subject:
                return {'description': f'Subject with subject_id {subject_id} does not exist'}, 400

            # Проверяем, существует ли учитель
            teacher = db_sess.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
            if not teacher:
                return {'description': f'Teacher with teacher_id {teacher_id} does not exist'}, 400

            # Проверяем, нет ли пересечений в расписании для учителя
            existing_schedule = (db_sess.query(Schedule)
                                .filter(Schedule.teacher_id == teacher_id,
                                        Schedule.day_of_week == day_of_week,
                                        Schedule.start_time == start_time)
                                .first())
            if existing_schedule:
                return {'description': f'Teacher {teacher_id} already has a schedule at {start_time} on {day_of_week}'}, 400

            # Создаем новую запись расписания
            new_schedule = Schedule(
                class_id=class_id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            db_sess.add(new_schedule)
            db_sess.commit()

            logging.info(f"POST /api/admin/schedule - Schedule {new_schedule.schedule_id} created by user {username}")
            return {
                'message': 'Запись расписания успешно создана.',
                'schedule': {
                    'schedule_id': new_schedule.schedule_id,
                    'class_id': new_schedule.class_id,
                    'subject_id': new_schedule.subject_id,
                    'teacher_id': new_schedule.teacher_id,
                    'day_of_week': new_schedule.day_of_week,
                    'start_time': new_schedule.start_time,
                    'end_time': new_schedule.end_time
                }
            }, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/admin/schedule - Error: {str(e)}")
            return {'description': f"Ошибка при создании записи расписания: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/schedule/<schedule_id>", method="PATCH")
    def patch(self, schedule_id, username=None, update_data=None):
        """Обновление записи расписания по schedule_id."""
        db_sess = db_session.create_session()
        try:
            schedule = (db_sess.query(Schedule)
                        .options(joinedload(Schedule.class_))
                        .options(joinedload(Schedule.subject))
                        .options(joinedload(Schedule.teacher))
                        .filter(Schedule.schedule_id == schedule_id)
                        .first())

            if not schedule:
                logging.error(f"PATCH /api/admin/schedule/{schedule_id} - Not found for user {username}")
                return {'description': f'Запись расписания {schedule_id} не найдена.'}, 404

            # Если update_data передано (например, из маршрута), используем его
            if update_data is not None:
                args = update_data
            else:
                # Иначе проверяем Content-Type и обрабатываем запрос
                content_type = request.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    args = self.one_schedule_patch.parse_args()
                elif 'multipart/form-data' in content_type:
                    args = {}
                    for key in request.form:
                        args[key] = request.form[key]
                else:
                    return {'description': "Unsupported Content-Type. Use 'application/json' or 'multipart/form-data'."}, 415

            updated_fields = {}
            if args.get('class_id') is not None:
                class_ = db_sess.query(Class).filter(Class.class_id == args['class_id']).first()
                if not class_:
                    return {'description': f'Class with class_id {args["class_id"]} does not exist'}, 400
                schedule.class_id = args['class_id']
                updated_fields['class_id'] = schedule.class_id
            if args.get('subject_id') is not None:
                subject = db_sess.query(Subject).filter(Subject.subject_id == args['subject_id']).first()
                if not subject:
                    return {'description': f'Subject with subject_id {args["subject_id"]} does not exist'}, 400
                schedule.subject_id = args['subject_id']
                updated_fields['subject_id'] = schedule.subject_id
            if args.get('teacher_id') is not None:
                teacher = db_sess.query(Teacher).filter(Teacher.teacher_id == args['teacher_id']).first()
                if not teacher:
                    return {'description': f'Teacher with teacher_id {args["teacher_id"]} does not exist'}, 400
                schedule.teacher_id = args['teacher_id']
                updated_fields['teacher_id'] = schedule.teacher_id
            if args.get('day_of_week') is not None:
                schedule.day_of_week = args['day_of_week']
                updated_fields['day_of_week'] = schedule.day_of_week
            if args.get('start_time') is not None:
                if not validate_time_format(args['start_time']):
                    return {'description': 'start_time must be in HH:MM format'}, 400
                schedule.start_time = args['start_time']
                updated_fields['start_time'] = schedule.start_time
            if args.get('end_time') is not None:
                if not validate_time_format(args['end_time']):
                    return {'description': 'end_time must be in HH:MM format'}, 400
                schedule.end_time = args['end_time']
                updated_fields['end_time'] = schedule.end_time

            # Проверяем пересечения после обновления
            existing_schedule = (db_sess.query(Schedule)
                                .filter(Schedule.teacher_id == schedule.teacher_id,
                                        Schedule.day_of_week == schedule.day_of_week,
                                        Schedule.start_time == schedule.start_time,
                                        Schedule.schedule_id != schedule.schedule_id)
                                .first())
            if existing_schedule:
                return {'description': f'Teacher {schedule.teacher_id} already has a schedule at {schedule.start_time} on {schedule.day_of_week}'}, 400

            db_sess.commit()
            logging.info(f"PATCH /api/admin/schedule/{schedule_id} - Updated by user {username}: {updated_fields}")
            return {
                'message': f'Запись расписания {schedule_id} успешно обновлена.',
                'schedule_id': schedule.schedule_id,
                'updated_fields': updated_fields
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PATCH /api/admin/schedule/{schedule_id} - Error: {str(e)}")
            return {'description': f"Ошибка при обновлении записи расписания: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/schedule/<schedule_id>", method="DELETE")
    def delete(self, schedule_id, username=None):
        """Удаление записи расписания по schedule_id."""
        db_sess = db_session.create_session()
        try:
            schedule = db_sess.query(Schedule).filter(Schedule.schedule_id == schedule_id).first()

            if not schedule:
                logging.error(f"DELETE /api/admin/schedule/{schedule_id} - Not found for user {username}")
                return {'description': f'Запись расписания {schedule_id} не найдена.'}, 404

            db_sess.delete(schedule)
            db_sess.commit()

            logging.info(f"DELETE /api/admin/schedule/{schedule_id} - Deleted by user {username}")
            return {
                'message': f'Запись расписания {schedule_id} успешно удалена.',
                'schedule_id': schedule_id
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"DELETE /api/admin/schedule/{schedule_id} - Error: {str(e)}")
            return {'description': f"Ошибка при удалении записи расписания: {str(e)}"}, 500

        finally:
            db_sess.close()


class AdminAllSchedulesAPI(Resource):
    @admin_authorization_required("/api/admin/schedules", method="GET")
    def get(self, username=None):
        """Получение списка всех записей расписания."""
        db_sess = db_session.create_session()
        try:
            # Запрашиваем все записи расписания с подгрузкой связанных данных
            schedules = (db_sess.query(Schedule)
                         .options(joinedload(Schedule.class_))
                         .options(joinedload(Schedule.subject))
                         .options(joinedload(Schedule.teacher).joinedload(Teacher.user))
                         .all())

            if not schedules:
                logging.info(f"GET /api/admin/schedules - No schedules found by {username}")
                return {
                    'message': 'Список расписания пуст.',
                    'schedules': []
                }, 200

            # Формируем список записей расписания для ответа
            schedules_list = []
            for schedule in schedules:
                schedule_data = {
                    'schedule_id': schedule.schedule_id,
                    'class': {
                        'class_id': schedule.class_.class_id,
                        'class_name': schedule.class_.class_name
                    },
                    'subject': {
                        'subject_id': schedule.subject.subject_id,
                        'subject_name': schedule.subject.subject_name
                    },
                    'teacher': {
                        'teacher_id': schedule.teacher.teacher_id,
                        'username': schedule.teacher.user.username if schedule.teacher.user else None,
                        'first_name': schedule.teacher.user.first_name if schedule.teacher.user else None,
                        'last_name': schedule.teacher.user.last_name if schedule.teacher.user else None
                    },
                    'day_of_week': schedule.day_of_week,
                    'start_time': schedule.start_time,
                    'end_time': schedule.end_time
                }
                schedules_list.append(schedule_data)

            logging.info(f"GET /api/admin/schedules - Retrieved {len(schedules)} schedules by {username}")
            return {
                'message': f'Найдено {len(schedules)} записей расписания.',
                'schedules': schedules_list
            }, 200

        except Exception as e:
            logging.error(f"GET /api/admin/schedules - Error: {str(e)}")
            return {'description': f"Внутренняя ошибка сервера: {str(e)}"}, 500

        finally:
            db_sess.close()