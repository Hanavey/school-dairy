from flask_restful import Resource, reqparse, request
from data import db_session
from data.user import User
from decorators.authorization_decorator import check_api_key
import logging
import base64

logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    encoding='utf-8'
)

class UserSettingsAPI(Resource):
    settings_parser = reqparse.RequestParser()
    settings_parser.add_argument('first_name', type=str)
    settings_parser.add_argument('last_name', type=str)
    settings_parser.add_argument('email', type=str)
    settings_parser.add_argument('phone_number', type=str)
    settings_parser.add_argument('password', type=str)

    @check_api_key
    def get(self, user_id, username=None):
        """Получение данных профиля пользователя."""
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.user_id == user_id).first()
            if not user:
                logging.error(f'GET /api/user/settings/{user_id} - Not found for user {username}')
                return {'description': f'Пользователь с id {user_id} не найден.'}, 404

            if user.username != username:
                logging.error(f'GET /api/user/settings/{user_id} - Access denied for user {username}')
                return {'description': 'Вы можете просматривать только свой профиль.'}, 403

            logging.info(f'GET /api/user/settings/{user_id} - Retrieved by user {username}')
            return {
                'user': {
                    'user_id': user.user_id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'profile_picture': user.profile_picture
                }
            }, 200

        except Exception as e:
            logging.error(f"GET /api/user/settings/{user_id} - Error: {str(e)}")
            return {'description': f"Ошибка при получении данных профиля: {str(e)}"}, 500

        finally:
            db_sess.close()

    @check_api_key
    def patch(self, user_id, username=None, update_data=None):
        """Обновление профиля пользователя."""
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.user_id == user_id).first()
            if not user:
                logging.error(f'PATCH /api/user/settings/{user_id} - Not found for user {username}')
                return {'description': f'Пользователь с id {user_id} не найден.'}, 404

            if user.username != username:
                logging.error(f'PATCH /api/user/settings/{user_id} - Access denied for user {username}')
                return {'description': 'Вы можете редактировать только свой профиль.'}, 403

            if update_data is not None:
                args = update_data
            else:
                content_type = request.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    args = self.settings_parser.parse_args()
                elif 'multipart/form-data' in content_type:
                    args = {}
                    for key in ['first_name', 'last_name', 'email', 'phone_number', 'password']:
                        if key in request.form:
                            args[key] = request.form[key]
                    if 'profile_picture' in request.files:
                        file = request.files['profile_picture']
                        if file:
                            image_data = base64.b64encode(file.read()).decode('utf-8')
                            args['profile_picture'] = image_data
                else:
                    return {'description': "Unsupported Content-Type. Use 'application/json' or 'multipart/form-data'."}, 415

            updated_fields = {}
            if args.get('first_name'):
                user.first_name = args['first_name']
                updated_fields['first_name'] = user.first_name
            if args.get('last_name'):
                user.last_name = args['last_name']
                updated_fields['last_name'] = user.last_name
            if args.get('email'):
                user.email = args['email']
                updated_fields['email'] = user.email
            if args.get('phone_number'):
                user.phone_number = args['phone_number']
                updated_fields['phone_number'] = user.phone_number
            if args.get('password'):
                user.set_password(args['password'])
                updated_fields['password'] = 'updated'
            if 'profile_picture' in args:
                user.profile_picture = args['profile_picture']
                updated_fields['profile_picture'] = 'updated'

            if not updated_fields:
                return {'description': 'No fields to update'}, 400

            db_sess.commit()
            logging.info(f'PATCH /api/user/settings/{user_id} - Updated by user {username}: {updated_fields}')
            return {
                'message': f'Профиль пользователя {user_id} успешно обновлен.',
                'user_id': user_id,
                'updated_fields': updated_fields
            }, 200

        except Exception as e:
            db_sess.rollback()
            logging.error(f"PATCH /api/user/settings/{user_id} - Error: {str(e)}")
            return {'description': f"Ошибка при обновлении профиля: {str(e)}"}, 500

        finally:
            db_sess.close()