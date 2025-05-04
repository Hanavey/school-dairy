import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Admin(SqlAlchemyBase, SerializerMixin):
    """Таблица с администраторами"""
    __tablename__ = 'admins'

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.user_id"), primary_key=True)
    admin_id = sqlalchemy.Column(sqlalchemy.Integer, unique=True, nullable=False)

    user = orm.relationship("User", back_populates="admin_")

    def __repr__(self):
        return f'<teachers> user_id={self.user_id} | admin_id={self.admin_id}'