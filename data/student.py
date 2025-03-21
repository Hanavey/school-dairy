import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class Student(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'students'

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.user_id"), primary_key=True)
    class_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("classes.class_id"), nullable=False)
    birth_date = sqlalchemy.Column(sqlalchemy.Date, nullable=True)
    address = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    user = orm.relationship("User", back_populates="student")
    class_ = orm.relationship("Class", back_populates="students")
    grades = orm.relationship("Grade", back_populates="student")
    attendance = orm.relationship("Attendance", back_populates="student")

    def __repr__(self):
        return (f'<students> user_id={self.user_id} | class_id={self.class_id} | birth_date={self.birth_date} | '
                f'address={self.address}')