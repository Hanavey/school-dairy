import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class TeacherPositionAssignment(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'teacher_position_assignments'

    teacher_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teachers.teacher_id"), primary_key=True)
    position_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teacher_positions.position_id"),
                                    primary_key=True)
    class_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("classes.class_id"), nullable=True)
    subject_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("subjects.subject_id"), nullable=True)

    teacher = orm.relationship("Teacher", back_populates="positions")

    def __repr__(self):
        return (f'<teacher_position_assignments> teacher_id={self.teacher_id} | position_id={self.position_id} | '
                f'class_id={self.class_id} | subject_id={self.subject_id}')