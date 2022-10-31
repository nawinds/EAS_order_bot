"""
Database manager
"""
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

SqlAlchemyBase = dec.declarative_base()

__factory = None


def global_init(db_file):
    """
    Database initialisation. Creating DB file and tables
    :param db_file: path to DB file
    """
    global __factory

    if __factory:
        return

    if not db_file or not db_file.strip():
        raise Exception("DB file is not specified")

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    print(f"Connecting to DB on {conn_str}")

    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    from . import __all_models

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    """
    Creates DB session
    :return: DB session
    """
    global __factory
    return __factory()
