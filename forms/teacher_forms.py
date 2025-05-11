from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, StringField, DateField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, AnyOf, Optional
from wtforms.fields import FieldList, FormField
from datetime import datetime

class GradeEntry(FlaskForm):
    date = HiddenField('Дата', validators=[DataRequired()])
    grade = IntegerField('Оценка', validators=[Optional(), NumberRange(min=2, max=5)])

class AttendanceEntry(FlaskForm):
    date = HiddenField('Дата', validators=[DataRequired()])
    status = SelectField('Статус', choices=[('присутствовал', 'Присутствовал'), ('отсутствовал', 'Отсутствовал')], validators=[Optional()])

class StudentRowForm(FlaskForm):
    student_id = HiddenField('Студент', validators=[DataRequired()])
    grades = FieldList(FormField(GradeEntry), min_entries=0)
    attendance = FieldList(FormField(AttendanceEntry), min_entries=0)
    submit = SubmitField('Сохранить')

class GradeForm(FlaskForm):
    student_id = SelectField('Студент', coerce=int, validators=[DataRequired()])
    grade = IntegerField('Оценка', validators=[DataRequired(), NumberRange(min=2, max=5)])
    date = DateField('Дата', format='%Y-%m-%d', validators=[DataRequired()])
    class_id = HiddenField('Класс', validators=[DataRequired()])
    subject_id = HiddenField('Предмет', validators=[DataRequired()])
    submit = SubmitField('Добавить')

class AttendanceForm(FlaskForm):
    student_id = SelectField('Студент', coerce=int, validators=[DataRequired()])
    status = SelectField('Статус', choices=[('присутствовал', 'Присутствовал'), ('отсутствовал', 'Отсутствовал')], validators=[DataRequired()])
    date = DateField('Дата', format='%Y-%m-%d', validators=[DataRequired()])
    class_id = HiddenField('Класс', validators=[DataRequired()])
    subject_id = HiddenField('Предмет', validators=[DataRequired()])
    submit = SubmitField('Добавить')

class HomeworkForm(FlaskForm):
    task = StringField('Задание', validators=[DataRequired()])
    due_date = DateField('Срок сдачи', format='%Y-%m-%d', validators=[DataRequired()])
    class_id = HiddenField('Класс', validators=[DataRequired()])
    subject_id = HiddenField('Предмет', validators=[DataRequired()])
    submit = SubmitField('Добавить')

class LessonDateForm(FlaskForm):
    date = DateField('Дата урока', format='%Y-%m-%d', default=datetime.now(), validators=[DataRequired()])
    submit = SubmitField('Добавить урок')

class DeleteGradeForm(FlaskForm):
    grade_id = HiddenField('ID оценки', validators=[DataRequired()])
    submit = SubmitField('Удалить')