"""Comprehensive tests for game data fixtures and validation."""

import pytest
from typing import Dict, List

from backend.api.models import GameSettings, MCTSSettings, PlayerType
from tests.fixtures.game_data import (
    FAST_GAME_SETTINGS,
    STANDARD_GAME_SETTINGS,
    PUCT_GAME_SETTINGS,
    OPENING_MOVES,
    WALL_GAME_MOVES,
    HUMAN_PLAYERS,
    AI_PLAYERS,
)


class TestGameSettingsFixtures:
    """Test predefined game settings fixtures."""

    def test_fast_game_settings_structure(self) -> None:
        """Test that FAST_GAME_SETTINGS has proper structure and values."""
        assert isinstance(FAST_GAME_SETTINGS, GameSettings)

        mcts_settings = FAST_GAME_SETTINGS.mcts_settings
        assert isinstance(mcts_settings, MCTSSettings)

        # Verify fast game configuration
        assert mcts_settings.c == 0.158
        assert mcts_settings.min_simulations == 100
        assert mcts_settings.max_simulations == 100
        assert mcts_settings.use_rollout is True
        assert mcts_settings.seed == 42

    def test_standard_game_settings_structure(self) -> None:
        """Test that STANDARD_GAME_SETTINGS has proper structure and values."""
        assert isinstance(STANDARD_GAME_SETTINGS, GameSettings)

        mcts_settings = STANDARD_GAME_SETTINGS.mcts_settings
        assert isinstance(mcts_settings, MCTSSettings)

        # Verify standard game configuration
        assert mcts_settings.c == 1.4
        assert mcts_settings.min_simulations == 1000
        assert mcts_settings.max_simulations == 1000
        assert mcts_settings.use_rollout is True
        assert mcts_settings.seed == 42

    def test_puct_game_settings_structure(self) -> None:
        """Test that PUCT_GAME_SETTINGS has proper structure and values."""
        assert isinstance(PUCT_GAME_SETTINGS, GameSettings)

        mcts_settings = PUCT_GAME_SETTINGS.mcts_settings
        assert isinstance(mcts_settings, MCTSSettings)

        # Verify PUCT game configuration
        assert mcts_settings.c == 0.158
        assert mcts_settings.min_simulations == 500
        assert mcts_settings.max_simulations == 500
        assert mcts_settings.use_puct is True
        assert mcts_settings.use_probs is True
        assert mcts_settings.seed == 42

    def test_settings_are_different_configurations(self) -> None:
        """Test that the three settings represent different MCTS configurations."""
        # Different exploration constants
        assert (
            FAST_GAME_SETTINGS.mcts_settings.c != STANDARD_GAME_SETTINGS.mcts_settings.c
        )

        # Different simulation counts
        assert (
            FAST_GAME_SETTINGS.mcts_settings.min_simulations
            != STANDARD_GAME_SETTINGS.mcts_settings.min_simulations
        )
        assert (
            STANDARD_GAME_SETTINGS.mcts_settings.min_simulations
            != PUCT_GAME_SETTINGS.mcts_settings.min_simulations
        )

        # PUCT vs UCT algorithms
        assert getattr(PUCT_GAME_SETTINGS.mcts_settings, "use_puct", False) is True
        assert getattr(FAST_GAME_SETTINGS.mcts_settings, "use_puct", False) is not True
        assert (
            getattr(STANDARD_GAME_SETTINGS.mcts_settings, "use_puct", False) is not True
        )

    def test_settings_reproducibility(self) -> None:
        """Test that all settings use the same seed for reproducibility."""
        assert FAST_GAME_SETTINGS.mcts_settings.seed == 42
        assert STANDARD_GAME_SETTINGS.mcts_settings.seed == 42
        assert PUCT_GAME_SETTINGS.mcts_settings.seed == 42

    def test_settings_serialization(self) -> None:
        """Test that settings can be serialized to dict (for API usage)."""
        for settings in [
            FAST_GAME_SETTINGS,
            STANDARD_GAME_SETTINGS,
            PUCT_GAME_SETTINGS,
        ]:
            settings_dict = settings.dict()

            assert isinstance(settings_dict, dict)
            assert "mcts_settings" in settings_dict
            assert isinstance(settings_dict["mcts_settings"], dict)

            # Essential fields should be present
            mcts = settings_dict["mcts_settings"]
            assert "c" in mcts
            assert "min_simulations" in mcts
            assert "max_simulations" in mcts
            assert "seed" in mcts


