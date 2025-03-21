import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class Teacher(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'teachers'

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.user_id"), primary_key=True)
    teacher_id = sqlalchemy.Column(sqlalchemy.Integer, unique=True, nullable=False)

    user = orm.relationship("User", back_populates="teacher")
    classes = orm.relationship("Class", back_populates="teacher")
    schedules = orm.relationship("Schedule", back_populates="teacher")
    positions = orm.relationship("TeacherPositionAssignment", back_populates="teacher")

    def __repr__(self):
        return f'<teachers> user_id={self.user_id} | teacher_id={self.teacher_id}'