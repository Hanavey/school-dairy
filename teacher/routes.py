from flask import render_template, redirect, flash, url_for, request, jsonify, current_app
from flask_login import current_user, login_user, logout_user
from teacher import teacher_bp
from data import db_session
from api.user_settings_api import UserSettingsAPI
from api.teacher.teacher_classes_api import TeacherClassesAPI
from api.teacher.teacher_list_api import TeacherListAPI
from api.teacher.teacher_subjects_for_class import TeacherSubjectsForClass
from api.teacher.teacher_grades_homework_attendance_api import GradeResource, AttendanceResource, HomeworkResource
from api.teacher.class_teacher_api import ClassTeacherResource
from api.teacher.teacher_schedule_api import TeacherScheduleResource
from api.teacher.teacher_excel_files import ClassExcelReportResource, ClassFullReportResource, TeacherScheduleExcelResource
from forms.user_settings import UserSettingsForm
from forms.class_form import ClassForm
from forms.add_students_form import AddStudentForm
from forms.login import LoginForm
from data.teacher import Teacher
from data.user import User
from data.teacher_position import TeacherPosition
from data.teacher_position_assignment import TeacherPositionAssignment
from data.classes import Class
from data.student import Student
from data.subject import Subject
from decorators.login_decorator import blueprint_login_required
import base64
import logging


