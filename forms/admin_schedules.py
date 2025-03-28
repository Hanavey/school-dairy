from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp


class CreateScheduleForm(FlaskForm):
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


class EditScheduleForm(FlaskForm):
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