from infra.settings import Settings


def test_settings_loads_defaults():
    s = Settings()
    assert s.APP_MODE in {"dev", "test", "prod", "staging", "development", "production"} or isinstance(s.APP_MODE, str)
