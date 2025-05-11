from flask import redirect, url_for
from flask_login import current_user
from functools import wraps


def blueprint_login_required(bp_name):
    """Декоратор для автоматического паренаправления на страницу регистрации"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if bp_name == 'admin_bp':
                    return redirect(url_for('admin.login'))
                elif bp_name == 'teacher_bp':
                    return redirect(url_for('teacher.login'))
                elif bp_name == 'students_bp':
                    return redirect(url_for('students.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator