import React from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';
import { createGameCreationSettings } from '../utils/aiConfig';

interface NewGameButtonProps {
  className?: string;
  dataTestId?: string;
}

export const NewGameButton: React.FC<NewGameButtonProps> = ({
  className = "retro-btn new-game",
  dataTestId = "new-game-button"
}) => {
  const {
    gameId,
    isConnected,
    isLoading,
    gameSettings,
    reset
  } = useGameStore();

  // Don't render if no active game
  if (!gameId) {
    return null;
  }

  const isDisabled = !isConnected || isLoading;

  const getTitle = () => {
    if (!isConnected) return 'Connect to server to start a new game';
    if (isLoading) return 'Please wait, starting new game...';
    return 'Start a new game';
  };

  const handleNewGame = async () => {
    if (isDisabled) return;

    // Disconnect from game-specific WebSocket first to prevent race conditions
    wsService.disconnectFromGame();
    reset();

    // Create new game with current settings
    const gameCreationSettings = createGameCreationSettings({
      mode: gameSettings.mode,
      ai_difficulty: gameSettings.ai_difficulty,
      ai_time_limit: gameSettings.ai_time_limit,
      board_size: gameSettings.board_size
    });

    try {
      await wsService.createGame(gameCreationSettings);
    } catch (error) {
      console.error('Failed to create new game:', error);
    }
  };

  return (
    <button
      type="button"
      className={className}
      onClick={handleNewGame}
      disabled={isDisabled}
      title={getTitle()}
      data-testid={dataTestId}
      aria-label="Start new game"
    >
      New Game
    </button>
  );
};