from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class AddressSearchForm(FlaskForm):
    address = StringField('Адрес школы', validators=[DataRequired(message='Введите адрес')])
    submit = SubmitField('Найти')