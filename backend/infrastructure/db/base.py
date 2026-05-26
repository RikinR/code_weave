"""Shared SQLAlchemy declarative base for all ORM models.

All tables in :mod:`infrastructure.db.models` inherit from :class:`Base` so
:func:`infrastructure.db.init_db.init_db` can create schema from a single
metadata registry.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root declarative base; table models subclass this type."""
