import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_supabase_client():
    """Auto-used fixture to mock supabase.create_client globally for tests."""
    # Mock the Supabase Client class itself if needed, or just the create_client
    mock_client = MagicMock()
    # Configure mock methods if the client is used directly on import (it isn't here)

    # Patch the create_client function in the database module where it's imported
    with patch('server.database.create_client', return_value=mock_client) as mock_create:
        yield mock_create # Yield the mock in case any test needs to inspect it 