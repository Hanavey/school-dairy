import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class TeacherSubjectLink(SqlAlchemyBase, SerializerMixin):
    """Таблица для соединения учителей и предметов"""
    __tablename__ = 'teacher_subject_links'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    assignment_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teacher_position_assignments.assignment_id"), nullable=False)
    subject_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("subjects.subject_id"), nullable=False)
    assignment = orm.relationship("TeacherPositionAssignment", back_populates="subject_links")
    subject = orm.relationship("Subject")

    def __repr__(self):
        return (f'<teacher_position_assignments> id={self.id} | assignment_id={self.assignment_id} | '
                f'subject_id={self.subject_id}')