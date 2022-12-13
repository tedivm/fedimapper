from sqlalchemy import Column, String

from .base import Base


class Evil(Base):
    __tablename__ = "evil"

    domain = Column(String, primary_key=True, nullable=False)