logging.basicConfig(
    filename='routes.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)


@teacher_bp.route('/')
def index():
    """Базовая страница учителя"""
    return render_template('teacher/index.html')


@teacher_bp.route('/classes', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def classes():
    """Страница управления классами для учителей и завучей."""
    api = TeacherClassesAPI()
    response, status_code = api.get()
    classes_data = []
    if status_code == 200:
        classes_data = response.get('data', [])
        message = response.get('message', '')
    else:
        message = response.get('description', 'Ошибка при получении классов')

    print('\n\n', response.get('position_name', 'Предметник') == "Завуч", '\n\n')
    print(response)

    return render_template(
        'teacher/classes_list.html',
        form=ClassForm(),
        classes=classes_data,
        is_head_teacher=response.get('teacher_role', 'Предметник') == "Завуч",
        message=message
    )


@teacher_bp.route('/class/<int:class_id>')
@blueprint_login_required('teacher_bp')
def class_subjects(class_id):
    api = TeacherSubjectsForClass()
    response, status_code = api.get(class_id)
    return render_template('teacher/subjects_list.html', subjects=response.get('subjects', []), class_id=class_id)


@teacher_bp.route('/create_class', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def create_class():
    """Страница создания нового класса (доступно только завучам)."""
    api = TeacherListAPI()
    teachers_response, teachers_status = api.get()
    teachers = teachers_response.get('data', []) if teachers_status == 200 else []

    form = ClassForm()
    if form.validate_on_submit():
        class_data = {
            'class_name': form.class_name.data,
            'teacher_id': form.teacher_id.data,
            'students': []
        }
        api = TeacherClassesAPI()
        api.class_post_parser.parse_args = lambda: class_data
        response, status_code = api.post()
        if status_code == 201:
            flash('Класс успешно создан', 'success')
            return redirect(url_for('teacher.classes'))
        else:
            flash(response.get('description', 'Ошибка при создании класса'), 'danger')

    return render_template(
        'teacher/create_class.html',
        form=form,
        teachers=teachers,
        message='',
        status='success'
    )


@teacher_bp.route('/class/<int:class_id>/<int:subject_id>', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def class_management(class_id, subject_id):
    db_sess = db_session.create_session()
    try:
        class_obj = db_sess.query(Class).filter(Class.class_id == class_id).first()
        if not class_obj:
            return jsonify({"status": "error", "description": "Класс не найден"}), 404

        subject_obj = db_sess.query(Subject).filter(Subject.subject_id == subject_id).first()
        if not subject_obj:
            return jsonify({"status": "error", "description": "Предмет не найден"}), 404

        grade_resource = GradeResource()
        attendance_resource = AttendanceResource()
        homework_resource = HomeworkResource()

        grades_response = grade_resource.get(class_id=class_id)
        if grades_response[1] != 200:
            return jsonify(grades_response[0]), grades_response[1]

        attendance_response = attendance_resource.get(class_id=class_id)
        if attendance_response[1] != 200:
            return jsonify(attendance_response[0]), attendance_response[1]

        homework_response = homework_resource.get(class_id=class_id)
        if homework_response[1] != 200:
            return jsonify(homework_response[0]), homework_response[1]

        grades = [grade for grade in grades_response[0]['data'] if grade['subject_id'] == subject_id]
        attendance = attendance_response[0]['data']
        homeworks = [hw for hw in homework_response[0]['data'] if hw['subject_id'] == subject_id]

        students = db_sess.query(Student).filter(Student.class_id == class_id).all()
        students_data = [
            {
                'user_id': student.user_id,
                'full_name': f"{student.user.first_name} {student.user.last_name}"
            }
            for student in students
        ]

        if request.method == 'POST':
            action = request.form.get('action')

            def execute_in_test_context(resource, json_data, method='post'):
                """Выполняет запрос API в изолированном тестовом контексте"""
                with current_app.test_request_context(
                        '/api',
                        method='POST',
                        json=json_data,
                        headers={'Authorization': request.headers.get('Authorization', '')}
                ):
                    if method == 'post':
                        return resource.post()
                    elif method == 'put':
                        return resource.put()
                    elif method == 'delete':
                        return resource.delete()

            if action == 'add_grade':
                grade_data = {
                    'student_id': int(request.form.get('student_id')),
                    'subject_id': subject_id,
                    'grade': int(request.form.get('grade')),
                    'date': request.form.get('date')
                }
                response = execute_in_test_context(grade_resource, grade_data)
                return jsonify(response[0]), response[1]

            elif action == 'update_grade':
                grade_data = {
                    'grade_id': int(request.form.get('grade_id')),
                    'student_id': int(request.form.get('student_id')),
                    'subject_id': subject_id,
                    'grade': int(request.form.get('grade')),
                    'date': request.form.get('date')
                }
                response = execute_in_test_context(grade_resource, grade_data, 'put')
                return jsonify(response[0]), response[1]

            elif action == 'delete_grade':
                grade_id = int(request.form.get('grade_id'))
                with current_app.test_request_context(
                        f'/api/grades/{grade_id}',
                        method='DELETE',
                        headers={'Authorization': request.headers.get('Authorization', '')}
                ):
                    response = grade_resource.delete(grade_id=grade_id)
                return jsonify(response[0]), response[1]

            elif action == 'add_attendance':
                date = request.form.get('date')
                for student in students_data:
                    attendance_data = {
                        'student_id': student['user_id'],
                        'date': date,
                        'status': 'присутствовал'
                    }
                    response = execute_in_test_context(attendance_resource, attendance_data)
                    if response[1] != 201:
                        return jsonify(response[0]), response[1]
                return jsonify({"status": "success", "description": "Посещаемость добавлена"}), 201

            elif action == 'update_attendance':
                attendance_data = {
                    'attendance_id': int(request.form.get('attendance_id')),
                    'student_id': int(request.form.get('student_id')),
                    'date': request.form.get('date'),
                    'status': request.form.get('status')
                }
                response = execute_in_test_context(attendance_resource, attendance_data, 'put')
                return jsonify(response[0]), response[1]

            elif action == 'add_homework':
                homework_data = {
                    'subject_id': subject_id,
                    'class_id': class_id,
                    'task': request.form.get('task'),
                    'due_date': request.form.get('due_date')
                }
                response = execute_in_test_context(homework_resource, homework_data)
                return jsonify(response[0]), response[1]

        return render_template(
            'teacher/class_management.html',
            class_id=class_id,
            subject_id=subject_id,
            students=students_data,
            grades=grades,
            attendance=attendance,
            homeworks=homeworks,
            subject_name=subject_obj.subject_name
        )

    finally:
        db_sess.close()


@teacher_bp.route('/class/<int:class_id>/<int:subject_id>/excel_report', methods=['GET'])
@blueprint_login_required('teacher_bp')
def class_excel_report(class_id, subject_id):
    """Маршрут для скачивания Excel-файла с оценками и посещаемостью для указанного класса и предмета."""
    db_sess = db_session.create_session()
    try:
        api = ClassExcelReportResource()
        teacher = db_sess.query(Teacher).join(User).filter(User.user_id == current_user.user_id).first()
        if not teacher:
            logging.error(f"GET /class/{class_id}/{subject_id}/excel_report - Teacher not found for user {current_user.username}")
            flash('Учитель не найден', 'danger')
            return redirect(url_for('teacher.class_management', class_id=class_id, subject_id=subject_id))

        position = db_sess.query(TeacherPosition).join(TeacherPositionAssignment).filter(
            TeacherPositionAssignment.teacher_id == teacher.teacher_id
        ).first()
        position_name = position.position_name if position else 'Учитель'

        response = api.get(
            username=current_user.username,
            position_name=position_name,
            class_id=class_id,
            subject_id=subject_id
        )

        if isinstance(response, tuple):
            logging.error(f"GET /class/{class_id}/{subject_id}/excel_report - Error: {response[0]['description']}")
            flash(response[0]['description'], 'danger')
            return redirect(url_for('teacher.class_management', class_id=class_id, subject_id=subject_id))

        return response

    except Exception as e:
        logging.error(f"GET /class/{class_id}/{subject_id}/excel_report - Error: {str(e)} for user {current_user.username}")
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('teacher.class_management', class_id=class_id, subject_id=subject_id))
    finally:
        db_sess.close()


@teacher_bp.route('/add_students/<int:class_id>', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def add_students(class_id):
    """Страница добавления учеников в класс (доступно только завучам)."""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.user_id == current_user.user_id).first()
        is_head_teacher = False
        teacher = db_sess.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        if teacher:
            position = db_sess.query(TeacherPosition).join(TeacherPositionAssignment).filter(
                TeacherPositionAssignment.teacher_id == teacher.teacher_id,
                TeacherPosition.position_name == 'Завуч'
            ).first()
            is_head_teacher = bool(position)

        if not is_head_teacher:
            flash('Доступ запрещен: только завуч может добавлять учеников', 'danger')
            return redirect(url_for('teacher.classes'))

        class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
        if not class_:
            flash('Класс не найден', 'danger')
            return redirect(url_for('teacher.classes'))

        form = AddStudentForm()
        if form.validate_on_submit():
            student_data = {
                'students': [{
                    'username': form.username.data,
                    'first_name': form.first_name.data,
                    'last_name': form.last_name.data,
                    'email': form.email.data,
                    'password': form.password.data,
                    'birth_date': form.birth_date.data.strftime('%Y-%m-%d') if form.birth_date.data else None,
                    'phone_number': form.phone_number.data or None,
                    'address': form.address.data or None
                }]
            }
            logging.debug(f"Submitting student data for class {class_id}: {student_data}")
            api = TeacherClassesAPI()
            api.class_patch_parser.parse_args = lambda: student_data
            response, status_code = api.patch(class_id=class_id, username=user.username, position_name='Завуч')
            if status_code == 200:
                flash('Ученик успешно добавлен', 'success')
                return redirect(url_for('teacher.classes'))
            else:
                flash(response.get('description', 'Ошибка при добавлении ученика'), 'danger')
                logging.error(f"Failed to add student to class {class_id}: {response.get('description')}")
                return render_template(
                    'teacher/add_students.html',
                    form=form,
                    class_id=class_id,
                    class_name=class_.class_name,
                    message=response.get('description', 'Ошибка при добавлении ученика'),
                    status='error'
                )

        return render_template(
            'teacher/add_students.html',
            form=form,
            class_id=class_id,
            class_name=class_.class_name,
            message='',
            status='success'
        )

    except Exception as e:
        logging.error(f"Error in /add_students/{class_id}: {str(e)}")
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('teacher.classes'))
    finally:
        db_sess.close()


@teacher_bp.route('/confirm_delete/class/<int:class_id>', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def confirm_delete_class(class_id):
    """Страница для подтверждения удаления класса"""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.user_id == current_user.user_id).first()
        logging.debug(f"User {user.username} attempting to delete class {class_id}")

        is_head_teacher = False
        teacher = db_sess.query(Teacher).filter(Teacher.user_id == current_user.user_id).first()
        if teacher:
            position = db_sess.query(TeacherPosition).join(TeacherPositionAssignment).filter(
                TeacherPositionAssignment.teacher_id == teacher.teacher_id,
                TeacherPosition.position_name == 'Завуч'
            ).first()
            is_head_teacher = bool(position)

        if not is_head_teacher:
            logging.error(
                f"DELETE /confirm_delete/class/{class_id} - Access denied for user {user.username} (not a head teacher)")
            flash('Доступ запрещен: только завуч может удалять классы', 'danger')
            return redirect(url_for('teacher.classes'))

        class_ = db_sess.query(Class).filter(Class.class_id == class_id).first()
        if not class_:
            logging.error(f"DELETE /confirm_delete/class/{class_id} - Class not found by user {user.username}")
            flash('Класс не найден', 'danger')
            return redirect(url_for('teacher.classes'))

        if request.method == 'POST':
            logging.debug(f"POST request received for deleting class {class_id} by user {user.username}")
            api = TeacherClassesAPI()
            response, status = api.delete(class_id=class_id, username=user.username, position_name='Завуч')
            logging.debug(f"API response for DELETE class {class_id}: {response}, status: {status}")
            if status == 200:
                flash('Класс успешно удален', 'success')
                return redirect(url_for('teacher.classes'))
            else:
                flash(response.get('description', 'Ошибка при удалении класса'), 'danger')
                return redirect(url_for('teacher.classes'))

        return render_template(
            'teacher/confirm_delete.html',
            entity='Класс',
            id=class_id,
            class_name=class_.class_name,
            delete_url=url_for('teacher.confirm_delete_class', class_id=class_id),
            list_url=url_for('teacher.classes')
        )

    except Exception as e:
        logging.error(f"Error in /confirm_delete/class/{class_id}: {str(e)}")
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('teacher.classes'))
    finally:
        db_sess.close()


@teacher_bp.route('/my_schedule', methods=['GET'])
@blueprint_login_required('teacher_bp')
def my_schedule():
    """Страница для учителя: просмотр своего расписания."""
    api = TeacherScheduleResource()
    response, status_code = api.get(username=current_user.username, position_name='Учитель')

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении расписания'), 'danger')
        return redirect(url_for('teacher.index'))

    schedule_data = response.get('data', {})
    return render_template(
        'teacher/my_schedule.html',
        teacher_id=schedule_data.get('teacher_id'),
        schedule=schedule_data.get('schedule', [])
    )


@teacher_bp.route('/my_schedule/excel', methods=['GET'])
@blueprint_login_required('teacher_bp')
def my_schedule_excel():
    """Маршрут для скачивания Excel-файла с расписанием учителя."""
    db_sess = db_session.create_session()
    try:
        api = TeacherScheduleExcelResource()
        logging.debug(f"Calling TeacherScheduleExcelResource.get for user {current_user.username}")
        response = api.get()

        if isinstance(response, tuple):
            logging.error(f"GET /my_schedule/excel - Error: {response[0]['description']}")
            flash(response[0]['description'], 'danger')
            print('\n\n', response[0]['description'], 'danger', '\n\n')
            return redirect(url_for('teacher.my_schedule'))

        logging.info(f"Excel schedule successfully generated for user {current_user.username}")
        return response

    except Exception as e:
        logging.error(f"GET /my_schedule/excel - Error: {str(e)} for user {current_user.username}")
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('teacher.my_schedule'))
    finally:
        db_sess.close()


