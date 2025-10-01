import React from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';

interface NewGameButtonProps {
  className?: string;
  dataTestId?: string;
}

export const NewGameButton: React.FC<NewGameButtonProps> = ({
  className = "retro-btn new-game",
  dataTestId = "new-game-button"
}) => {
  const store = useGameStore();
  const isConnected = store.isConnected();
  const gameId = store.getCurrentGameId();
  // Type-safe: Only render when game is active or over
  if (!gameId) {
    return null;
  }

  const isDisabled = !isConnected;

  const getTitle = () => {
    if (!isConnected) return 'Connect to server to start a new game';
    return 'Start a new game';
  };

  const handleNewGame = () => {
    if (isDisabled) return;

    // With simplified state machine: direct transition to no-game
    store.dispatch({ type: 'NEW_GAME_REQUESTED' });
    
    // Disconnect from game-specific WebSocket
    wsService.disconnectFromGame();
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