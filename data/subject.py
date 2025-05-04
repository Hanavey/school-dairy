import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Subject(SqlAlchemyBase, SerializerMixin):
    """Таблица для предметов"""
    __tablename__ = 'subjects'

    subject_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    subject_name = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)

    homeworks = orm.relationship("Homework", back_populates="subject")
    grades = orm.relationship("Grade", back_populates="subject")

    def __repr__(self):
        return f'<subjects> subject_id={self.subject_id} | subject_name={self.subject_name}'