import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class Student(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'students'

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.user_id"), primary_key=True)
    student_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, unique=True)
    class_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("classes.class_id"), nullable=False)
    birth_date = sqlalchemy.Column(sqlalchemy.Date, nullable=True)
    address = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    user = orm.relationship("User", back_populates="student")
    class_ = orm.relationship("Class", back_populates="students")
    grades = orm.relationship("Grade", back_populates="student")
    attendance = orm.relationship("Attendance", back_populates="student")

    def __repr__(self):
        return (f'<students> user_id={self.user_id} | student_id={self.student_id} | class_id={self.class_id} | '
                f'birth_date={self.birth_date} | address={self.address}')