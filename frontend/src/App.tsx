import React, { useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { useGameStore } from './store/gameStore';
import { wsService } from './services/websocket';
import { GameBoard } from './components/GameBoard';
import { MoveHistory } from './components/MoveHistory';
import { GameSettings } from './components/GameSettings';
import { NewGameButton } from './components/NewGameButton';
import './App.css';

function App() {
  const {
    gameState,
    gameId,
    isConnected,
    error,
    gameSettings,
    setError,
    reset
  } = useGameStore();

  useEffect(() => {
    wsService.connect();
    
    return () => {
      wsService.disconnect();
    };
  }, []);

  useEffect(() => {
    if (error) {
      toast.error(error, {
        duration: 4000,
        style: {
          background: '#ff4444',
          color: '#ffffff',
          fontFamily: 'Press Start 2P, monospace',
          fontSize: '10px',
        },
      });
      setError(null);
    }
  }, [error, setError]);

  useEffect(() => {
    if (gameState && gameSettings.mode === 'ai_vs_ai' && gameId && gameState.winner === null) {
      const timer = setTimeout(() => {
        if (gameState.current_player === 0 || gameState.current_player === 1) {
          wsService.getAIMove(gameId);
        }
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [gameState, gameSettings.mode, gameId]);

  useEffect(() => {
    if (gameState && gameSettings.mode === 'human_vs_ai' && gameId && gameState.winner === null) {
      if (gameState.current_player === 1) {
        const timer = setTimeout(() => {
          wsService.getAIMove(gameId);
        }, 500);
        return () => clearTimeout(timer);
      }
    }
  }, [gameState, gameSettings.mode, gameId]);

  // App component render

  return (
    <div className="App">
      <Toaster position="top-center" />

      <header className="app-header">
        <h1 className="app-title">CORRIDORS</h1>
        <div className="connection-status" data-testid="connection-status">
          <span
            className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}
            data-testid="connection-indicator"
          ></span>
          <span className="status-text" data-testid="connection-text">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>

      <main className="app-main" data-testid="app-main">
        {!gameId ? (
          <div className="game-setup" data-testid="game-setup">
            <GameSettings />
          </div>
        ) : !gameState ? (
          <div className="game-loading" data-testid="game-loading">
            <GameSettings />
            <div className="loading-message">Loading game...</div>
          </div>
        ) : (
          <div className="game-container" data-testid="game-container">
            <div className="game-left">
              <GameSettings />
              <MoveHistory />
            </div>
            <div className="game-center">
              <GameBoard />
            </div>
            <div className="game-right">
              <div className="game-info" data-testid="game-info-panel">
                <h3>Game Info</h3>
                <div className="info-item">
                  <span className="info-label">Mode:</span>
                  <span className="info-value">{gameSettings.mode.replace(/_/g, ' ')}</span>
                </div>
                {gameSettings.mode !== 'human_vs_human' && (
                  <>
                    <div className="info-item">
                      <span className="info-label">AI Level:</span>
                      <span className="info-value">{gameSettings.ai_difficulty}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">AI Time:</span>
                      <span className="info-value">{gameSettings.ai_time_limit / 1000}s</span>
                    </div>
                  </>
                )}
                <div className="info-item">
                  <span className="info-label">Board:</span>
                  <span className="info-value">{gameSettings.board_size}x{gameSettings.board_size}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Game ID:</span>
                  <span className="info-value game-id">{gameId?.slice(0, 8)}</span>
                </div>
              </div>
              
              <div className="game-controls-panel" data-testid="game-controls-panel">
                <NewGameButton />
                <button
                  className="retro-btn"
                  onClick={() => {
                    if (gameId && gameState) {
                      const moveList = gameState.move_history.map(m => m.notation).join(' ');
                      navigator.clipboard.writeText(moveList);
                      toast.success('Moves copied to clipboard!', {
                        style: {
                          background: '#00ff00',
                          color: '#000000',
                          fontFamily: 'Press Start 2P, monospace',
                          fontSize: '10px',
                        },
                      });
                    }
                  }}
                  data-testid="copy-moves-button"
                >
                  Copy Moves
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>© 2024 Corridors MCTS - Retro Gaming Edition</p>
      </footer>
    </div>
  );
}

export default App;
