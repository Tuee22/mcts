"""Simplified tests for TestDataSeeder utility class - mypy strict compatible."""

import asyncio
import pytest
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx

from tests.fixtures.data_seeder import TestDataSeeder


class TestTestDataSeederSimplified:
    """Simplified test class focusing on behavior over call inspection."""

    def test_init(self) -> None:
        """Test TestDataSeeder initialization."""
        seeder = TestDataSeeder("http://localhost:8000")
        assert seeder.base_url == "http://localhost:8000"
        assert seeder.client is None

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slashes are stripped from base URL."""
        seeder = TestDataSeeder("http://localhost:8000/")
        assert seeder.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self) -> None:
        """Test async context manager enter and exit."""
        with patch("tests.fixtures.data_seeder.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            assert isinstance(mock_client_class, Mock)
            mock_client_class.return_value = mock_client

            seeder = TestDataSeeder("http://localhost:8000")

            async with seeder as entered_seeder:
                assert entered_seeder is seeder
                assert seeder.client is not None
                mock_client_class.assert_called_once_with(
                    base_url="http://localhost:8000"
                )

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_test_games_success(self) -> None:
        """Test successful game seeding without call introspection."""
        response = MagicMock()
        response.json.return_value = {"id": "game_0", "status": "created"}
        response.raise_for_status.return_value = None

        with patch("tests.fixtures.data_seeder.AsyncClient") as MockAsyncClient:
            assert isinstance(MockAsyncClient, Mock)
            mock_client = AsyncMock()
            setattr(mock_client.post, "side_effect", [response] * 5)
            MockAsyncClient.return_value = mock_client

            seeder = TestDataSeeder("http://localhost:8000")
            async with seeder:
                games = await seeder.seed_test_games()

            assert len(games) == 5
            assert mock_client.post.call_count == 5

    @pytest.mark.asyncio
    async def test_seed_game_with_moves_success(self) -> None:
        """Test successful game seeding with moves."""
        create_response = MagicMock()
        create_response.json.return_value = {"id": "game_123", "status": "created"}
        create_response.raise_for_status.return_value = None

        move_response = MagicMock()
        move_response.raise_for_status.return_value = None

        with patch("tests.fixtures.data_seeder.AsyncClient") as MockAsyncClient:
            assert isinstance(MockAsyncClient, Mock)
            mock_client = AsyncMock()
            mock_client.post.side_effect = [
                create_response,
                move_response,
                move_response,
            ]
            MockAsyncClient.return_value = mock_client

            seeder = TestDataSeeder("http://localhost:8000")
            async with seeder:
                moves = ["*(4,1)", "*(4,7)"]
                game = await seeder.seed_game_with_moves(moves)

            assert game == {"id": "game_123", "status": "created"}
            assert mock_client.post.call_count == 3  # 1 create + 2 moves

    @pytest.mark.asyncio
    async def test_cleanup_test_games_success(self) -> None:
        """Test successful game cleanup."""
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None

        with patch("tests.fixtures.data_seeder.AsyncClient") as MockAsyncClient:
            assert isinstance(MockAsyncClient, Mock)
            mock_client = AsyncMock()
            mock_client.delete.return_value = response
            MockAsyncClient.return_value = mock_client

            seeder = TestDataSeeder("http://localhost:8000")
            async with seeder:
                pass

            game_ids = ["game_1", "game_2", "game_3"]
            await seeder.cleanup_test_games(game_ids)

            assert mock_client.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_verify_server_health_success(self) -> None:
        """Test successful server health verification."""
        response = MagicMock()
        response.json.return_value = {"status": "healthy", "version": "1.0.0"}
        response.raise_for_status.return_value = None

        with patch("tests.fixtures.data_seeder.AsyncClient") as MockAsyncClient:
            assert isinstance(MockAsyncClient, Mock)
            mock_client = AsyncMock()
            mock_client.get.return_value = response
            MockAsyncClient.return_value = mock_client

            with patch(
                "tests.fixtures.data_seeder.HealthResponse"
            ) as MockHealthResponse:
                assert isinstance(MockHealthResponse, Mock)
                expected_health = {"status": "healthy", "version": "1.0.0"}
                health_instance = MagicMock()
                MockHealthResponse.return_value = health_instance

                seeder = TestDataSeeder("http://localhost:8000")
                async with seeder:
                    pass

                health = await seeder.verify_server_health()

                mock_client.get.assert_called_once_with("/health")
                MockHealthResponse.assert_called_once_with(**expected_health)
                assert health is not None

    @pytest.mark.asyncio
    async def test_get_test_game_list_success(self) -> None:
        """Test successful game list retrieval."""
        response = MagicMock()
        expected_response = {
            "games": [
                {"id": "game_1", "status": "in_progress"},
                {"id": "game_2", "status": "finished"},
            ],
            "total": 2,
        }
        response.json.return_value = expected_response
        response.raise_for_status.return_value = None

        with patch("tests.fixtures.data_seeder.AsyncClient") as MockAsyncClient:
            assert isinstance(MockAsyncClient, Mock)
            mock_client = AsyncMock()
            mock_client.get.return_value = response
            MockAsyncClient.return_value = mock_client

            with patch(
                "tests.fixtures.data_seeder.GameListResponse"
            ) as MockGameListResponse:
                assert isinstance(MockGameListResponse, Mock)
                game_list_instance = MagicMock()
                MockGameListResponse.return_value = game_list_instance

                seeder = TestDataSeeder("http://localhost:8000")
                async with seeder:
                    pass

                game_list = await seeder.get_test_game_list()

                mock_client.get.assert_called_once_with("/games")
                MockGameListResponse.assert_called_once_with(**expected_response)
                assert game_list is not None

    @pytest.mark.asyncio
    async def test_error_propagation(self) -> None:
        """Test that HTTP errors are properly propagated."""
        with patch("tests.fixtures.data_seeder.AsyncClient") as MockAsyncClient:
            assert isinstance(MockAsyncClient, Mock)
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPError("Bad Request")
            MockAsyncClient.return_value = mock_client

            seeder = TestDataSeeder("http://localhost:8000")
            async with seeder:
                pass

            with pytest.raises(httpx.HTTPError):
                await seeder.seed_test_games(count=1)
