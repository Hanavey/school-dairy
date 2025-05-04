from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class UserSettingsForm(FlaskForm):
    """Форма для изменения информации пользователя"""
    first_name = StringField('Имя', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Номер телефона', validators=[Optional(), Length(max=16)])
    profile_picture = FileField('Фото профиля', validators=[FileAllowed(['jpg', 'png'], 'Только изображения!')])
    password = PasswordField('Новый пароль', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Сохранить')
