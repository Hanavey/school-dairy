import sqlalchemy
from sqlalchemy import orm
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash
import uuid


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    user_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    password_hash = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    first_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    last_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=True, unique=True)
    phone_number = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    profile_picture = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    api_key = sqlalchemy.Column(sqlalchemy.String, nullable=True, unique=True)

    # Связь с таблицами Teachers и Students
    teacher = orm.relationship("Teacher", back_populates="user", uselist=False)
    student = orm.relationship("Student", back_populates="user", uselist=False)
    admin_ = orm.relationship("Admin", back_populates="user", uselist=False)

    def __repr__(self):
        return (f'<users> user_id={self.user_id} | username={self.username} | password_hash={self.password_hash} | '
                f'first_name={self.first_name} | last_name={self.last_name} | email={self.email} | '
                f'phone_number={self.phone_number}')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        self.api_key = str(uuid.uuid4())  # Генерируем уникальный API-ключ
        return self.api_key

    def get_id(self):
        return str(self.user_id)
