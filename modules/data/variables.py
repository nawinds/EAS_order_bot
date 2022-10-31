"""
Variables table in DB
"""
import sqlalchemy

from .db_session import SqlAlchemyBase


class Variable(SqlAlchemyBase):
    """
    Variable object linked to 'variables' table of DB
    """
    __tablename__ = 'variables'

    name = sqlalchemy.Column(sqlalchemy.String,
                             primary_key=True, index=True, unique=True)
    value = sqlalchemy.Column(sqlalchemy.String)
