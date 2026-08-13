import pytest
from backend.scripts.sahibinden_category_tree_fetcher import fetch_public_url

def test_fetch_public_url_invalid_scheme():
    with pytest.raises(ValueError, match="Invalid URL scheme: file"):
        fetch_public_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Invalid URL scheme: ftp"):
        fetch_public_url("ftp://example.com")

from unittest.mock import patch, MagicMock

@patch('urllib.request.urlopen')
def test_fetch_public_url_valid_scheme(mock_urlopen):
    # Mock urlopen to avoid actual network request
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b"test body"
    mock_response.headers.get_content_charset.return_value = "utf-8"
    mock_response.geturl.return_value = "http://example.com"
    mock_urlopen.return_value.__enter__.return_value = mock_response

    status, body, url = fetch_public_url("http://example.com")

    assert status == 200
    assert body == "test body"
    assert url == "http://example.com"
