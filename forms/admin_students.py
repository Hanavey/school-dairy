from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FileField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Optional
from flask_wtf.file import FileAllowed
from data import db_session
from data.classes import Class

class CreateStudentForm(FlaskForm):
    """Форма для создания студента"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    birth_date = DateField('Дата рождения', format='%Y-%m-%d', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    profile_picture = FileField('Фото профиля', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Создать')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_sess = db_session.create_session()
        self.class_id.choices = [(c.class_id, c.class_name) for c in db_sess.query(Class).all()]
        db_sess.close()

class EditStudentForm(FlaskForm):
    """Форма для редактирования информации о студенте"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль (оставьте пустым, если не меняете)', validators=[Optional()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    birth_date = DateField('Дата рождения', format='%Y-%m-%d', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    profile_picture = FileField('Фото профиля', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_sess = db_session.create_session()
        self.class_id.choices = [(c.class_id, c.class_name) for c in db_sess.query(Class).all()]
        db_sess.close()

class StudentSearchForm(FlaskForm):
    """Форма для поиска по студентам"""
    search = StringField('Поиск', validators=[Optional()])
    submit = SubmitField('Поиск')