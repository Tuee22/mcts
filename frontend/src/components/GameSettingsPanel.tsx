import React from 'react';
import { GameMode } from '../types/game';

export interface GameSettingsData {
  mode: GameMode;
  ai_difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  ai_time_limit: number;
  board_size: number;
}

export interface GameSettingsPanelProps {
  settings: GameSettingsData;
  isConnected: boolean;
  isLoading: boolean;
  gameId: string | null;
  onModeChange: (mode: GameMode) => void;
  onDifficultyChange: (difficulty: 'easy' | 'medium' | 'hard' | 'expert') => void;
  onTimeLimitChange: (time: number) => void;
  onBoardSizeChange: (size: number) => void;
  onStartGame: () => void;
  onCancel?: () => void;
}

/**
 * Pure GameSettings panel component for better testability.
 * Decoupled from game state and WebSocket service.
 */
export const GameSettingsPanel: React.FC<GameSettingsPanelProps> = ({
  settings,
  isConnected,
  isLoading,
  gameId,
  onModeChange,
  onDifficultyChange,
  onTimeLimitChange,
  onBoardSizeChange,
  onStartGame,
  onCancel
}) => {
  return (
    <div className="game-settings-container" data-testid="game-settings-panel">
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
            className={`mode-btn ${settings.mode === 'human_vs_human' ? 'active' : ''}`}
            onClick={() => onModeChange('human_vs_human')}
            disabled={!isConnected}
            data-testid="mode-human-vs-human"
          >
            <span className="mode-icon">👤 vs 👤</span>
            <span className="mode-label">Human vs Human</span>
          </button>
          <button
            className={`mode-btn ${settings.mode === 'human_vs_ai' ? 'active' : ''}`}
            onClick={() => onModeChange('human_vs_ai')}
            disabled={!isConnected}
            data-testid="mode-human-vs-ai"
          >
            <span className="mode-icon">👤 vs 🤖</span>
            <span className="mode-label">Human vs AI</span>
          </button>
          <button
            className={`mode-btn ${settings.mode === 'ai_vs_ai' ? 'active' : ''}`}
            onClick={() => onModeChange('ai_vs_ai')}
            disabled={!isConnected}
            data-testid="mode-ai-vs-ai"
          >
            <span className="mode-icon">🤖 vs 🤖</span>
            <span className="mode-label">AI vs AI</span>
          </button>
        </div>
      </div>

      {settings.mode !== 'human_vs_human' && (
        <div className="settings-group" data-testid="ai-difficulty-group">
          <label>AI Difficulty</label>
          <div className="difficulty-buttons">
            <button
              className={`difficulty-btn ${settings.ai_difficulty === 'easy' ? 'active' : ''}`}
              onClick={() => onDifficultyChange('easy')}
              disabled={!isConnected}
              data-testid="difficulty-easy"
            >
              Easy
            </button>
            <button
              className={`difficulty-btn ${settings.ai_difficulty === 'medium' ? 'active' : ''}`}
              onClick={() => onDifficultyChange('medium')}
              disabled={!isConnected}
              data-testid="difficulty-medium"
            >
              Medium
            </button>
            <button
              className={`difficulty-btn ${settings.ai_difficulty === 'hard' ? 'active' : ''}`}
              onClick={() => onDifficultyChange('hard')}
              disabled={!isConnected}
              data-testid="difficulty-hard"
            >
              Hard
            </button>
            <button
              className={`difficulty-btn ${settings.ai_difficulty === 'expert' ? 'active' : ''}`}
              onClick={() => onDifficultyChange('expert')}
              disabled={!isConnected}
              data-testid="difficulty-expert"
            >
              Expert
            </button>
          </div>
        </div>
      )}

      {settings.mode !== 'human_vs_human' && (
        <div className="settings-group" data-testid="ai-time-limit-group">
          <label>AI Time Limit</label>
          <div className="time-buttons">
            <button
              className={`time-btn ${settings.ai_time_limit === 1000 ? 'active' : ''}`}
              onClick={() => onTimeLimitChange(1000)}
              disabled={!isConnected}
              data-testid="time-limit-1s"
            >
              1s
            </button>
            <button
              className={`time-btn ${settings.ai_time_limit === 3000 ? 'active' : ''}`}
              onClick={() => onTimeLimitChange(3000)}
              disabled={!isConnected}
              data-testid="time-limit-3s"
            >
              3s
            </button>
            <button
              className={`time-btn ${settings.ai_time_limit === 5000 ? 'active' : ''}`}
              onClick={() => onTimeLimitChange(5000)}
              disabled={!isConnected}
              data-testid="time-limit-5s"
            >
              5s
            </button>
            <button
              className={`time-btn ${settings.ai_time_limit === 10000 ? 'active' : ''}`}
              onClick={() => onTimeLimitChange(10000)}
              disabled={!isConnected}
              data-testid="time-limit-10s"
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
            className={`size-btn ${settings.board_size === 5 ? 'active' : ''}`}
            onClick={() => onBoardSizeChange(5)}
            disabled={!isConnected}
            data-testid="board-size-5"
          >
            5x5
          </button>
          <button
            className={`size-btn ${settings.board_size === 7 ? 'active' : ''}`}
            onClick={() => onBoardSizeChange(7)}
            disabled={!isConnected}
            data-testid="board-size-7"
          >
            7x7
          </button>
          <button
            className={`size-btn ${settings.board_size === 9 ? 'active' : ''}`}
            onClick={() => onBoardSizeChange(9)}
            disabled={!isConnected}
            data-testid="board-size-9"
          >
            9x9
          </button>
        </div>
      </div>

      <div className="settings-actions">
        <button
          className="retro-btn start-game"
          onClick={onStartGame}
          disabled={isLoading || !isConnected}
          data-testid="start-game-button"
        >
          {isLoading ? 'Starting...' : !isConnected ? 'Disconnected' : 'Start Game'}
        </button>
        {gameId && onCancel && (
          <button
            className="retro-btn cancel"
            onClick={onCancel}
            data-testid="cancel-settings-button"
          >
            Cancel
          </button>
        )}
      </div>
      </div>
    </div>
  );
};