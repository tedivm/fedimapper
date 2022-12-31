from sqlalchemy import JSON, Column, ForeignKey, String

from .base import Base
from .instance import Instance


class Ban(Base):
    __tablename__ = "bans"

    host = Column(ForeignKey(Instance.host), primary_key=True, nullable=False)
    ingest_id = Column(String, nullable=False)
    banned_host = Column(ForeignKey(Instance.host), primary_key=True, nullable=False)
    digest = Column(String, index=True)
    severity = Column(String, nullable=False)
    comment = Column(String)
    keywords = Column(JSON)
