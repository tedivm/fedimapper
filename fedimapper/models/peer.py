from sqlalchemy import Column, ForeignKey, Integer, String

from .base import Base
from .instance import Instance


class Peer(Base):
    __tablename__ = "peers"

    host = Column(ForeignKey(Instance.host), primary_key=True, nullable=False)
    peer_host = Column(ForeignKey(Instance.host), primary_key=True, nullable=False)
    ingest_id = Column(String, nullable=False)
