import React, { useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { useGameStore } from './store/gameStore';
import { wsService } from './services/websocket';
import { getTabManager, cleanupTabManager } from './services/tabManager';
import { GameBoard } from './components/GameBoard';
import { MoveHistory } from './components/MoveHistory';
import { GameSettings } from './components/GameSettings';
import { NewGameButton } from './components/NewGameButton';
import { exhaustiveCheck } from './types/appState';
import './App.css';

function App() {
  const store = useGameStore();
  const { connection, session } = store;
  const { gameSettings } = store.settings;
  const isConnected = store.isConnected();
  
  // Handle connection lifecycle and tab management
  useEffect(() => {
    // Initialize tab manager
    const tabManager = getTabManager();
    
    wsService.connect();
    store.dispatch({ type: 'CONNECTION_START' });
    
    return () => {
      wsService.disconnect();
      store.dispatch({ type: 'CONNECTION_LOST' });
      cleanupTabManager();
    };
  }, []);

  // Handle notifications
  useEffect(() => {
    const notifications = store.ui.notifications;
    notifications.forEach(notification => {
      if (notification.type === 'error') {
        toast.error(notification.message, {
          id: notification.id,
          duration: 4000,
          style: {
            background: '#ff4444',
            color: '#ffffff',
            fontFamily: 'Press Start 2P, monospace',
            fontSize: '10px',
          },
        });
      } else if (notification.type === 'warning') {
        toast(notification.message, {
          id: notification.id,
          duration: 6000,
          icon: '⚠️',
          style: {
            background: '#ffaa00',
            color: '#000000',
            fontFamily: 'Press Start 2P, monospace',
            fontSize: '10px',
          },
        });
      }
      // Remove notification after displaying (except persistent ones)
      if (notification.id !== 'multi-tab-conflict') {
        setTimeout(() => {
          store.dispatch({ type: 'NOTIFICATION_REMOVED', id: notification.id });
        }, notification.type === 'warning' ? 6000 : 4000);
      }
    });
  }, [store.ui.notifications]);

  // Handle tab manager integration with game state
  useEffect(() => {
    const tabManager = getTabManager();
    const gameId = store.getCurrentGameId();
    
    if (gameId) {
      tabManager.notifyGameCreated(gameId);
    } else {
      tabManager.notifyGameEnded();
    }
  }, [store.getCurrentGameId()]);

  // Handle AI moves for AI games
  useEffect(() => {
    if (session.type === 'active-game' && session.state && session.state.winner === null) {
      const gameId = session.gameId;
      const gameState = session.state;
      
      if (gameSettings.mode === 'ai_vs_ai') {
        const timer = setTimeout(() => {
          if (gameState.current_player === 0 || gameState.current_player === 1) {
            wsService.getAIMove(gameId);
          }
        }, 1000);
        return () => clearTimeout(timer);
      } else if (gameSettings.mode === 'human_vs_ai' && gameState.current_player === 1) {
        const timer = setTimeout(() => {
          wsService.getAIMove(gameId);
        }, 500);
        return () => clearTimeout(timer);
      }
    }
  }, [session, gameSettings.mode]);

  // Render based on session state - exhaustive pattern matching
  const renderContent = () => {
    switch (session.type) {
      case 'no-game':
        return (
          <div className="game-setup" data-testid="game-setup">
            <GameSettings />
          </div>
        );
      
      case 'creating-game':
        return (
          <div className="game-setup" data-testid="game-setup">
            <GameSettings />
            <div className="loading-message">Creating game...</div>
          </div>
        );
      
      case 'joining-game':
        return (
          <div className="game-loading" data-testid="game-loading">
            <GameSettings />
            <div className="loading-message">Joining game...</div>
          </div>
        );
      
      case 'active-game':
        return (
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
                  <span className="info-value game-id">{session.gameId.slice(0, 8)}</span>
                </div>
              </div>

              <div className="game-controls-panel" data-testid="game-controls-panel">
                <NewGameButton />
                <button
                  className="retro-btn"
                  onClick={() => {
                    const moveList = session.state.move_history.map(m => m.notation).join(' ');
                    navigator.clipboard.writeText(moveList);
                    toast.success('Moves copied to clipboard!', {
                      style: {
                        background: '#00ff00',
                          color: '#000000',
                          fontFamily: 'Press Start 2P, monospace',
                          fontSize: '10px',
                        },
                      });
                  }}
                  data-testid="copy-moves-button"
                >
                  Copy Moves
                </button>
              </div>
            </div>
          </div>
        );
      
      case 'game-ending':
        return (
          <div className="game-loading" data-testid="game-loading">
            <GameSettings />
            <div className="loading-message">Ending game...</div>
          </div>
        );
      
      case 'game-over':
        return (
          <div className="game-container" data-testid="game-container">
            <div className="game-left">
              <GameSettings />
              <MoveHistory />
            </div>
            <div className="game-center">
              <GameBoard />
              <div className="game-over-message">
                Game Over! Winner: Player {session.winner + 1}
              </div>
            </div>
            <div className="game-right">
              <NewGameButton />
            </div>
          </div>
        );
      
      default:
        return exhaustiveCheck(session);
    }
  };

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
        {renderContent()}
      </main>

      <footer className="app-footer">
        <p>© 2024 Corridors MCTS - Retro Gaming Edition</p>
      </footer>
    </div>
  );
}

export default App;
