import pytest

from pipeline import settings


@pytest.fixture(autouse=True)
def restore_target_settings():
    keys = ("TENANT", "ALLOWED_ACCOUNTS", "ADMIN_ENV_ID", "ADMIN", "ADMIN_SITE", "SOLUTION", "PUBLISHER",
            "DV_CONN", "SP_CONN", "CONN_REFS", "FLOW_REFS", "LIST_CONFIG", "LIST_CONNECTIONS", "LIST_VARIABLES")
    original = {key: getattr(settings, key) for key in keys}
    yield
    for key, value in original.items():
        setattr(settings, key, value)