@teacher_bp.route('/settings', methods=['GET', 'POST'])
@blueprint_login_required('teacher_bp')
def settings():
    """Страница настроек аккаунта учителя."""
    form = UserSettingsForm()
    api = UserSettingsAPI()

    username = current_user.username

    if form.validate_on_submit():
        update_data = {
            'first_name': form.first_name.data,
            'last_name': form.last_name.data,
            'email': form.email.data,
            'phone_number': form.phone_number.data,
        }

        if form.profile_picture.data:
            file = form.profile_picture.data
            image_data = base64.b64encode(file.read()).decode('utf-8')
            update_data['profile_picture'] = image_data

        if form.password.data:
            update_data['password'] = form.password.data

        response, status_code = api.patch(current_user.user_id, username=username, update_data=update_data)
        if status_code == 200:
            return redirect('/teacher/')
        else:
            return render_template('teacher/settings.html', form=form,
                                   message=response.get('description', 'Ошибка при обновлении'))

    response, status_code = api.get(current_user.user_id, username=username)
    if status_code != 200:
        return render_template('teacher/settings.html', form=form,
                               message=response.get('description', 'Ошибка при получении данных профиля'))

    user_data = response['user']
    form.first_name.data = user_data['first_name']
    form.last_name.data = user_data['last_name']
    form.email.data = user_data['email']
    form.phone_number.data = user_data['phone_number']

    return render_template('teacher/settings.html', form=form)


