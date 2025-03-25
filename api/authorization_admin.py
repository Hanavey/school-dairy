from flask import request, abort
from flask_login import current_user
import logging
from data import db_session
from data.admin import Admin
from data.user import User


logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


def check_admin_authorization(endpoint, method="GET"):
    """
    Проверяет авторизацию пользователя (через сессию или API-ключ) и права администратора.
    Возвращает имя пользователя, если проверка пройдена.

    :param endpoint: Путь API (например, '/api/admin/students' или '/api/admin/student/3050')
    :param method: HTTP-метод (GET, POST, PATCH, DELETE и т.д.)
    :return: username (строка) — имя авторизованного администратора
    """
    client_ip = request.remote_addr
    full_endpoint = f"{method} {endpoint}"

    # Проверка авторизации через сессию (Flask-Login)
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        username = current_user.username
        logging.info(f"{full_endpoint} - IP: {client_ip}, User: {username} (via session)")

        db_sess = db_session.create_session()
        admin_user = (db_sess.query(User)
                      .join(Admin, User.user_id == Admin.user_id)
                      .filter(User.username == username)
                      .first())
        db_sess.close()

        if not admin_user:
            logging.error(f"{full_endpoint} - Access denied for user {username} (not an admin)")
            abort(403, description="Доступ запрещен: пользователь не является администратором.")

        return username

    api_key = request.headers.get('X-API-Key')
    if api_key:
        db_sess = db_session.create_session()
        user = (db_sess.query(User)
                .join(Admin, User.user_id == Admin.user_id)
                .filter(User.api_key == api_key)
                .first())
        db_sess.close()

        if user:
            logging.info(f"{full_endpoint} - IP: {client_ip}, User: {user.username} (via API key)")
            return user.username
    logging.error(f"{full_endpoint} - Unauthorized access from IP: {client_ip}")
    abort(401, description="Необходима авторизация: предоставьте валидную сессию или API-ключ.")
