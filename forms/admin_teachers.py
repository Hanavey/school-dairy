from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, Optional
from flask_wtf.file import FileAllowed
from data import db_session
from data.classes import Class
from data.subject import Subject
from data.teacher_position import TeacherPosition

class CreateTeacherForm(FlaskForm):
    """Форма для создания учителя"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    position_id = SelectField('Должность', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[Optional()])
    subject_ids = SelectMultipleField('Предметы', coerce=int, validators=[Optional()])
    profile_picture = FileField('Фото профиля', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Создать')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_sess = db_session.create_session()
        self.position_id.choices = [(p.position_id, p.position_name) for p in db_sess.query(TeacherPosition).all()]
        self.class_id.choices = [(0, 'Не выбран')] + [(c.class_id, c.class_name) for c in db_sess.query(Class).all()]
        self.subject_ids.choices = [(0, 'Не выбран')] + [(s.subject_id, s.subject_name) for s in db_sess.query(Subject).all()]
        db_sess.close()

class EditTeacherForm(FlaskForm):
    """Форма для редактирования информации об учителе"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль (оставьте пустым, если не меняете)', validators=[Optional()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    position_id = SelectField('Должность', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[Optional()])
    subject_ids = SelectMultipleField('Предметы', coerce=int, validators=[Optional()])
    profile_picture = FileField('Фото профиля', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_sess = db_session.create_session()
        self.position_id.choices = [(p.position_id, p.position_name) for p in db_sess.query(TeacherPosition).all()]
        self.class_id.choices = [(0, 'Не выбран')] + [(c.class_id, c.class_name) for c in db_sess.query(Class).all()]
        self.subject_ids.choices = [(0, 'Не выбран')] + [(s.subject_id, s.subject_name) for s in db_sess.query(Subject).all()]
        db_sess.close()

class TeacherSearchForm(FlaskForm):
    """Форма для поиска по учителям"""
    search = StringField('Поиск', validators=[Optional()])
    submit = SubmitField('Поиск')