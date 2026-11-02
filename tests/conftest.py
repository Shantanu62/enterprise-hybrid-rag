
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """Provide a FastAPI test client for API tests."""

    with TestClient(app) as test_client:
        yield test_client
