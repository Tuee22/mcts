import React, { useState } from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';
import { GameMode } from '../types/game';
import './GameSettings.css';

export const GameSettings: React.FC = () => {
  console.log('🔧 GameSettings component loaded with updated code!');
  
  const { gameSettings, setGameSettings, isLoading, isConnected } = useGameStore();
  const [showSettings, setShowSettings] = useState(false);

  const handleModeChange = (mode: GameMode) => {
    setGameSettings({ mode });
  };

  const handleDifficultyChange = (difficulty: 'easy' | 'medium' | 'hard' | 'expert') => {
    setGameSettings({ ai_difficulty: difficulty });
  };

  const handleTimeLimitChange = (time: number) => {
    setGameSettings({ ai_time_limit: time });
  };

  const handleBoardSizeChange = (size: number) => {
    setGameSettings({ board_size: size });
  };

  const startNewGame = () => {
    console.log('🚀 startNewGame called!');
    console.log('  isConnected:', isConnected);
    console.log('  gameSettings:', gameSettings);
    
    if (!isConnected) {
      console.error('❌ Cannot start game while disconnected');
      return;
    }

    const settings = {
      mode: gameSettings.mode,
      ai_config: gameSettings.mode !== 'human_vs_human' ? {
        difficulty: gameSettings.ai_difficulty,
        time_limit_ms: gameSettings.ai_time_limit,
        use_mcts: gameSettings.ai_difficulty !== 'easy',
        mcts_iterations: gameSettings.ai_difficulty === 'medium' ? 1000 :
                         gameSettings.ai_difficulty === 'hard' ? 5000 :
                         gameSettings.ai_difficulty === 'expert' ? 10000 : 100
      } : undefined,
      board_size: gameSettings.board_size
    };

    console.log('✅ About to call wsService.createGame with settings:', settings);
    
    try {
      wsService.createGame(settings);
      console.log('✅ wsService.createGame called successfully');
    } catch (error) {
      console.error('❌ Error calling wsService.createGame:', error);
    }
    
    setShowSettings(false);
    console.log('✅ Settings closed');
  };

  if (!showSettings) {
    return (
      <button 
        className="retro-btn toggle-settings"
        onClick={() => setShowSettings(true)}
        disabled={!isConnected}
        title={!isConnected ? 'Connect to server to access settings' : 'Game Settings'}
      >
        ⚙️ Game Settings
      </button>
    );
  }

  return (
    <div className="game-settings-container">
      <h2>Game Settings</h2>
      
      {!isConnected && (
        <div className="connection-warning" data-testid="connection-warning">
          <h3>⚠️ Connection Required</h3>
          <p>Please connect to the server before configuring game settings.</p>
        </div>
      )}
      
      <div className={!isConnected ? 'settings-disabled' : ''}>
      
      <div className="settings-group">
        <label>Game Mode</label>
        <div className="mode-buttons">
          <button
            className={`mode-btn ${gameSettings.mode === 'human_vs_human' ? 'active' : ''}`}
            onClick={() => handleModeChange('human_vs_human')}
            disabled={!isConnected}
            data-testid="mode-human-vs-human"
          >
            <span className="mode-icon">👤 vs 👤</span>
            <span className="mode-label">Human vs Human</span>
          </button>
          <button
            className={`mode-btn ${gameSettings.mode === 'human_vs_ai' ? 'active' : ''}`}
            onClick={() => handleModeChange('human_vs_ai')}
            disabled={!isConnected}
            data-testid="mode-human-vs-ai"
          >
            <span className="mode-icon">👤 vs 🤖</span>
            <span className="mode-label">Human vs AI</span>
          </button>
          <button
            className={`mode-btn ${gameSettings.mode === 'ai_vs_ai' ? 'active' : ''}`}
            onClick={() => handleModeChange('ai_vs_ai')}
            disabled={!isConnected}
            data-testid="mode-ai-vs-ai"
          >
            <span className="mode-icon">🤖 vs 🤖</span>
            <span className="mode-label">AI vs AI</span>
          </button>
        </div>
      </div>

      {gameSettings.mode !== 'human_vs_human' && (
        <div className="settings-group">
          <label>AI Difficulty</label>
          <div className="difficulty-buttons">
            <button
              className={`difficulty-btn ${gameSettings.ai_difficulty === 'easy' ? 'active' : ''}`}
              onClick={() => handleDifficultyChange('easy')}
              disabled={!isConnected}
            >
              Easy
            </button>
            <button
              className={`difficulty-btn ${gameSettings.ai_difficulty === 'medium' ? 'active' : ''}`}
              onClick={() => handleDifficultyChange('medium')}
              disabled={!isConnected}
            >
              Medium
            </button>
            <button
              className={`difficulty-btn ${gameSettings.ai_difficulty === 'hard' ? 'active' : ''}`}
              onClick={() => handleDifficultyChange('hard')}
              disabled={!isConnected}
            >
              Hard
            </button>
            <button
              className={`difficulty-btn ${gameSettings.ai_difficulty === 'expert' ? 'active' : ''}`}
              onClick={() => handleDifficultyChange('expert')}
              disabled={!isConnected}
            >
              Expert
            </button>
          </div>
        </div>
      )}

      {gameSettings.mode !== 'human_vs_human' && (
        <div className="settings-group">
          <label>AI Time Limit</label>
          <div className="time-buttons">
            <button
              className={`time-btn ${gameSettings.ai_time_limit === 1000 ? 'active' : ''}`}
              onClick={() => handleTimeLimitChange(1000)}
              disabled={!isConnected}
            >
              1s
            </button>
            <button
              className={`time-btn ${gameSettings.ai_time_limit === 3000 ? 'active' : ''}`}
              onClick={() => handleTimeLimitChange(3000)}
              disabled={!isConnected}
            >
              3s
            </button>
            <button
              className={`time-btn ${gameSettings.ai_time_limit === 5000 ? 'active' : ''}`}
              onClick={() => handleTimeLimitChange(5000)}
              disabled={!isConnected}
            >
              5s
            </button>
            <button
              className={`time-btn ${gameSettings.ai_time_limit === 10000 ? 'active' : ''}`}
              onClick={() => handleTimeLimitChange(10000)}
              disabled={!isConnected}
            >
              10s
            </button>
          </div>
        </div>
      )}

      <div className="settings-group">
        <label>Board Size</label>
        <div className="size-buttons">
          <button
            className={`size-btn ${gameSettings.board_size === 5 ? 'active' : ''}`}
            onClick={() => handleBoardSizeChange(5)}
            disabled={!isConnected}
          >
            5x5
          </button>
          <button
            className={`size-btn ${gameSettings.board_size === 7 ? 'active' : ''}`}
            onClick={() => handleBoardSizeChange(7)}
            disabled={!isConnected}
          >
            7x7
          </button>
          <button
            className={`size-btn ${gameSettings.board_size === 9 ? 'active' : ''}`}
            onClick={() => handleBoardSizeChange(9)}
            disabled={!isConnected}
          >
            9x9
          </button>
        </div>
      </div>

      <div className="settings-actions">
        <button 
          className="retro-btn start-game"
          onClick={startNewGame}
          disabled={isLoading || !isConnected}
          data-testid="start-game-button"
        >
          {isLoading ? 'Starting...' : !isConnected ? 'Disconnected' : 'Start Game'}
        </button>
        <button 
          className="retro-btn cancel"
          onClick={() => setShowSettings(false)}
        >
          Cancel
        </button>
      </div>
      </div>
    </div>
  );
};