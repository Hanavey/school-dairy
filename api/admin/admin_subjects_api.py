from flask_restful import Resource, reqparse, request
from data import db_session
from data.subject import Subject
from decorators.authorization_admin_decorator import admin_authorization_required
import logging


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    encoding='utf-8'
)


class AdminSubjectApi(Resource):
    """Класс для api одного предмета"""
    subject_pars = reqparse.RequestParser()
    subject_pars.add_argument('subject_name', type=str, required=True)

    subject_patch = reqparse.RequestParser()
    subject_patch.add_argument('subject_name', type=str)

    @admin_authorization_required('api/admin/subject/<subject_id>', method='GET')
    def get(self, subject_id, username=None):
        db_sess = db_session.create_session()
        try:
            subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()

            if not subject:
                logging.error(f'GET /api/admin/subject/{subject_id} - Not found for user {username}')
                return {'description': f'Предмет с id {subject_id} не найден.'}, 404

            logging.info(f'GET /api/admin/subject/{subject_id} - Retrieved by user {username}')
            return {
                'Subject': {
                    'subject_id': subject_id,
                    'subject_name': subject.subject_name
                }
            }, 200

        except Exception as e:
            logging.error(f"GET /api/admin/subject/{subject_id} - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных предмета: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required('api/admin/subject', method='POST')
    def post(self, username=None, subject_name=None):
        db_sess = db_session.create_session()
        try:
            if subject_name is not None:
                subject_name = subject_name['subject_name']
            else:
                content_type = request.headers.get('Content-Type', '')
                if 'multipart/form-data' in content_type:
                    subject_name = request.form.get('subject_name')
                    if not subject_name:
                        return {'description': 'Field subject_name is required'}, 400
                else:
                    try:
                        args = self.subject_pars.parse_args()
                        subject_name = args['subject_name']
                    except Exception as e:
                        return {'description': f'Validation error: {str(e)}'}, 400

            existing_subject = db_sess.query(Subject).filter(Subject.subject_name == subject_name).first()
            if existing_subject:
                return {'description': f'Subject with name "{subject_name}" already exists'}, 400

            new_subject = Subject(subject_name=subject_name)
            db_sess.add(new_subject)
            db_sess.commit()

            logging.info(f'POST /api/admin/subject - Subject "{subject_name}" created successfully by user {username}')
            return {
                'message': 'Предмет добавлен успешно.',
                'subject': {
                    'subject_id': new_subject.subject_id,
                    'subject_name': new_subject.subject_name
                }
            }, 201

        except Exception as e:
            db_sess.rollback()
            logging.error(f"POST /api/admin/subject - Error: {str(e)}")
            return {'description': f"Ошибка при создании предмета: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required('api/admin/subject/<subject_id>', method='PATCH')
    def patch(self, subject_id, username=None, update_data=None):
        db_sess = db_session.create_session()
        try:
            subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
            if not subject:
                logging.error(f'PATCH /api/admin/subject/{subject_id} - Not found for user {username}')
                return {'description': f'Предмет с id {subject_id} не найден.'}, 404

            if update_data is not None:
                args = update_data
            else:
                content_type = request.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    args = self.subject_patch.parse_args()
                elif 'multipart/form-data' in content_type:
                    args = {}
                    if 'subject_name' in request.form:
                        args['subject_name'] = request.form['subject_name']
                else:
                    return {
                        'description': "Unsupported Content-Type. Use 'application/json' or 'multipart/form-data'."}, 415

            updated_fields = {}
            if args.get('subject_name') is not None:
                existing_subject = db_sess.query(Subject).filter(
                    Subject.subject_name == args['subject_name'],
                    Subject.subject_id != subject_id
                ).first()
                if existing_subject:
                    return {'description': f'Subject with name "{args["subject_name"]}" already exists'}, 400
                subject.subject_name = args['subject_name']
                updated_fields['subject_name'] = subject.subject_name

            if not updated_fields:
                return {'description': 'No fields to update'}, 400

            db_sess.commit()
            logging.info(f'PATCH /api/admin/subject/{subject_id} - Updated by user {username}: {updated_fields}')
            return {
                'message': f'Предмет {subject_id} успешно обновлен.',
                'subject_id': subject_id,
                'updated_fields': updated_fields
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PATCH /api/admin/subject/{subject_id} - Error: {str(e)}")
            return {'description': f"Ошибка при обновлении предмета: {str(e)}"}, 500

        finally:
            db_sess.close()

    @admin_authorization_required('api/admin/subject/<subject_id>', method='DELETE')
    def delete(self, subject_id, username=None):
        db_sess = db_session.create_session()
        try:
            subject = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
            if not subject:
                logging.error(f'DELETE /api/admin/subject/{subject_id} - Not found for user {username}')
                return {'description': f'Предмет {subject_id} не найден'}, 404

            if subject.grades or subject.homeworks:
                return {
                    'description': 'Нельзя удалить предмет, так как он связан с оценками или домашними заданиями.'}, 400

            db_sess.delete(subject)
            db_sess.commit()

            logging.info(f'DELETE /api/admin/subject/{subject_id} - Deleted successfully by user {username}')
            return {
                'message': f'Предмет {subject_id} успешно удален.',
                'subject_id': subject_id
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"DELETE /api/admin/subject/{subject_id} - Error: {str(e)}")
            return {'description': f"Ошибка при удалении предмета: {str(e)}"}, 500

        finally:
            db_sess.close()


class AdminSubjectsApi(Resource):
    """Класс для api всех предметов"""
    @admin_authorization_required('api/admin/subjects', method='GET')
    def get(self, username=None):
        db_sess = db_session.create_session()
        try:
            subjects = db_sess.query(Subject).all()

            if not subjects:
                logging.info(f'GET /api/admin/subjects - No subjects found by {username}')
                return {'message': 'Список предметов пуст', 'subjects': []}, 200

            subjects_list = []
            for subject in subjects:
                subjects_list.append({'subject_id': subject.subject_id, 'subject_name': subject.subject_name})

            logging.info(f"GET /api/admin/subjects - Retrieved {len(subjects)} subjects by {username}")
            return {
                'message': f'Найдено {len(subjects)} предметов',
                'subjects': subjects_list
            }, 200

        except Exception as e:
            logging.error(f"GET /api/admin/subjects - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных предметов: {str(e)}"}, 500

        finally:
            db_sess.close()