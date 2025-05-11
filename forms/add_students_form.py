from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Regexp


class AddStudentForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    birth_date = DateField('Дата рождения (YYYY-MM-DD)', format='%Y-%m-%d', validators=[Optional()])
    phone_number = StringField('Номер телефона', validators=[Optional(), Regexp(r'^\+?\d{0,15}$', message="Неверный формат номера телефона")])
    address = StringField('Адрес', validators=[Optional()])
    submit = SubmitField('Добавить ученика')