import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class Class(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'classes'

    class_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    class_name = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    teacher_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teachers.teacher_id"))

    teacher = orm.relationship("Teacher", back_populates="classes")
    students = orm.relationship("Student", back_populates="class_")
    schedule = orm.relationship("Schedule", back_populates="class_")
    homeworks = orm.relationship("Homework", back_populates="class_")

    def __repr__(self):
        return f'<classes> class_id={self.class_id} | class_name={self.class_name} | teacher_id={self.teacher_id}'