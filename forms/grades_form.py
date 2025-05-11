from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, HiddenField
from wtforms.validators import Optional, Length
from flask import request

class GradesForm(FlaskForm):
    """Форма для управления оценками, посещаемостью и домашними заданиями."""
    homework_id = HiddenField('ID домашнего задания', validators=[Optional()])
    homework_task = StringField('Задание', validators=[Optional(), Length(max=500)])
    homework_due_date = DateField('Срок сдачи', format='%Y-%m-%d', validators=[Optional()])
    new_date = DateField('Добавить дату', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Сохранить')
    add_date = SubmitField('Добавить дату')

    def validate(self):
        # Базовая валидация WTForms
        if not super(GradesForm, self).validate():
            return False

        # Проверяем, есть ли данные в форме или динамических полях
        has_data = (
            self.homework_task.data or
            self.homework_due_date.data or
            self.new_date.data or
            any(key.startswith('grade_') or key.startswith('attendance_') for key in request.form)
        )
        if not has_data:
            self.submit.errors.append('Заполните хотя бы одно поле (оценка, посещаемость, домашнее задание или дата).')
            return False

        return True