"""Verify database bootstrap builds maintenance engine URLs from environment.

Covers ``infrastructure.db.bootstrap._maintenance_engine_url`` and
``infrastructure.db.config`` so credentials such as passwords are preserved.
"""

from sqlalchemy.engine import make_url

def test_maintenance_engine_url_preserves_password(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')
    monkeypatch.setenv('DB_NAME', 'code_weave')
    monkeypatch.setenv('DB_USER', 'postgres')
    monkeypatch.setenv('DB_PASSWORD', 's3cret!')
    import importlib
    import infrastructure.db.bootstrap as bootstrap_mod
    import infrastructure.db.config as config_mod
    importlib.reload(config_mod)
    importlib.reload(bootstrap_mod)
    url = make_url(bootstrap_mod._maintenance_engine_url('postgres'))
    assert url.database == 'postgres'
    assert url.username == 'postgres'
    assert url.password == 's3cret!'
