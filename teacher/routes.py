from flask import render_template
from flask_login import login_required, current_user
from teacher import teacher_bp
from data import db_session
from data.schedule import Schedule
from data.grade import Grade

@teacher_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'teacher':
        return "Доступ запрещен", 403
    db_sess = db_session.create_session()
    schedules = db_sess.query(Schedule).filter(Schedule.teacher_id == current_user.id).all()
    return render_template('dashboard.html', schedules=schedules)

@teacher_bp.route('/grade')
@login_required
def grade():
    if current_user.role != 'teacher':
        return "Доступ запрещен", 403
    db_sess = db_session.create_session()
    grades = db_sess.query(Grade).filter(Grade.teacher_id == current_user.id).all()
    return render_template('grade.html', grades=grades)