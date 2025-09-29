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
  const isTransitioning = store.session.type === 'game-ending';

  // Type-safe: Only render when game is active or ending
  if (!gameId) {
    return null;
  }

  const isDisabled = !isConnected || isTransitioning;

  const getTitle = () => {
    if (!isConnected) return 'Connect to server to start a new game';
    if (isTransitioning) return 'Ending current game...';
    return 'Start a new game';
  };

  const handleNewGame = () => {
    if (isDisabled) return;

    // Type-safe state transition: active-game -> game-ending -> no-game
    store.dispatch({ type: 'NEW_GAME_CLICKED' });
    
    // Disconnect from game-specific WebSocket
    wsService.disconnectFromGame();
    
    // Transition to no-game state after cleanup
    setTimeout(() => {
      store.dispatch({ type: 'GAME_ENDING_COMPLETE' });
    }, 100);
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