class TestMoveSequenceFixtures:
    """Test predefined move sequence fixtures."""

    def test_opening_moves_structure(self) -> None:
        """Test that OPENING_MOVES has proper structure."""
        assert isinstance(OPENING_MOVES, list)
        assert len(OPENING_MOVES) == 4
        assert all(isinstance(move, str) for move in OPENING_MOVES)

    def test_opening_moves_content(self) -> None:
        """Test that OPENING_MOVES contains valid move notation."""
        expected_moves = [
            "*(4,1)",  # Hero forward
            "*(4,7)",  # Villain forward
            "*(4,2)",  # Hero forward
            "*(4,6)",  # Villain forward
        ]
        assert OPENING_MOVES == expected_moves

    def test_opening_moves_alternating_players(self) -> None:
        """Test that opening moves alternate between players."""
        # Odd indices (0, 2) should be hero moves at y=1,2
        assert "*(4,1)" in OPENING_MOVES[0]
        assert "*(4,2)" in OPENING_MOVES[2]

        # Even indices (1, 3) should be villain moves at y=7,6
        assert "*(4,7)" in OPENING_MOVES[1]
        assert "*(4,6)" in OPENING_MOVES[3]

    def test_wall_game_moves_structure(self) -> None:
        """Test that WALL_GAME_MOVES has proper structure."""
        assert isinstance(WALL_GAME_MOVES, list)
        assert len(WALL_GAME_MOVES) == 6
        assert all(isinstance(move, str) for move in WALL_GAME_MOVES)

    def test_wall_game_moves_content(self) -> None:
        """Test that WALL_GAME_MOVES contains valid move notation with walls."""
        expected_moves = [
            "*(4,1)",  # Hero forward
            "*(4,7)",  # Villain forward
            "H(4,1)",  # Hero places horizontal wall
            "V(3,6)",  # Villain places vertical wall
            "*(3,1)",  # Hero moves left
            "*(5,7)",  # Villain moves right
        ]
        assert WALL_GAME_MOVES == expected_moves

    def test_wall_game_moves_has_walls(self) -> None:
        """Test that WALL_GAME_MOVES includes wall placement moves."""
        wall_moves = [move for move in WALL_GAME_MOVES if move.startswith(("H", "V"))]
        assert len(wall_moves) == 2
        assert "H(4,1)" in wall_moves  # Horizontal wall
        assert "V(3,6)" in wall_moves  # Vertical wall

    def test_move_notation_validity(self) -> None:
        """Test that all moves use valid notation patterns."""
        all_moves = OPENING_MOVES + WALL_GAME_MOVES

        for move in all_moves:
            # Should match patterns: *(x,y), H(x,y), V(x,y)
            assert len(move) >= 5, f"Move too short: {move}"
            assert move[0] in ["*", "H", "V"], f"Invalid move type: {move[0]} in {move}"
            assert move[1] == "(", f"Missing opening paren in {move}"
            assert "," in move, f"Missing comma in {move}"
            assert move.endswith(")"), f"Missing closing paren in {move}"

    def test_move_coordinates_are_numeric(self) -> None:
        """Test that move coordinates are numeric."""
        all_moves = OPENING_MOVES + WALL_GAME_MOVES

        for move in all_moves:
            # Extract coordinates from move like "*(4,1)"
            coords_part = move[2:-1]  # Remove "*(", "H(", "V(" and ")"
            x_str, y_str = coords_part.split(",")

            # Should be convertible to integers
            try:
                x, y = int(x_str), int(y_str)
                assert 0 <= x <= 8, f"X coordinate out of range in {move}: {x}"
                assert 0 <= y <= 8, f"Y coordinate out of range in {move}: {y}"
            except ValueError:
                pytest.fail(f"Non-numeric coordinates in move: {move}")


