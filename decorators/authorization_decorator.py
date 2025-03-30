from functools import wraps
from flask import request, current_app
from flask_login import current_user
from data import db_session
from data.user import User
import logging


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    encoding='utf-8'
)


def check_api_key(f):
    """
    Декоратор для проверки авторизации
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Если пользователь аутентифицирован через Flask-Login
        if current_user.is_authenticated:
            kwargs['username'] = current_user.username
            return f(*args, **kwargs)

        # Получаем API ключ из разных источников
        api_key = (
            request.headers.get('X-API-Key') or
            request.args.get('api_key') or
            request.form.get('api_key')
        )

        if not api_key:
            logging.error("API key not provided in request")
            return {'description': 'API key is required'}, 401

        db_sess = db_session.create_session()

        try:
            user = db_sess.query(User).filter(User.api_key == api_key).first()
            if not user:
                logging.error(f"Invalid API key: {api_key}")
                return {'description': 'Invalid API key'}, 401

            # Передаём username в метод
            kwargs['username'] = user.username
            return f(*args, **kwargs)

        except Exception as e:
            logging.error(f"Database error during API key validation: {str(e)}")
            return {'description': 'Internal server error'}, 500

        finally:
            db_sess.close()

    return decorated_function