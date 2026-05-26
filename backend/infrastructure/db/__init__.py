"""PostgreSQL persistence layer: config, sessions, models, and bootstrap.

Application code obtains a :class:`sqlalchemy.orm.Session` from
:mod:`infrastructure.db.session` and queries models under
:mod:`infrastructure.db.models`.
"""
