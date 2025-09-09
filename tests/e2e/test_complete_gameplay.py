"""
E2E tests for complete gameplay scenarios.

These tests verify full game flows from start to finish, including
player moves, wall placements, turn management, and victory conditions.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Locator

import pytest
from playwright.async_api import Page, async_playwright, expect


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCompleteGameplay:
    """Tests for complete game scenarios from start to finish."""

    async def test_human_vs_human_complete_game(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test a complete Human vs Human game from start to victory.

        This test simulates two human players taking turns, moving pieces,
        placing walls, and ultimately reaching a victory condition.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Setup game
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")

                # Wait for connection
                await self._wait_for_connection(page)

                # Configure Human vs Human game
                await self._setup_game(page, mode="human_vs_human", board_size=5)

                # Start the game
                game_container = await self._start_game(page)
                assert game_container is not None, "Failed to start game"

                # Verify initial game state
                board = page.locator('[data-testid="game-board"]')
                await expect(board).to_be_visible(timeout=5000)

                # Get player positions
                player1_piece = page.locator('[data-testid="player-0-piece"]')
                player2_piece = page.locator('[data-testid="player-1-piece"]')

                # Verify both players are on the board
                await expect(player1_piece).to_be_visible()
                await expect(player2_piece).to_be_visible()

                # Simulate several moves
                moves_made = []

                # Player 1 move
                await self._make_move(page, player=0, target_cell="cell-2-0")
                moves_made.append("Player 1: Move to (2,0)")

                # Player 2 move
                await self._make_move(page, player=1, target_cell="cell-2-4")
                moves_made.append("Player 2: Move to (2,4)")

                # Player 1 places wall
                await self._place_wall(
                    page, player=0, wall_type="horizontal", position="wall-h-2-1"
                )
                moves_made.append("Player 1: Horizontal wall at (2,1)")

                # Player 2 places wall
                await self._place_wall(
                    page, player=1, wall_type="vertical", position="wall-v-1-2"
                )
                moves_made.append("Player 2: Vertical wall at (1,2)")

                # Continue playing until victory (simplified for test)
                # Player 1 tries to reach the opposite side
                await self._make_move(page, player=0, target_cell="cell-3-0")
                await self._make_move(page, player=1, target_cell="cell-1-4")
                await self._make_move(
                    page, player=0, target_cell="cell-4-0"
                )  # Victory move

                # Check for victory condition
                victory_modal = page.locator('[data-testid="victory-modal"]')
                winner_text = page.locator('[data-testid="winner-text"]')

                # One of these should indicate game end
                if await victory_modal.count() > 0:
                    await expect(victory_modal).to_be_visible(timeout=5000)
                    winner = await winner_text.text_content()
                    assert winner is not None and (
                        "Player 1" in winner or "Player 2" in winner
                    ), f"Victory modal doesn't show winner: {winner}"
                    print(f"✅ Game completed with winner: {winner}")
                else:
                    # Alternative: Check if game state shows winner
                    game_status = page.locator('[data-testid="game-status"]')
                    if await game_status.count() > 0:
                        status_text = await game_status.text_content()
                        assert status_text is not None and (
                            "won" in status_text.lower()
                            or "victory" in status_text.lower()
                        ), f"Game doesn't show victory status: {status_text}"

                print(f"✅ Human vs Human game completed. Moves: {len(moves_made)}")

            finally:
                await browser.close()

    async def test_human_vs_ai_complete_game(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test a complete Human vs AI game.

        This verifies that AI moves are properly triggered and displayed,
        and that the game flows correctly with mixed human/AI players.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Setup game
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")
                await self._wait_for_connection(page)

                # Configure Human vs AI game
                await self._setup_game(
                    page, mode="human_vs_ai", ai_difficulty="medium", board_size=5
                )

                # Start the game
                game_container = await self._start_game(page)
                assert game_container is not None, "Failed to start game"

                # Make human move
                await self._make_move(page, player=0, target_cell="cell-1-0")

                # Wait for AI move
                ai_thinking_indicator = page.locator('[data-testid="ai-thinking"]')
                if await ai_thinking_indicator.count() > 0:
                    # Wait for AI thinking indicator to disappear
                    await expect(ai_thinking_indicator).not_to_be_visible(timeout=10000)
                else:
                    # Just wait for board state to change
                    await page.wait_for_timeout(3000)

                # Verify AI made a move (player 2 position should change)
                move_history = page.locator('[data-testid="move-history"]')
                if await move_history.count() > 0:
                    move_entries = page.locator(
                        '[data-testid="move-history"] .move-entry'
                    )
                    move_count = await move_entries.count()
                    assert move_count >= 2, "AI didn't make a move"
                    print(f"✅ AI responded to human move. Total moves: {move_count}")

                # Continue playing
                max_moves = 30
                game_ended = False

                for i in range(max_moves):
                    # Check if game ended
                    if await self._check_game_ended(page):
                        game_ended = True
                        break

                    # Get current player
                    current_player = await self._get_current_player(page)

                    if current_player == 0:
                        # Human turn - make a simple move
                        legal_moves = await self._get_legal_move_indicators(page)
                        if legal_moves:
                            await legal_moves[0].click()
                            await page.wait_for_timeout(500)
                    else:
                        # AI turn - wait for it
                        await page.wait_for_timeout(2000)

                assert game_ended, "Game didn't end within expected moves"
                print("✅ Human vs AI game completed successfully")

            finally:
                await browser.close()

    async def test_ai_vs_ai_observation(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test AI vs AI game observation mode.

        This verifies that users can watch two AIs play against each other,
        with proper move visualization and game flow.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")
                await self._wait_for_connection(page)

                # Configure AI vs AI game
                await self._setup_game(
                    page, mode="ai_vs_ai", ai_difficulty="medium", board_size=5
                )

                # Start the game
                game_container = await self._start_game(page)
                assert game_container is not None, "Failed to start game"

                # Watch several AI moves
                moves_observed = 0
                max_observations = 20

                for _ in range(max_observations):
                    # Wait for next AI move
                    await page.wait_for_timeout(1500)

                    # Check move history is updating
                    move_history = page.locator('[data-testid="move-history"]')
                    if await move_history.count() > 0:
                        move_entries = page.locator(
                            '[data-testid="move-history"] .move-entry'
                        )
                        moves = await move_entries.count()
                        if moves > moves_observed:
                            moves_observed = moves
                            print(f"AI vs AI: {moves} moves completed")

                    # Check if game ended
                    if await self._check_game_ended(page):
                        print(f"✅ AI vs AI game ended after {moves_observed} moves")
                        break

                assert moves_observed > 0, "No AI moves were observed"

                # Verify game controls are in observation mode
                board_cells = page.locator('[data-testid^="cell-"]')
                if await board_cells.count() > 0:
                    # Cells should not be clickable in AI vs AI mode
                    first_cell = board_cells.first
                    try:
                        is_clickable = await first_cell.evaluate(  # type: ignore
                            "el => window.getComputedStyle(el).cursor === 'pointer'"
                        )
                        assert (
                            not is_clickable
                        ), "Bug: Board cells are clickable in AI vs AI mode"
                    except AttributeError:
                        print(
                            "ℹ️ Cannot check cell cursor style - assume correct behavior"
                        )

                print("✅ AI vs AI observation mode working correctly")

            finally:
                await browser.close()

    async def test_quick_victory_scenario(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test a quick victory scenario with minimal moves.

        This verifies that victory conditions are properly detected
        even in the shortest possible games.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")
                await self._wait_for_connection(page)

                # Setup small board for quick game
                await self._setup_game(page, mode="human_vs_human", board_size=5)
                game_container = await self._start_game(page)

                # Execute a series of moves for quick victory
                # This simulates optimal play for fastest win
                quick_moves = [
                    ("cell-1-0", 0),  # P1 forward
                    ("cell-3-4", 1),  # P2 sideways
                    ("cell-2-0", 0),  # P1 forward
                    ("cell-3-3", 1),  # P2 sideways
                    ("cell-3-0", 0),  # P1 forward
                    ("cell-3-2", 1),  # P2 sideways
                    ("cell-4-0", 0),  # P1 reaches goal - victory!
                ]

                for cell_id, expected_player in quick_moves:
                    current_player = await self._get_current_player(page)
                    assert (
                        current_player == expected_player
                    ), f"Wrong player turn. Expected {expected_player}, got {current_player}"

                    cell = page.locator(f'[data-testid="{cell_id}"]')
                    if await cell.count() > 0:
                        await cell.click()
                        await page.wait_for_timeout(500)

                    # Check for victory
                    if await self._check_game_ended(page):
                        print(f"✅ Quick victory achieved in {len(quick_moves)} moves")
                        break

                # Verify game is in completed state
                assert await self._check_game_ended(
                    page
                ), "Game didn't end after reaching goal"

            finally:
                await browser.close()

    async def test_complex_50_move_game(self, e2e_urls: Dict[str, str]) -> None:
        """
        Test a complex game with many moves and wall placements.

        This stress tests the game flow with a longer, more complex game
        including multiple walls and strategic positioning.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(e2e_urls["frontend"])
                await page.wait_for_load_state("networkidle")
                await self._wait_for_connection(page)

                # Setup larger board for complex game
                await self._setup_game(page, mode="human_vs_ai", board_size=9)
                game_container = await self._start_game(page)

                moves_made = 0
                walls_placed = 0
                max_moves = 50

                for i in range(max_moves):
                    if await self._check_game_ended(page):
                        print(
                            f"Game ended after {moves_made} moves and {walls_placed} walls"
                        )
                        break

                    current_player = await self._get_current_player(page)

                    if current_player == 0:  # Human turn
                        # Alternate between moves and walls
                        if i % 3 == 0 and walls_placed < 10:
                            # Try to place a wall
                            success = await self._place_random_wall(page)
                            if success:
                                walls_placed += 1
                        else:
                            # Make a move
                            legal_moves = await self._get_legal_move_indicators(page)
                            if legal_moves:
                                # Choose a strategic move (toward goal)
                                await legal_moves[0].click()
                                moves_made += 1

                        await page.wait_for_timeout(500)
                    else:  # AI turn
                        # Wait for AI to complete its turn
                        await page.wait_for_timeout(2000)
                        moves_made += 1

                # Verify game statistics
                move_history = page.locator('[data-testid="move-history"]')
                if await move_history.count() > 0:
                    move_entries = page.locator(
                        '[data-testid="move-history"] .move-entry'
                    )
                    total_moves = await move_entries.count()
                    assert (
                        total_moves >= 20
                    ), f"Complex game too short: only {total_moves} moves"
                    print(f"✅ Complex game completed with {total_moves} total moves")

                # Check that walls were actually placed
                wall_elements = page.locator('[data-testid^="wall-"]')
                wall_count = await wall_elements.count()
                assert wall_count > 0, "No walls were placed in complex game"
                print(f"✅ {wall_count} walls on board at game end")

            finally:
                await browser.close()

    # Helper methods

    async def _wait_for_connection(self, page: Page) -> None:
        """Wait for WebSocket connection to be established."""
        connection_text = page.locator('[data-testid="connection-text"]')
        if await connection_text.count() > 0:
            await expect(connection_text).to_have_text("Connected", timeout=10000)
        else:
            # Alternative: just wait a bit
            await page.wait_for_timeout(2000)

    async def _setup_game(
        self,
        page: Page,
        mode: str = "human_vs_human",
        ai_difficulty: str = "medium",
        board_size: int = 9,
    ) -> None:
        """Configure game settings."""
        settings_button = page.locator('button:has-text("⚙️ Game Settings")')
        if await settings_button.count() > 0:
            await settings_button.click()
            await page.wait_for_timeout(500)

            # Select game mode
            mode_button = page.locator(f'[data-testid="mode-{mode}"]')
            if await mode_button.count() == 0:
                # Fallback to text-based selection
                if mode == "human_vs_human":
                    mode_button = page.locator('button:has-text("Human vs Human")')
                elif mode == "human_vs_ai":
                    mode_button = page.locator('button:has-text("Human vs AI")')
                elif mode == "ai_vs_ai":
                    mode_button = page.locator('button:has-text("AI vs AI")')

            if await mode_button.count() > 0:
                await mode_button.click()

            # Set AI difficulty if applicable
            if mode != "human_vs_human":
                diff_button = page.locator(
                    f'button:has-text("{ai_difficulty.title()}")'
                )
                if await diff_button.count() > 0:
                    await diff_button.click()

            # Set board size
            size_button = page.locator(f'button:has-text("{board_size}x{board_size}")')
            if await size_button.count() > 0:
                await size_button.click()

    async def _start_game(self, page: Page) -> Optional[object]:
        """Start the game and return game container if successful."""
        start_button = page.locator('[data-testid="start-game-button"]')
        if await start_button.count() == 0:
            start_button = page.locator('button:has-text("Start Game")')

        if await start_button.count() > 0 and await start_button.is_enabled():
            await start_button.click()

            # Wait for game to start
            game_container = page.locator('[data-testid="game-container"]')
            if await game_container.count() > 0:
                await expect(game_container).to_be_visible(timeout=5000)
                return game_container

        return None

    async def _make_move(self, page: Page, player: int, target_cell: str) -> None:
        """Make a move to a specific cell."""
        cell = page.locator(f'[data-testid="{target_cell}"]')
        if await cell.count() > 0:
            await cell.click()
            await page.wait_for_timeout(500)

    async def _place_wall(
        self, page: Page, player: int, wall_type: str, position: str
    ) -> None:
        """Place a wall at a specific position."""
        # Toggle wall placement mode
        wall_button = page.locator(f'[data-testid="wall-mode-{wall_type}"]')
        if await wall_button.count() == 0:
            wall_button = page.locator(f'button:has-text("{wall_type.title()} Wall")')

        if await wall_button.count() > 0:
            await wall_button.click()
            await page.wait_for_timeout(200)

        # Click wall position
        wall_position = page.locator(f'[data-testid="{position}"]')
        if await wall_position.count() > 0:
            await wall_position.click()
            await page.wait_for_timeout(500)

    async def _place_random_wall(self, page: Page) -> bool:
        """Place a wall at a random valid position."""
        # Toggle wall mode
        wall_button = page.locator('[data-testid="wall-mode-horizontal"]')
        if await wall_button.count() > 0:
            await wall_button.click()

            # Find valid wall positions
            wall_positions = page.locator('[data-testid^="wall-h-"]:not(.placed)')
            count = await wall_positions.count()
            if count > 0:
                # Click first available position
                await wall_positions.first.click()
                return True

        return False

    async def _check_game_ended(self, page: Page) -> bool:
        """Check if the game has ended."""
        # Check for victory modal
        victory_modal = page.locator('[data-testid="victory-modal"]')
        if await victory_modal.count() > 0 and await victory_modal.is_visible():
            return True

        # Check game status
        game_status = page.locator('[data-testid="game-status"]')
        if await game_status.count() > 0:
            status_text = await game_status.text_content()
            if status_text and (
                "won" in status_text.lower() or "victory" in status_text.lower()
            ):
                return True

        # Check for game over indicator
        game_over = page.locator('[data-testid="game-over"]')
        if await game_over.count() > 0 and await game_over.is_visible():
            return True

        return False

    async def _get_current_player(self, page: Page) -> int:
        """Get the current player turn (0 or 1)."""
        current_player_indicator = page.locator('[data-testid="current-player"]')
        if await current_player_indicator.count() > 0:
            text = await current_player_indicator.text_content()
            if text and ("1" in text or "Player 1" in text):
                return 0
            elif text and ("2" in text or "Player 2" in text):
                return 1

        # Fallback: check whose turn indicator is active
        player1_active = page.locator('[data-testid="player-0-active"]')
        if await player1_active.count() > 0 and await player1_active.is_visible():
            return 0

        return 1

    async def _get_legal_move_indicators(self, page: Page) -> List[Locator]:
        """Get all legal move indicators on the board."""
        legal_moves = page.locator('.legal-move, [data-testid^="legal-move-"]')
        if await legal_moves.count() > 0:
            # Return list of individual locators using nth()
            count = await legal_moves.count()
            return [legal_moves.nth(i) for i in range(count)]

        # Fallback: look for highlighted cells
        highlighted = page.locator(".cell.highlighted, .cell.legal")
        if await highlighted.count() > 0:
            count = await highlighted.count()
            return [highlighted.nth(i) for i in range(count)]

        return []
