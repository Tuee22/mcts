import React, { useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { useGameStore } from './store/gameStore';
import { wsService } from './services/websocket';
import { 
  initializeTabCoordinator, 
  cleanupTabCoordinator, 
  getTabCoordinator,
  TabCoordinationResult
} from './services/functionalTabCoordinator';
import { GameBoard } from './components/GameBoard';
import { MoveHistory } from './components/MoveHistory';
import { GameSettings } from './components/GameSettings';
import { NewGameButton } from './components/NewGameButton';
import { ErrorBoundary } from './components/ErrorBoundary';
import { exhaustiveCheck } from './types/appState';
import './App.css';

function App() {
  const session = useGameStore((store) => store.session);
  const gameSettings = useGameStore((store) => store.settings.gameSettings);
  const isConnected = useGameStore((store) => store.isConnected());
  const dispatch = useGameStore((store) => store.dispatch);
  const currentGameId = useGameStore((store) => store.getCurrentGameId());
  
  // Handle connection lifecycle and tab coordination
  useEffect(() => {
    // Initialize functional tab coordinator
    initializeTabCoordinator((result: TabCoordinationResult) => {
      if (result.shouldShowConflictWarning && result.conflictMessage) {
        // Handle multi-tab conflict functionally - but don't force disconnect
        // All tabs maintain their WebSocket connections
        
        dispatch({
          type: 'NOTIFICATION_ADDED',
          notification: {
            id: result.isPrimary ? 'primary-tab-info' : 'multi-tab-conflict',
            type: result.isPrimary ? 'warning' : 'warning', // Changed error to warning for secondary tabs
            message: result.conflictMessage,
            timestamp: new Date()
          }
        });
      } else {
        // Clear any existing multi-tab notifications
        dispatch({
          type: 'NOTIFICATION_REMOVED',
          id: 'multi-tab-conflict'
        });
        dispatch({
          type: 'NOTIFICATION_REMOVED',
          id: 'primary-tab-info'
        });
      }
    });
    
    // Initial connection
    wsService.connect();
    dispatch({ type: 'CONNECTION_START' });

    // Handle page visibility changes to reconnect after browser navigation
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Check if this is likely from browser navigation
        const navigationTime = sessionStorage.getItem('ws-navigation-time');
        const timeSinceNavigation = navigationTime ? Date.now() - parseInt(navigationTime) : Infinity;
        
        // If navigation was recent (within 5 seconds), attempt immediate reconnection
        if (timeSinceNavigation < 5000) {
          console.log('Page became visible after recent navigation, attempting immediate reconnection...');
          const currentlyConnected = useGameStore.getState().isConnected();
          if (!currentlyConnected) {
            wsService.connect();
            dispatch({ type: 'CONNECTION_START' });
          }
          sessionStorage.removeItem('ws-navigation-time');
        } else {
          // Normal visibility change, small delay
          setTimeout(() => {
            const currentlyConnected = useGameStore.getState().isConnected();
            if (!currentlyConnected) {
              console.log('Page became visible, attempting WebSocket reconnection...');
              wsService.connect();
              dispatch({ type: 'CONNECTION_START' });
            }
          }, 100);
        }
      }
    };

    // Handle page focus to reconnect
    const handleFocus = () => {
      setTimeout(() => {
        const currentlyConnected = useGameStore.getState().isConnected();
        if (!currentlyConnected) {
          console.log('Page focused, attempting WebSocket reconnection...');
          wsService.connect();
          dispatch({ type: 'CONNECTION_START' });
        }
      }, 100);
    };

    // Handle browser back/forward navigation
    const handlePopState = () => {
      console.log('Browser navigation detected (popstate), attempting WebSocket reconnection...');
      setTimeout(() => {
        const currentlyConnected = useGameStore.getState().isConnected();
        if (!currentlyConnected) {
          wsService.connect();
          dispatch({ type: 'CONNECTION_START' });
        }
      }, 200);
    };

    // Handle page show event (triggered on browser back/forward)
    const handlePageShow = (event: PageTransitionEvent) => {
      console.log('Page show event detected, attempting WebSocket reconnection...', { persisted: event.persisted });
      // Immediate reconnection for browser navigation (no delay)
      const currentlyConnected = useGameStore.getState().isConnected();
      if (!currentlyConnected) {
        wsService.connect();
        dispatch({ type: 'CONNECTION_START' });
      }
    };

    // Handle page hide event for clean disconnect
    const handlePageHide = () => {
      console.log('Page hide event detected, preserving connection state...');
      // Don't disconnect, just note that navigation is happening
      sessionStorage.setItem('ws-navigation-time', Date.now().toString());
    };

    // Handle window load event for page reloads
    const handleWindowLoad = () => {
      console.log('Window load event detected, ensuring WebSocket connection...');
      // Force a fresh connection on page reload
      setTimeout(() => {
        const currentlyConnected = useGameStore.getState().isConnected();
        if (!currentlyConnected) {
          console.log('Page loaded but not connected, forcing fresh connection...');
          wsService.resetConnection();
          dispatch({ type: 'CONNECTION_START' });
        }
      }, 100);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('pageshow', handlePageShow);
    window.addEventListener('pagehide', handlePageHide);
    window.addEventListener('load', handleWindowLoad);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('pageshow', handlePageShow);
      window.removeEventListener('pagehide', handlePageHide);
      window.removeEventListener('load', handleWindowLoad);
      wsService.disconnect();
      dispatch({ type: 'CONNECTION_LOST' });
      cleanupTabCoordinator();
    };
  }, [dispatch]); // Removed isConnected to prevent reconnection loop

  // Handle notifications
  const notifications = useGameStore((store) => store.ui.notifications);
  useEffect(() => {
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
          dispatch({ type: 'NOTIFICATION_REMOVED', id: notification.id });
        }, notification.type === 'warning' ? 6000 : 4000);
      }
    });
  }, [notifications, dispatch]);

  // Handle tab coordinator integration with game state
  useEffect(() => {
    const coordinator = getTabCoordinator();
    const gameId = currentGameId;
    
    if (coordinator) {
      if (gameId) {
        coordinator.notifyGameCreated(gameId);
      } else {
        coordinator.notifyGameEnded();
      }
    }
  }, [currentGameId]);

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
            <ErrorBoundary fallback={<div>Error loading game settings</div>}>
              <GameSettings />
            </ErrorBoundary>
          </div>
        );
      
      
      case 'active-game':
        return (
          <div className="game-container" data-testid="game-container">
            <div className="game-left">
              <ErrorBoundary fallback={<div>Error loading settings</div>}>
                <GameSettings />
              </ErrorBoundary>
              <ErrorBoundary fallback={<div>Error loading history</div>}>
                <MoveHistory />
              </ErrorBoundary>
            </div>
            <div className="game-center">
              <ErrorBoundary fallback={<div>Error loading game board</div>}>
                <GameBoard />
              </ErrorBoundary>
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
      
      case 'game-over':
        return (
          <div className="game-container" data-testid="game-container">
            <div className="game-left">
              <ErrorBoundary fallback={<div>Error loading settings</div>}>
                <GameSettings />
              </ErrorBoundary>
              <ErrorBoundary fallback={<div>Error loading history</div>}>
                <MoveHistory />
              </ErrorBoundary>
            </div>
            <div className="game-center">
              <ErrorBoundary fallback={<div>Error loading game board</div>}>
                <GameBoard />
              </ErrorBoundary>
              <div className="game-over-message">
                Game Over! Winner: Player {session.winner + 1}
              </div>
            </div>
            <div className="game-right">
              <ErrorBoundary fallback={<div>Error loading controls</div>}>
                <NewGameButton />
              </ErrorBoundary>
            </div>
          </div>
        );
      
      default:
        // Handle unhandled session states gracefully
        const result = exhaustiveCheck(session);
        if (result === null) {
          // Fallback for invalid states in development/testing
          return (
            <div className="game-setup" data-testid="game-setup">
              <ErrorBoundary fallback={<div>Error: Invalid game state</div>}>
                <GameSettings />
              </ErrorBoundary>
            </div>
          );
        }
        return result;
    }
  };

  return (
    <div className="App">
      <Toaster position="top-center" />

      <header className="app-header">
        <h1 className="app-title">CORRIDORS - Build Test v2</h1>
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
