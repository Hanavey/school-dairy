from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class CreateSubjectForm(FlaskForm):
    """Форма для создания предмета"""
    subject_name = StringField('Название предмета', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Создать')

class EditSubjectForm(FlaskForm):
    """Форма для редактирования предмета"""
    subject_name = StringField('Название предмета', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Сохранить')