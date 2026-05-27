from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey,
    UniqueConstraint, Index, Text, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255))
    logo_path = Column(String(500))
    website = Column(String(500))
    crawler_key = Column(String(50), nullable=False)
    timezone = Column(String(50), nullable=False, default="Asia/Seoul")
    created_at = Column(DateTime, server_default=func.now())

    events = relationship("Event", back_populates="school", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    summary = Column(String(500), nullable=False)
    dtstart = Column(Date, nullable=False)
    dtend = Column(Date, nullable=False)
    description = Column(Text)
    last_seen_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    school = relationship("School", back_populates="events")

    __table_args__ = (
        UniqueConstraint("school_id", "summary", "dtstart", "dtend", name="uq_event_identity"),
        Index("idx_events_school_dt", "school_id", "dtstart"),
    )
