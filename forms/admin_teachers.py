from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Email, Optional
from flask_wtf.file import FileAllowed


class CreateTeacherForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    position_id = SelectField('Должность', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Класс (необязательно)', coerce=int, validators=[Optional()])
    subject_id = SelectField('Предмет (необязательно)', coerce=int, validators=[Optional()])
    profile_picture = FileField('Фото профиля', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Создать учителя')


class EditTeacherForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль (оставьте пустым, если не меняете)', validators=[Optional()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[DataRequired()])
    position_id = SelectField('Должность', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Класс (необязательно)', coerce=int, validators=[Optional()])
    subject_id = SelectField('Предмет (необязательно)', coerce=int, validators=[Optional()])
    profile_picture = FileField('Фото профиля', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')])
    submit = SubmitField('Сохранить изменения')