@teacher_bp.route('/my_class', methods=['GET'])
@blueprint_login_required('teacher_bp')
def my_class():
    """Страница для классного руководителя: просмотр информации об учениках и расписании класса."""
    api = ClassTeacherResource()
    response, status_code = api.get(username=current_user.username, position_name='Классный руководитель')

    if status_code != 200:
        flash(response.get('description', 'Ошибка при получении данных'), 'danger')
        return redirect(url_for('teacher.index'))

    class_data = response.get('data', {})
    return render_template(
        'teacher/my_class.html',
        class_id=class_data.get('class_id'),
        class_name=class_data.get('class_name'),
        students=class_data.get('students', []),
        schedule=class_data.get('schedule', [])
    )


@teacher_bp.route('/my_class/full_report', methods=['GET'])
@blueprint_login_required('teacher_bp')
def my_class_full_report():
    """Маршрут для скачивания Excel-файла с полной информацией о классе классного руководителя."""
    db_sess = db_session.create_session()
    try:
        api = ClassFullReportResource()

        logging.debug(f"Calling ClassFullReportResource.get for user {current_user.username}")
        response = api.get()

        if isinstance(response, tuple):
            logging.error(f"GET /my_class/full_report - Error: {response[0]['description']}")
            flash(response[0]['description'], 'danger')
            print('\n\n', response[0]['description'], 'danger', '\n\n')
            return redirect(url_for('teacher.index'))

        logging.info(f"Full class report successfully generated for user {current_user.username}")
        return response

    except Exception as e:
        logging.error(f"GET /my_class/full_report - Error: {str(e)} for user {current_user.username}")
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('teacher.index'))
    finally:
        db_sess.close()


