import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class Attendance(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'attendance'

    attendance_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    student_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("students.user_id"), nullable=False)
    date = sqlalchemy.Column(sqlalchemy.Date, nullable=False)
    status = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    student = orm.relationship("Student", back_populates="attendance")

    def __repr__(self):
        return (f'<attendance> attendance_id={self.attendance_id} | student_id={self.student_id} | date={self.date} | '
                f'status={self.status}')