import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class TeacherPositionAssignment(SqlAlchemyBase, SerializerMixin):
    """Таблица для соединения учителей, должностей и предметов"""
    __tablename__ = 'teacher_position_assignments'

    assignment_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    teacher_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teachers.teacher_id"))
    position_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teacher_positions.position_id"))

    teacher = orm.relationship("Teacher", back_populates="positions")
    position = orm.relationship("TeacherPosition")
    subject_links = orm.relationship("TeacherSubjectLink", back_populates="assignment")

    def __repr__(self):
        return (f'<teacher_position_assignments> assignment_id={self.assignment_id} | teacher_id={self.teacher_id} | '
                f'position_id={self.position_id}')