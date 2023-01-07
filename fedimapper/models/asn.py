from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .base import Base


class ASN(Base):
    __tablename__ = "asn"

    asn = Column(String, primary_key=True)
    cc = Column(String, nullable=True)
    company = Column(String, nullable=True, index=True)
    owner = Column(String, nullable=True)
    prefix = Column(String, nullable=True)
