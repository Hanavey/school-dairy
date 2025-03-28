from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FileField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Optional
from flask_wtf.file import FileAllowed


class CreateStudentForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    birth_date = DateField('Дата рождения (YYYY-MM-DD)', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    profile_picture = FileField('Фото профиля', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Создать ученика')


class EditStudentForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль (оставьте пустым, если не меняете)', validators=[Optional()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    birth_date = DateField('Дата рождения (YYYY-MM-DD)', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    profile_picture = FileField('Фото профиля', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Сохранить изменения')