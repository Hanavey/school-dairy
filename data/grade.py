import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Grade(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'grades'

    grade_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    student_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("students.user_id"), nullable=False)
    subject_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("subjects.subject_id"), nullable=False)
    grade = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)

    student = orm.relationship("Student", back_populates="grades")
    subject = orm.relationship("Subject", back_populates="grades")

    def __repr__(self):
        return (f'<grades> grade_id={self.grade_id} | student_id={self.student_id} | subject_id={self.subject_id} | '
                f'grade={self.grade} | date={self.date}>')
