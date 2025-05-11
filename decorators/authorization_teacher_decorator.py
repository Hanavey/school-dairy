from flask import request, abort
from flask_login import current_user
import logging
from functools import wraps
from data import db_session
from data.teacher import Teacher
from data.user import User
from data.teacher_position_assignment import TeacherPositionAssignment
from data.teacher_position import TeacherPosition

logging.basicConfig(
    filename='api_access.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

def teacher_authorization_required(endpoint, method="GET"):
    """Декоратор для проверки авторизации учителя (через сессию или API-ключ) и получения роли."""
    def decorator(f):
        @wraps(f)
        def wrapped_function(*args, **kwargs):
            client_ip = request.remote_addr
            full_endpoint = f"{method} {endpoint}"

            db_sess = db_session.create_session()
            try:
                if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                    username = current_user.username
                    user = db_sess.query(User).filter(User.username == username).first()
                    if not user or not user.teacher:
                        logging.error(f"{full_endpoint} - Access denied for user {username} (not a teacher)")
                        abort(403, description="Доступ запрещен: пользователь не является учителем.")

                    position = (db_sess.query(TeacherPosition.position_name)
                                .join(TeacherPositionAssignment,
                                      TeacherPositionAssignment.position_id == TeacherPosition.position_id)
                                .filter(TeacherPositionAssignment.teacher_id == user.teacher.teacher_id)
                                .first())
                    position_name = position.position_name if position else None
                    if not position_name:
                        logging.error(f"{full_endpoint} - No position found for teacher {username}")
                        abort(403, description="Доступ запрещен: у учителя не указана должность.")

                    logging.info(f"{full_endpoint} - IP: {client_ip}, User: {username}, Role: {position_name} (via session)")
                    kwargs['username'] = username
                    kwargs['position_name'] = position_name
                    return f(*args, **kwargs)

                api_key = request.headers.get('X-API-Key')
                if api_key:
                    user = (db_sess.query(User)
                            .join(Teacher, User.user_id == Teacher.user_id)
                            .filter(User.api_key == api_key)
                            .first())
                    if not user:
                        logging.error(f"{full_endpoint} - Invalid API key from IP: {client_ip}")
                        abort(401, description="Необходима авторизация: недействительный API-ключ.")

                    position = (db_sess.query(TeacherPosition.position_name)
                                .join(TeacherPositionAssignment,
                                      TeacherPositionAssignment.position_id == TeacherPosition.position_id)
                                .filter(TeacherPositionAssignment.teacher_id == user.teacher.teacher_id)
                                .first())
                    position_name = position.position_name if position else None
                    if not position_name:
                        logging.error(f"{full_endpoint} - No position found for teacher {user.username}")
                        abort(403, description="Доступ запрещен: у учителя не указана должность.")

                    logging.info(f"{full_endpoint} - IP: {client_ip}, User: {user.username}, Role: {position_name} (via API key)")
                    kwargs['username'] = user.username
                    kwargs['position_name'] = position_name
                    return f(*args, **kwargs)

                logging.error(f"{full_endpoint} - Unauthorized access from IP: {client_ip}")
                abort(401, description="Необходима авторизация: предоставьте валидную сессию или API-ключ.")

            finally:
                db_sess.close()

        return wrapped_function
    return decorator