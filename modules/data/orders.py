"""
Order tables in DB
"""
import sqlalchemy
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .db_session import SqlAlchemyBase


class Order(SqlAlchemyBase):
    """
    Order object linked to 'orders' table of DB
    """
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True, index=True)
    customer = Column(Integer, default=0)
    amount = Column(Integer, default=0)
    total = Column(Integer, default=0)
    status = Column(Integer, default=0)
    origin_msg = Column(Integer, unique=True)
    new_msg = Column(Integer, unique=True)
    payment_msg = Column(Integer, unique=True)
    status_msg = Column(Integer, unique=True)

    stats = relationship("OrderStats", back_populates="order")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(SqlAlchemyBase):
    """
    Order products object linked to 'order_items' table of DB
    """
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    order_id = Column(sqlalchemy.Integer, ForeignKey("orders.id"), index=True)
    url = Column(String)

    order = relationship("Order", back_populates="items")


class OrderStats(SqlAlchemyBase):
    """
    Order stats object linked to 'order_stats' table of DB
    """
    __tablename__ = "order_stats"
    order_id = Column(sqlalchemy.Integer, ForeignKey("orders.id"), primary_key=True, unique=True, index=True)
    d_course = Column(Integer)
    comission = Column(Integer)
    total = Column(Integer)

    order = relationship("Order", back_populates="stats")
