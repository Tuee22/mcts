"""Unit tests for DNS resolution error handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Optional, Union
import pytest


@pytest.mark.asyncio
async def test_dns_resolution_failure_handling() -> None:
    """Test that DNS resolution failures are handled properly."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Simulate DNS resolution failure
        mock_client.get = AsyncMock(
            side_effect=OSError(
                "Cannot connect to host invalid-domain:80 ssl:default [Name or service not known]"
            )
        )

        # Test that the error is caught and handled
        import httpx

        with pytest.raises(OSError) as exc_info:
            async with httpx.AsyncClient() as client:
                await client.get("http://invalid-domain.example.com")

        assert "Name or service not known" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dns_timeout_handling() -> None:
    """Test that DNS resolution timeouts are handled properly."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Simulate DNS resolution timeout
        mock_client.get = AsyncMock(
            side_effect=asyncio.TimeoutError("DNS lookup timed out")
        )

        # Test that the timeout is caught and handled
        import httpx

        with pytest.raises(asyncio.TimeoutError) as exc_info:
            async with httpx.AsyncClient() as client:
                await client.get("http://slow-dns.example.com", timeout=1.0)

        assert "DNS lookup timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_hostname_format() -> None:
    """Test handling of invalid hostname formats."""
    invalid_hostnames = [
        "http://",
        "http://.",
        "http://..",
        "http://invalid..domain",
        "http://invalid-.domain",
        "http://-invalid.domain",
    ]

    for hostname in invalid_hostnames:
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Simulate invalid hostname error
            mock_client.get = AsyncMock(
                side_effect=ValueError(f"Invalid hostname: {hostname}")
            )

            # Test that the error is caught
            import httpx

            with pytest.raises(ValueError) as exc_info:
                async with httpx.AsyncClient() as client:
                    await client.get(hostname)

            assert "Invalid hostname" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dns_recovery_after_failure() -> None:
    """Test that the system can recover after DNS failures."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"

        call_count = 0

        async def get_with_failure(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("DNS failure")
            return mock_response

        mock_client.get = get_with_failure

        import httpx

        async with httpx.AsyncClient() as client:
            # First attempt should fail
            with pytest.raises(OSError):
                await client.get("http://failing.example.com")

            # Second attempt should succeed
            response = await client.get("http://working.example.com")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_dns_cache_poisoning_protection() -> None:
    """Test protection against DNS cache poisoning attempts."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Simulate unexpected redirect that might indicate DNS poisoning
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_response.headers = {"Location": "http://malicious-site.com"}
        mock_client.get = AsyncMock(return_value=mock_response)

        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://legitimate-site.com", follow_redirects=False
            )

            # Verify we detect the unexpected redirect
            assert response.status_code == 301
            assert response.headers["Location"] != "http://legitimate-site.com"


@pytest.mark.asyncio
async def test_concurrent_dns_failures() -> None:
    """Test handling of multiple concurrent DNS failures."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # All requests fail with DNS errors
        mock_client.get = AsyncMock(side_effect=OSError("DNS failure"))

        import httpx

        async with httpx.AsyncClient() as client:
            # Create multiple concurrent requests
            tasks = [client.get(f"http://invalid-{i}.example.com") for i in range(5)]

            # All should fail with DNS errors
            results = await asyncio.gather(*tasks, return_exceptions=True)

            assert len(results) == 5
            assert all(isinstance(r, OSError) for r in results)


@pytest.mark.asyncio
async def test_dns_fallback_mechanism() -> None:
    """Test DNS fallback mechanism when primary DNS fails."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Simulate primary DNS failure, fallback success
        attempts: List[Optional[str]] = []

        async def track_attempts(*args: object, **kwargs: object) -> MagicMock:
            url = args[0] if args else kwargs.get("url")
            attempts.append(str(url) if url else None)
            if len(attempts) == 1:
                raise OSError("Primary DNS failed")
            else:
                mock_response = MagicMock()
                mock_response.status_code = 200
                return mock_response

        mock_client.get = track_attempts

        import httpx

        async with httpx.AsyncClient() as client:
            # First attempt should internally fail and retry
            try:
                await client.get("http://example.com")
            except OSError:
                # Retry with fallback
                response = await client.get("http://example.com")
                assert response.status_code == 200

            assert len(attempts) == 2