@teacher_bp.route('/generate_api_key', methods=['POST'])
@blueprint_login_required('teacher_bp')
def generate_api_key():
    """Генерация API-ключа для учителя."""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            flash('Пользователь не найден.', 'danger')
            return redirect(url_for('teacher.settings'))

        api_key = user.generate_api_key()
        db_sess.commit()
        logging.info(f"API key generated for teacher user_id={user.user_id}")
        return render_template('teacher/settings.html', form=UserSettingsForm(), api_key=api_key)
    except Exception as e:
        db_sess.rollback()
        logging.error(f"Error generating API key for teacher user_id={current_user.user_id}: {str(e)}")
        flash(f'Ошибка при генерации API-ключа: {str(e)}', 'danger')
        return redirect(url_for('teacher.settings'))
    finally:
        db_sess.close()


@teacher_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница регистрации учителя"""
    db_sess = db_session.create_session()
    try:
        if current_user.is_authenticated and db_sess.query(Teacher).filter(
                Teacher.user_id == current_user.user_id).first():
            return redirect('/teacher/')

        form = LoginForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(User).join(Teacher, User.user_id == Teacher.user_id).filter(
                User.username == form.username.data
            ).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect('/teacher/')
            return render_template('teacher/login.html', form=form, message='Неверный логин или пароль')
        return render_template('teacher/login.html', form=form)

    finally:
        db_sess.close()


@teacher_bp.route('/logout')
@blueprint_login_required('teacher_bp')
def logout():
    """Выход из аккаунта учителя"""
    logout_user()
    return redirect('/teacher/')