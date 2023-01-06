from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.sql import func

from .base import Base


class Instance(Base):
    __tablename__ = "instances"

    host = Column(String, primary_key=True)
    digest = Column(String, index=True)
    last_ingest = Column(DateTime, nullable=True)
    last_ingest_status = Column(String, nullable=True)
    last_ingest_success = Column(DateTime, nullable=True)
    first_ingest_success = Column(DateTime, nullable=True)
    last_ingest_peers = Column(DateTime, nullable=True)
    www_host = Column(String, nullable=True)

    title = Column(String, nullable=True)
    short_description = Column(String, nullable=True)
    email = Column(String, nullable=True)
    version = Column(String, nullable=True)

    current_user_count = Column(Integer, nullable=True)
    current_status_count = Column(Integer, nullable=True)
    current_domain_count = Column(Integer, nullable=True)

    thumbnail = Column(String, nullable=True)

    registration_open = Column(Boolean, nullable=True)
    approval_required = Column(Boolean, nullable=True)

    has_public_bans = Column(Boolean, nullable=True)
    has_public_peers = Column(Boolean, nullable=True)

    software = Column(String, nullable=True)
    mastodon_version = Column(String, nullable=True)
    software_version = Column(String, nullable=True)
    nodeinfo_version = Column(String, nullable=True)

    ip_address = Column(String, nullable=True)
    asn = Column(String, nullable=True)
    base_domain = Column(String, index=True)


Index("idx_instance_status_time", Instance.last_ingest_status, Instance.last_ingest)


class InstanceStats(Base):
    __tablename__ = "instance_stats"

    host = Column(String, primary_key=True)
    ingest_time = Column(DateTime, primary_key=True, server_default=func.now())
    user_count = Column(Integer, nullable=True)
    active_monthly_users = Column(Integer, nullable=True)
    status_count = Column(Integer, nullable=True)
    domain_count = Column(Integer, nullable=True)
