import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Schedule(SqlAlchemyBase, SerializerMixin):
    """Таблица для расписания"""
    __tablename__ = 'schedule'

    schedule_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    class_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("classes.class_id"), nullable=False)
    subject_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("subjects.subject_id"), nullable=False)
    teacher_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("teachers.teacher_id"), nullable=False)
    day_of_week = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    start_time = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    end_time = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    class_ = orm.relationship("Class", back_populates="schedule")
    subject = orm.relationship("Subject")
    teacher = orm.relationship("Teacher", back_populates="schedules")

    def __repr__(self):
        return (f'<schedule> schedule_id={self.schedule_id} | class_id={self.class_id} | subject_id={self.subject_id} '
                f'| teacher_id={self.teacher_id} | day_of_week={self.day_of_week} | start_time={self.start_time} | '
                f'end_time={self.end_time}')