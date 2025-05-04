import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase

class TeacherPosition(SqlAlchemyBase, SerializerMixin):
    """Таблица для должностей"""
    __tablename__ = 'teacher_positions'

    position_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    position_name = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)

    def __repr__(self):
        return f'<teacher_positions> position_id={self.position_id} | position_name={self.position_name}'