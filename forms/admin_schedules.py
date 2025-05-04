from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp, Optional
from data import db_session
from data.classes import Class
from data.subject import Subject
from data.teacher import Teacher


class CreateScheduleForm(FlaskForm):
    """Форма для создания записи расписания"""
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Предмет', coerce=int, validators=[DataRequired()])
    teacher_id = SelectField('Учитель', coerce=int, validators=[DataRequired()])
    day_of_week = SelectField('День недели', choices=[
        ('Monday', 'Понедельник'),
        ('Tuesday', 'Вторник'),
        ('Wednesday', 'Среда'),
        ('Thursday', 'Четверг'),
        ('Friday', 'Пятница'),
        ('Saturday', 'Суббота'),
        ('Sunday', 'Воскресенье')
    ], validators=[DataRequired()])
    start_time = StringField('Время начала (HH:MM)', validators=[
        DataRequired(),
        Regexp(r'^\d{2}:\d{2}$', message='Время должно быть в формате HH:MM')
    ])
    end_time = StringField('Время окончания (HH:MM)', validators=[
        DataRequired(),
        Regexp(r'^\d{2}:\d{2}$', message='Время должно быть в формате HH:MM')
    ])
    submit = SubmitField('Создать')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_sess = db_session.create_session()
        self.class_id.choices = [(c.class_id, c.class_name) for c in db_sess.query(Class).all()]
        self.subject_id.choices = [(s.subject_id, s.subject_name) for s in db_sess.query(Subject).all()]
        self.teacher_id.choices = [(t.teacher_id, f"{t.user.first_name} {t.user.last_name}") for t in db_sess.query(Teacher).join(Teacher.user).all()]
        db_sess.close()

class EditScheduleForm(FlaskForm):
    """Форма для редактирования записи расписания"""
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    subject_id = SelectField('Предмет', coerce=int, validators=[DataRequired()])
    teacher_id = SelectField('Учитель', coerce=int, validators=[DataRequired()])
    day_of_week = SelectField('День недели', choices=[
        ('Monday', 'Понедельник'),
        ('Tuesday', 'Вторник'),
        ('Wednesday', 'Среда'),
        ('Thursday', 'Четверг'),
        ('Friday', 'Пятница'),
        ('Saturday', 'Суббота'),
        ('Sunday', 'Воскресенье')
    ], validators=[DataRequired()])
    start_time = StringField('Время начала (HH:MM)', validators=[
        DataRequired(),
        Regexp(r'^\d{2}:\d{2}$', message='Время должно быть в формате HH:MM')
    ])
    end_time = StringField('Время окончания (HH:MM)', validators=[
        DataRequired(),
        Regexp(r'^\d{2}:\d{2}$', message='Время должно быть в формате HH:MM')
    ])
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_sess = db_session.create_session()
        self.class_id.choices = [(c.class_id, c.class_name) for c in db_sess.query(Class).all()]
        self.subject_id.choices = [(s.subject_id, s.subject_name) for s in db_sess.query(Subject).all()]
        self.teacher_id.choices = [(t.teacher_id, f"{t.user.first_name} {t.user.last_name}") for t in db_sess.query(Teacher).join(Teacher.user).all()]
        db_sess.close()

class ScheduleSearchForm(FlaskForm):
    """Форма для поиска по расписанию"""
    teacher = StringField('Учитель', validators=[Optional()])
    class_name = StringField('Класс', validators=[Optional()])
    subject = StringField('Предмет', validators=[Optional()])
    time = StringField('Время', validators=[Optional(), Regexp(r'^\d{2}:\d{2}$', message="Формат времени должен быть HH:MM")])
    day = StringField('День недели', validators=[Optional()])
    submit = SubmitField('Фильтровать')