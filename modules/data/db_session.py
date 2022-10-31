"""
Database manager
"""
import logging

import sqlalchemy as sa
import sqlalchemy.ext.declarative as dec
from sqlalchemy import orm
from sqlalchemy.orm import Session

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
        logging.critical("DB file is not specified")
        raise Exception("DB file is not specified")

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    logging.info(f"Connecting to DB on {conn_str}")

    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    """
    Creates DB session
    :return: DB session
    """
    global __factory
    return __factory()