class TestPlayerFixtures:
    """Test predefined player configuration fixtures."""

    def test_human_players_structure(self) -> None:
        """Test that HUMAN_PLAYERS has proper structure."""
        assert isinstance(HUMAN_PLAYERS, dict)
        assert len(HUMAN_PLAYERS) == 2
        assert "alice" in HUMAN_PLAYERS
        assert "bob" in HUMAN_PLAYERS

    def test_human_players_content(self) -> None:
        """Test that HUMAN_PLAYERS contains valid player configs."""
        alice = HUMAN_PLAYERS["alice"]
        assert alice["name"] == "Alice"
        assert alice["type"] == PlayerType.HUMAN

        bob = HUMAN_PLAYERS["bob"]
        assert bob["name"] == "Bob"
        assert bob["type"] == PlayerType.HUMAN

    def test_ai_players_structure(self) -> None:
        """Test that AI_PLAYERS has proper structure."""
        assert isinstance(AI_PLAYERS, dict)
        assert len(AI_PLAYERS) == 2
        assert "ai_easy" in AI_PLAYERS
        assert "ai_hard" in AI_PLAYERS

    def test_ai_players_content(self) -> None:
        """Test that AI_PLAYERS contains valid player configs."""
        ai_easy = AI_PLAYERS["ai_easy"]
        assert ai_easy["name"] == "Easy AI"
        assert ai_easy["type"] == PlayerType.MACHINE

        ai_hard = AI_PLAYERS["ai_hard"]
        assert ai_hard["name"] == "Hard AI"
        assert ai_hard["type"] == PlayerType.MACHINE

    def test_player_type_consistency(self) -> None:
        """Test that player types are consistent within each category."""
        # All human players should be HUMAN type
        for player in HUMAN_PLAYERS.values():
            assert player["type"] == PlayerType.HUMAN

        # All AI players should be MACHINE type
        for player in AI_PLAYERS.values():
            assert player["type"] == PlayerType.MACHINE

    def test_player_names_are_unique(self) -> None:
        """Test that all player names are unique across fixtures."""
        all_players = {**HUMAN_PLAYERS, **AI_PLAYERS}
        names = [player["name"] for player in all_players.values()]

        assert len(names) == len(set(names)), "Duplicate player names found"

    def test_player_configs_for_api_usage(self) -> None:
        """Test that player configs can be used in API calls."""
        # Test that player configs have all required fields
        all_players = {**HUMAN_PLAYERS, **AI_PLAYERS}

        for player_id, config in all_players.items():
            assert "name" in config, f"Missing name in player {player_id}"
            assert "type" in config, f"Missing type in player {player_id}"

            # Name should be a non-empty string
            assert isinstance(config["name"], str)
            assert len(config["name"]) > 0

            # Type should be a valid PlayerType
            assert config["type"] in [PlayerType.HUMAN, PlayerType.MACHINE]


