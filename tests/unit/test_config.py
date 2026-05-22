import importlib


def test_wsgi_application_loads():
    wsgi = importlib.import_module("config.wsgi")
    assert wsgi.application is not None


def test_asgi_application_loads():
    asgi = importlib.import_module("config.asgi")
    assert asgi.application is not None


def test_prod_settings_load():
    settings = importlib.import_module("config.settings.prod")
    assert settings.DEBUG is False


def test_staging_settings_load():
    settings = importlib.import_module("config.settings.staging")
    assert hasattr(settings, "SECRET_KEY")


def test_mypy_settings_load_without_env_file():
    settings = importlib.import_module("config.settings.mypy")
    assert settings.SECRET_KEY
    assert settings.CACHES["default"]["BACKEND"].endswith("LocMemCache")
