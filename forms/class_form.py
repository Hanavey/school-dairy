from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired


class ClassForm(FlaskForm):
    class_name = StringField('Название класса', validators=[DataRequired()])
    teacher_id = IntegerField('ID учителя', validators=[DataRequired()])
    submit = SubmitField('Создать')