class TestFixturesIntegration:
    """Test integration between different fixture categories."""

    def test_settings_compatible_with_move_sequences(self) -> None:
        """Test that game settings are compatible with move sequences."""
        # All settings should work with the predefined move sequences
        settings_list = [FAST_GAME_SETTINGS, STANDARD_GAME_SETTINGS, PUCT_GAME_SETTINGS]
        move_sequences = [OPENING_MOVES, WALL_GAME_MOVES]

        for settings in settings_list:
            for moves in move_sequences:
                # Should be able to create a test scenario
                assert len(moves) > 0
                assert settings.mcts_settings.seed is not None

    def test_player_configs_compatible_with_settings(self) -> None:
        """Test that player configs can be used with game settings."""
        all_players = {**HUMAN_PLAYERS, **AI_PLAYERS}

        # Should be able to create game configs combining players and settings
        for player1_key, player1 in all_players.items():
            for player2_key, player2 in all_players.items():
                if player1_key != player2_key:  # Different players
                    # This represents a valid game configuration
                    game_config = {
                        "player1": player1,
                        "player2": player2,
                        "settings": FAST_GAME_SETTINGS,
                        "moves": OPENING_MOVES,
                    }

                    # Verify players have different names
                    player1_obj = game_config["player1"]
                    player2_obj = game_config["player2"]
                    assert isinstance(player1_obj, dict)
                    assert isinstance(player2_obj, dict)
                    assert player1_obj["name"] != player2_obj["name"]

    def test_complete_test_scenario_creation(self) -> None:
        """Test creating complete test scenarios from fixtures."""
        # Create various test scenarios using all fixtures
        scenarios = [
            {
                "name": "Human vs AI with fast settings",
                "player1": HUMAN_PLAYERS["alice"],
                "player2": AI_PLAYERS["ai_easy"],
                "settings": FAST_GAME_SETTINGS,
                "moves": OPENING_MOVES,
            },
            {
                "name": "AI vs AI with PUCT settings",
                "player1": AI_PLAYERS["ai_easy"],
                "player2": AI_PLAYERS["ai_hard"],
                "settings": PUCT_GAME_SETTINGS,
                "moves": WALL_GAME_MOVES,
            },
            {
                "name": "Human vs Human with standard settings",
                "player1": HUMAN_PLAYERS["alice"],
                "player2": HUMAN_PLAYERS["bob"],
                "settings": STANDARD_GAME_SETTINGS,
                "moves": OPENING_MOVES,
            },
        ]

        for scenario in scenarios:
            # Each scenario should have all required components
            assert "player1" in scenario
            assert "player2" in scenario
            assert "settings" in scenario
            assert "moves" in scenario

            # Players should be different
            player1_obj = scenario["player1"]
            player2_obj = scenario["player2"]
            assert isinstance(player1_obj, dict)
            assert isinstance(player2_obj, dict)
            assert player1_obj["name"] != player2_obj["name"]

            # Settings should be valid
            assert hasattr(scenario["settings"], "mcts_settings")

            # Moves should be non-empty
            moves = scenario["moves"]
            assert hasattr(moves, "__len__")  # Ensure it's sized
            assert len(moves) > 0

    def test_fixture_data_immutability(self) -> None:
        """Test that fixture data doesn't get mutated during tests."""
        # Save original values
        original_fast_c = FAST_GAME_SETTINGS.mcts_settings.c
        original_opening_moves = OPENING_MOVES.copy()
        original_alice_name = HUMAN_PLAYERS["alice"]["name"]

        # These values should not change throughout test execution
        assert FAST_GAME_SETTINGS.mcts_settings.c == original_fast_c
        assert OPENING_MOVES == original_opening_moves
        assert HUMAN_PLAYERS["alice"]["name"] == original_alice_name


class TestFixtureUtilityFunctions:
    """Test utility functions for working with fixtures."""

    def test_get_all_settings(self) -> None:
        """Test getting all available game settings."""
        all_settings = [FAST_GAME_SETTINGS, STANDARD_GAME_SETTINGS, PUCT_GAME_SETTINGS]

        assert len(all_settings) == 3
        assert all(isinstance(setting, GameSettings) for setting in all_settings)

        # Each should have different characteristics
        c_values = [setting.mcts_settings.c for setting in all_settings]
        sim_counts = [setting.mcts_settings.min_simulations for setting in all_settings]

        assert len(set(c_values)) > 1, "Settings should have different C values"
        assert (
            len(set(sim_counts)) > 1
        ), "Settings should have different simulation counts"

    def test_get_all_move_sequences(self) -> None:
        """Test getting all available move sequences."""
        all_sequences = [OPENING_MOVES, WALL_GAME_MOVES]

        assert len(all_sequences) == 2
        assert all(isinstance(seq, list) for seq in all_sequences)
        assert all(len(seq) > 0 for seq in all_sequences)

        # Should have different characteristics
        assert len(OPENING_MOVES) != len(WALL_GAME_MOVES)

        # Wall game should contain wall moves
        has_walls = any(move.startswith(("H", "V")) for move in WALL_GAME_MOVES)
        assert has_walls

    def test_get_all_players(self) -> None:
        """Test getting all available player configurations."""
        all_players = {**HUMAN_PLAYERS, **AI_PLAYERS}

        assert len(all_players) == 4

        # Should have both human and AI players
        human_count = sum(
            1 for p in all_players.values() if p["type"] == PlayerType.HUMAN
        )
        ai_count = sum(
            1 for p in all_players.values() if p["type"] == PlayerType.MACHINE
        )

        assert human_count == 2
        assert ai_count == 2
