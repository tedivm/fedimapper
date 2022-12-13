from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .base import Base


class Instance(Base):
    __tablename__ = "instances"

    host = Column(String, primary_key=True)
    last_ingest = Column(DateTime, nullable=True)
    last_ingest_status = Column(String, nullable=True)

    title = Column(String, nullable=True)
    short_description = Column(String, nullable=True)
    email = Column(String, nullable=True)
    version = Column(String, nullable=True)

    user_count = Column(Integer, nullable=True)
    status_count = Column(Integer, nullable=True)
    domain_count = Column(Integer, nullable=True)

    thumbnail = Column(String, nullable=True)

    registration_open = Column(Boolean, nullable=True)
    approval_required = Column(Boolean, nullable=True)

    has_public_bans = Column(Boolean, nullable=True)
    has_public_peers = Column(Boolean, nullable=True)

    software = Column(String, nullable=True)
    mastodon_version = Column(String, nullable=True)
    software_version = Column(String, nullable=True)
