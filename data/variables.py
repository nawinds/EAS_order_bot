import sqlalchemy
from .db_session import SqlAlchemyBase


class Variable(SqlAlchemyBase):
    __tablename__ = 'variables'

    name = sqlalchemy.Column(sqlalchemy.String,
                             primary_key=True, index=True, unique=True)
    value = sqlalchemy.Column(sqlalchemy.String)
