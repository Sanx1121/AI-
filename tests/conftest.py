import pytest

pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: async test")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
