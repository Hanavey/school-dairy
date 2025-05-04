from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from data import db_session
from data.teacher import Teacher
from data.user import User
from data.classes import Class
from data.teacher_position_assignment import TeacherPositionAssignment
from data.teacher_position import TeacherPosition
from data.subject import Subject
from data.teacher_subjects_link import TeacherSubjectLink
from data.schedule import Schedule
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


class AdminOneTeacherAPI(Resource):
    """Класс для api одного учителя"""
    one_teacher_patch = reqparse.RequestParser()
    one_teacher_patch.add_argument('username', type=str)
    one_teacher_patch.add_argument('password', type=str)
    one_teacher_patch.add_argument('first_name', type=str)
    one_teacher_patch.add_argument('last_name', type=str)
    one_teacher_patch.add_argument('email', type=str)
    one_teacher_patch.add_argument('phone_number', type=str)
    one_teacher_patch.add_argument('profile_picture', type=str)
    one_teacher_patch.add_argument('position_id', type=int)
    one_teacher_patch.add_argument('subject_id', type=int)

    one_teacher_post = reqparse.RequestParser()
    one_teacher_post.add_argument('username', type=str, required=True)
    one_teacher_post.add_argument('password', type=str, required=True)
    one_teacher_post.add_argument('first_name', type=str, required=True)
    one_teacher_post.add_argument('last_name', type=str, required=True)
    one_teacher_post.add_argument('email', type=str, required=True)
    one_teacher_post.add_argument('phone_number', type=str, required=True)
    one_teacher_post.add_argument('position_id', type=int, required=True)
    one_teacher_post.add_argument('subject_id', type=int)

    @admin_authorization_required("/api/admin/teacher/<teacher_id>", method="GET")
    def get(self, teacher_id, username=None):
        db_sess = db_session.create_session()
        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .options(joinedload(Teacher.classes))
                       .options(joinedload(Teacher.schedules))
                       .options(joinedload(Teacher.positions).joinedload(TeacherPositionAssignment.subject_links))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())

            if not teacher:
                logging.error(f"GET /api/admin/teacher/{teacher_id} - Not found for user {username}")
                return {'description': f'Учитель {teacher_id} не найден.'}, 404

            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                return {'description': "Ошибка: у учителя отсутствуют данные пользователя."}, 500

            classes = [{'class_id': cls.class_id, 'class_name': cls.class_name} for cls in teacher.classes]
            schedules = [{
                'schedule_id': sched.schedule_id,
                'class_id': sched.class_id,
                'subject_id': sched.subject_id,
                'day_of_week': sched.day_of_week,
                'start_time': sched.start_time,
                'end_time': sched.end_time
            } for sched in teacher.schedules]
            positions = [{
                'position_id': pos.position.position_id,
                'position_name': pos.position.position_name,
                'subjects': [{'subject_id': link.subject.subject_id, 'subject_name': link.subject.subject_name}
                             for link in pos.subject_links]
            } for pos in teacher.positions]

            class_id = classes[0]['class_id'] if classes else None

            teacher_data = {
                'Teacher': {
                    'user_id': teacher.user_id,
                    'teacher_id': teacher.teacher_id,
                    'username': teacher.user.username,
                    'first_name': teacher.user.first_name,
                    'last_name': teacher.user.last_name,
                    'email': teacher.user.email,
                    'phone_number': teacher.user.phone_number,
                    'profile_picture': teacher.user.profile_picture,
                    'api_key': teacher.user.api_key,
                    'class_id': class_id,
                    'classes': classes,
                    'schedules': schedules,
                    'positions': positions
                }
            }
            logging.info(
                f"GET /api/admin/teacher/{teacher_id} - Retrieved by user {username}, data size: {len(str(teacher_data))} bytes")
            return teacher_data, 200

        except Exception as e:
            logging.error(f"GET /api/admin/teacher/{teacher_id} - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных учителя: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required("/api/admin/teacher", method="POST")
    def post(self, username=None, update_data=None):
        db_sess = db_session.create_session()
        try:
            if update_data is not None:
                username_teacher = update_data.get('username')
                password = update_data.get('password')
                first_name = update_data.get('first_name')
                last_name = update_data.get('last_name')
                email = update_data.get('email')
                phone_number = update_data.get('phone_number')
                position_id = update_data.get('position_id')
                subject_ids = update_data.get('subject_ids', [])
                class_id = update_data.get('class_id')
                profile_picture = update_data.get('profile_picture')

                required_fields = {
                    'username': username_teacher,
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

                try:
                    position_id = int(position_id)
                except ValueError:
                    return {'description': 'position_id must be an integer'}, 400

                for subject_id in subject_ids:
                    try:
                        subject_id = int(subject_id)
                    except ValueError:
                        return {'description': f'subject_id {subject_id} must be an integer'}, 400

                if class_id:
                    try:
                        class_id = int(class_id)
                    except ValueError:
                        return {'description': 'class_id must be an integer'}, 400

            else:
                content_type = request.headers.get('Content-Type', '')
                if 'multipart/form-data' in content_type:
                    data = request.form
                    username_teacher = data.get('username')
                    password = data.get('password')
                    first_name = data.get('first_name')
                    last_name = data.get('last_name')
                    email = data.get('email')
                    phone_number = data.get('phone_number')
                    position_id = data.get('position_id')
                    subject_ids = data.getlist('subject_ids')
                    class_id = data.get('class_id')
                    profile_picture = None

                    if 'profile_picture' in request.files:
                        file = request.files['profile_picture']
                        if file and file.filename:
                            file_content = file.read()
                            profile_picture = base64.b64encode(file_content).decode('utf-8')

                    required_fields = ['username', 'password', 'first_name', 'last_name', 'email', 'phone_number',
                                       'position_id']
                    for field in required_fields:
                        if not data.get(field):
                            return {'description': f'Field {field} is required'}, 400

                    try:
                        position_id = int(position_id)
                    except ValueError:
                        return {'description': 'position_id must be an integer'}, 400

                    for subject_id in subject_ids:
                        try:
                            subject_id = int(subject_id)
                        except ValueError:
                            return {'description': f'subject_id {subject_id} must be an integer'}, 400

                    if class_id:
                        try:
                            class_id = int(class_id)
                        except ValueError:
                            return {'description': 'class_id must be an integer'}, 400

                else:
                    try:
                        args = self.one_teacher_post.parse_args()
                        username_teacher = args['username']
                        password = args['password']
                        first_name = args['first_name']
                        last_name = args['last_name']
                        email = args['email']
                        phone_number = args['phone_number']
                        position_id = args['position_id']
                        subject_ids = args.get('subject_ids', [])
                        class_id = args.get('class_id')
                        profile_picture = args.get('profile_picture')
                    except Exception as e:
                        return {'description': f'Validation error: {str(e)}'}, 400

            logging.info(f"POST /api/admin/teacher - Input data: {update_data}")

            position = db_sess.query(TeacherPosition).filter(TeacherPosition.position_id == position_id).first()
            if not position:
                return {'description': f'Position with position_id {position_id} does not exist'}, 400

            for subject_id in subject_ids:
                if subject_id:
                    subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
                    if not subject:
                        return {'description': f'Subject with subject_id {subject_id} does not exist'}, 400

            if class_id:
                class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
                if not class_:
                    return {'description': f'Class with class_id {class_id} does not exist'}, 400

            existing_user = db_sess.query(User).filter(
                (User.username == username_teacher) | (User.email == email)
            ).first()
            if existing_user:
                return {'description': 'User with this username or email already exists'}, 400

            max_teacher_id = db_sess.query(func.max(Teacher.teacher_id)).scalar() or 0
            new_teacher_id = max_teacher_id + 1

            with open('static/images/base.png', 'rb') as f:
                file_content = f.read()
                base_picture = base64.b64encode(file_content).decode('utf-8')

            new_user = User(
                username=username_teacher,
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

            new_teacher = Teacher(
                user_id=new_user.user_id,
                teacher_id=new_teacher_id
            )
            db_sess.add(new_teacher)
            db_sess.flush()

            if class_id:
                class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
                class_.teacher_id = new_teacher.teacher_id

            new_assignment = TeacherPositionAssignment(
                teacher_id=new_teacher.teacher_id,
                position_id=position_id
            )
            db_sess.add(new_assignment)
            db_sess.flush()

            for subject_id in subject_ids:
                if subject_id:
                    new_subject_link = TeacherSubjectLink(
                        assignment_id=new_assignment.assignment_id,
                        subject_id=subject_id
                    )
                    db_sess.add(new_subject_link)

            db_sess.commit()

            logging.info(f"POST /api/admin/teacher - Teacher {new_teacher.teacher_id} created by user {username}")
            return {
                'message': 'Учитель успешно создан.',
                'teacher': {
                    'user_id': new_user.user_id,
                    'teacher_id': new_teacher.teacher_id,
                    'username': new_user.username,
                    'email': new_user.email,
                    'position_id': position_id,
                    'class_id': class_id,
                    'subject_ids': subject_ids
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
        db_sess = db_session.create_session()
        try:
            teacher = (db_sess.query(Teacher)
                       .options(joinedload(Teacher.user))
                       .options(joinedload(Teacher.classes))
                       .options(joinedload(Teacher.positions))
                       .filter(Teacher.teacher_id == teacher_id)
                       .first())

            if not teacher:
                logging.error(f"PATCH /api/admin/teacher/{teacher_id} - Not found for user {username}")
                return {'description': f'Учитель {teacher_id} не найден.'}, 404

            if not teacher.user:
                logging.error(f"Teacher {teacher_id} has no associated User")
                return {'description': "Ошибка: у учителя отсутствуют данные пользователя."}, 500

            if update_data is not None:
                args = update_data
            else:
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
                    if 'subject_ids' in request.form:
                        args['subject_ids'] = request.form.getlist('subject_ids')
                else:
                    return {
                        'description': "Unsupported Content-Type. Use 'application/json' or 'multipart/form-data'."}, 415

            logging.info(f"PATCH /api/admin/teacher/{teacher_id} - Input data: {args}")

            user = teacher.user
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
                class_id = args['class_id']
                if class_id:
                    try:
                        class_id = int(class_id)
                    except ValueError:
                        return {'description': 'class_id must be an integer'}, 400
                    class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
                    if not class_:
                        return {'description': f'Class with class_id {class_id} does not exist'}, 400
                    existing_class = db_sess.query(Class).filter(Class.teacher_id == teacher.teacher_id).first()
                    if existing_class:
                        existing_class.teacher_id = None
                    class_.teacher_id = teacher.teacher_id
                    updated_fields['class_id'] = class_id

            if args.get('position_id') is not None:
                position = db_sess.query(TeacherPosition).filter(
                    TeacherPosition.position_id == args['position_id']).first()
                if not position:
                    return {'description': f"Position with ID {args['position_id']} not found"}, 400

                old_assignments = db_sess.query(TeacherPositionAssignment).filter(
                    TeacherPositionAssignment.teacher_id == teacher.teacher_id
                ).all()
                for assignment in old_assignments:
                    db_sess.query(TeacherSubjectLink).filter(
                        TeacherSubjectLink.assignment_id == assignment.assignment_id
                    ).delete()
                    db_sess.delete(assignment)

                position_assignment = TeacherPositionAssignment(
                    teacher_id=teacher.teacher_id,
                    position_id=args['position_id']
                )
                db_sess.add(position_assignment)
                db_sess.flush()

                if 'subject_ids' in args and args['subject_ids'] is not None:
                    subject_ids = args['subject_ids']
                    for subject_id in subject_ids:
                        try:
                            subject_id = int(subject_id)
                        except ValueError:
                            return {'description': f'subject_id {subject_id} must be an integer'}, 400
                        subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
                        if not subject:
                            return {'description': f"Subject with ID {subject_id} not found"}, 400

                    for subject_id in subject_ids:
                        if subject_id:
                            new_subject_link = TeacherSubjectLink(
                                assignment_id=position_assignment.assignment_id,
                                subject_id=subject_id
                            )
                            db_sess.add(new_subject_link)

                    updated_fields['subject_ids'] = subject_ids

                updated_fields['position_id'] = args['position_id']

            if not updated_fields:
                return {'description': 'No fields to update'}, 400

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

            schedules = db_sess.query(Schedule).filter(Schedule.teacher_id == teacher.teacher_id).count()
            classes = db_sess.query(Class).filter(Class.teacher_id == teacher.teacher_id).count()
            if schedules > 0 or classes > 0:
                logging.info(
                    f"DELETE /api/admin/teacher/{teacher_id} - Cannot delete: schedules={schedules}, classes={classes}")
                return {
                    'description': 'Нельзя удалить учителя, так как он связан с расписанием или классами.'
                }, 400

            assignments = db_sess.query(TeacherPositionAssignment).filter(
                TeacherPositionAssignment.teacher_id == teacher.teacher_id).all()
            for assignment in assignments:
                db_sess.query(TeacherSubjectLink).filter(
                    TeacherSubjectLink.assignment_id == assignment.assignment_id).delete()
                db_sess.delete(assignment)

            db_sess.delete(teacher.user)
            db_sess.delete(teacher)
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
    """Класс для api всех учителей"""
    @admin_authorization_required("/api/admin/teachers", method="GET")
    def get(self, username=None, **filters):
        db_sess = db_session.create_session()
        try:
            query = (db_sess.query(Teacher)
                     .options(joinedload(Teacher.user))
                     .options(joinedload(Teacher.classes))
                     .options(joinedload(Teacher.positions).joinedload(TeacherPositionAssignment.subject_links)))

            if filters and 'search' in filters:
                search_term = f"%{filters['search']}%"
                query = query.join(User).filter(
                    (User.first_name.ilike(search_term)) |
                    (User.last_name.ilike(search_term)) |
                    (func.concat(User.first_name, ' ', User.last_name).ilike(search_term))
                )
                logging.info(f"GET /api/admin/teachers - Search filter applied: {search_term}")

            teachers = query.all()
            if not teachers:
                logging.info(f"GET /api/admin/teachers - No teachers found by {username}")
                return {
                    'message': 'Список учителей пуст.',
                    'teachers': []
                }, 200

            teachers_list = []
            for teacher in teachers:
                if not teacher.user:
                    logging.warning(f"Teacher {teacher.teacher_id} has no associated user")
                    continue
                classes = [{'class_id': cls.class_id, 'class_name': cls.class_name} for cls in teacher.classes]
                positions = []
                for pos in teacher.positions:
                    subjects = [{
                        'subject_id': link.subject.subject_id,
                        'subject_name': link.subject.subject_name
                    } for link in pos.subject_links if link.subject] if pos.subject_links else []
                    positions.append({
                        'position_id': pos.position.position_id,
                        'position_name': pos.position.position_name,
                        'subjects': subjects
                    })
                teacher_data = {
                    'teacher_id': teacher.teacher_id,
                    'user_id': teacher.user_id,
                    'username': teacher.user.username if teacher.user else None,
                    'first_name': teacher.user.first_name if teacher.user else None,
                    'last_name': teacher.user.last_name if teacher.user else None,
                    'email': teacher.user.email if teacher.user else None,
                    'phone_number': teacher.user.phone_number if teacher.user else None,
                    'profile_picture': teacher.user.profile_picture if teacher.user else None,
                    'classes': classes,
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
