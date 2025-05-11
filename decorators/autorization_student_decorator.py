from flask import request, abort
from flask_login import current_user
import logging
from functools import wraps
from data import db_session
from data.student import Student
from data.user import User


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


def student_authorization_required(endpoint, method="GET"):
    """Декоратор для проверки авторизации администратора (через сессию или API-ключ)."""
    def decorator(f):
        @wraps(f)
        def wrapped_function(*args, **kwargs):
            client_ip = request.remote_addr
            full_endpoint = f"{method} {endpoint}"

            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                username = current_user.username
                logging.info(f"{full_endpoint} - IP: {client_ip}, User: {username} (via session)")

                db_sess = db_session.create_session()
                try:
                    admin_user = (db_sess.query(User)
                                  .join(Student, User.user_id == Student.user_id)
                                  .filter(User.username == username)
                                  .first())
                    if not admin_user:
                        logging.error(f"{full_endpoint} - Access denied for user {username} (not an admin)")
                        abort(403, description="Доступ запрещен: пользователь не является учеником.")
                finally:
                    db_sess.close()

                kwargs['username'] = username
                return f(*args, **kwargs)

            api_key = request.headers.get('X-API-Key')
            if api_key:
                db_sess = db_session.create_session()
                try:
                    user = (db_sess.query(User)
                            .join(Student, User.user_id == Student.user_id)
                            .filter(User.api_key == api_key)
                            .first())
                    if user:
                        logging.info(f"{full_endpoint} - IP: {client_ip}, User: {user.username} (via API key)")
                        kwargs['username'] = user.username
                        return f(*args, **kwargs)
                finally:
                    db_sess.close()

            logging.error(f"{full_endpoint} - Unauthorized access from IP: {client_ip}")
            abort(401, description="Необходима авторизация: предоставьте валидную сессию или API-ключ.")

        return wrapped_function
    return decorator