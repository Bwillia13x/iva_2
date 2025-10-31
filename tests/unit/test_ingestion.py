"""Tests for ingestion module."""
from unittest.mock import AsyncMock, patch

import pytest

from src.iva.ingestion.fetch import fetch_html, fetch_rendered
from src.iva.ingestion.parse import fetch_pdf_text, html_to_text


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_fetch_html(mock_client):
    """Test HTML fetching."""
    mock_response = AsyncMock()
    mock_response.text = "<html>Test</html>"
    mock_response.raise_for_status = AsyncMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    mock_client_instance.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    result = await fetch_html("http://test.com")
    assert result == "<html>Test</html>"


@pytest.mark.asyncio
@patch("playwright.async_api.async_playwright")
async def test_fetch_rendered(mock_playwright):
    """Test rendered HTML fetching."""
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html>Rendered</html>")
    mock_page.goto = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_browser.close = AsyncMock()

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser
    mock_playwright.return_value.__aenter__.return_value = mock_p
    mock_playwright.return_value.__aexit__.return_value = None

    result = await fetch_rendered("http://test.com")
    assert result == "<html>Rendered</html>"


def test_html_to_text():
    """Test HTML to text conversion."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <script>console.log('test');</script>
            <style>.test { color: red; }</style>
            <p>Hello World</p>
            <div>More text</div>
        </body>
    </html>
    """
    text = html_to_text(html)
    assert "Hello World" in text
    assert "More text" in text
    assert "console.log" not in text  # Scripts removed
    assert "color: red" not in text  # Styles removed


def test_html_to_text_strips_whitespace():
    """Test that HTML to text strips excessive whitespace."""
    html = "<p>Line   1</p><p>Line   2</p>"
    text = html_to_text(html)
    assert "Line 1" in text
    assert "Line 2" in text
    assert "   " not in text  # No triple spaces


def test_html_to_text_removes_scripts():
    """Test that scripts are removed from HTML."""
    html = """
    <html>
        <body>
            <script>alert('test');</script>
            <p>Content</p>
            <noscript>No JS</noscript>
        </body>
    </html>
    """
    text = html_to_text(html)
    assert "alert" not in text
    assert "No JS" not in text  # noscript removed
    assert "Content" in text


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_fetch_pdf_text(mock_client):
    """Test PDF text extraction."""
    from io import BytesIO

    from pypdf import PdfWriter

    # Create a mock PDF
    pdf_writer = PdfWriter()
    pdf_writer.add_blank_page(width=612, height=792)
    pdf_buffer = BytesIO()
    pdf_writer.write(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    mock_response = AsyncMock()
    mock_response.content = pdf_bytes
    mock_response.raise_for_status = AsyncMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    mock_client_instance.get.return_value = mock_response
    mock_client.return_value = mock_client_instance

    result = await fetch_pdf_text("http://test.com/file.pdf")
    assert isinstance(result, str)


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_fetch_html_error_handling(mock_client):
    """Test HTML fetching error handling."""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    mock_client_instance.get.side_effect = Exception("Connection error")
    mock_client.return_value = mock_client_instance

    with pytest.raises(Exception):
        await fetch_html("http://test.com")


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_fetch_html_timeout(mock_client):
    """Test HTML fetching with timeout."""
    import httpx

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")
    mock_client.return_value = mock_client_instance

    with pytest.raises(httpx.TimeoutException):
        await fetch_html("http://test.com")


def test_html_to_text_empty_html():
    """Test HTML to text with empty HTML."""
    text = html_to_text("")
    assert text == ""


def test_html_to_text_only_scripts():
    """Test HTML to text with only scripts."""
    html = "<script>test</script><style>test</style>"
    text = html_to_text(html)
    assert text.strip() == "" or len(text.strip()) == 0


def test_html_to_text_preserves_structure():
    """Test that HTML to text preserves some structure."""
    html = "<h1>Title</h1><p>Paragraph 1</p><p>Paragraph 2</p>"
    text = html_to_text(html)
    assert "Title" in text
    assert "Paragraph 1" in text
    assert "Paragraph 2" in text
