import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class Homework(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'homework'

    homework_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    subject_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("subjects.subject_id"), nullable=False)
    class_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("classes.class_id"), nullable=False)
    task = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    due_date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)

    subject = orm.relationship("Subject", back_populates="homeworks")
    class_ = orm.relationship("Class", back_populates="homeworks")

    def __repr__(self):
        return (f'<homework> homework_id={self.homework_id} | subject_id={self.subject_id} | class_id={self.class_id} '
                f'| task={self.task} | due_date={self.due_date}')