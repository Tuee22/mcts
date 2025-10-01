import React from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';
import { GameMode } from '../types/game';
import { GameSettingsPanel, GameSettingsData } from './GameSettingsPanel';
import { createGameCreationSettings, GameSettingsInput } from '../utils/aiConfig';
import './GameSettings.css';

export const GameSettings: React.FC = () => {
  const store = useGameStore();
  const settingsUI = store.getSettingsUI();
  const { gameSettings } = store.settings;
  const isConnected = store.isConnected();
  const gameId = store.getCurrentGameId();

  const handleModeChange = (mode: GameMode) => {
    store.dispatch({ type: 'SETTINGS_UPDATED', settings: { mode } });
  };

  const handleDifficultyChange = (difficulty: 'easy' | 'medium' | 'hard' | 'expert') => {
    store.dispatch({ type: 'SETTINGS_UPDATED', settings: { ai_difficulty: difficulty } });
  };

  const handleTimeLimitChange = (time: number) => {
    store.dispatch({ type: 'SETTINGS_UPDATED', settings: { ai_time_limit: time } });
  };

  const handleBoardSizeChange = (size: number) => {
    store.dispatch({ type: 'SETTINGS_UPDATED', settings: { board_size: size } });
  };

  const startNewGame = async () => {
    // Type-safe: can only start game in valid state
    if (!store.canStartGame()) {
      return;
    }

    try {
      const settingsInput: GameSettingsInput = {
        mode: gameSettings.mode,
        ai_difficulty: gameSettings.ai_difficulty,
        ai_time_limit: gameSettings.ai_time_limit,
        board_size: gameSettings.board_size
      };

      const gameCreationSettings = createGameCreationSettings(settingsInput);
      await wsService.createGame(gameCreationSettings);
    } catch (error) {
      console.error('Failed to create game:', error);
      store.dispatch({ 
        type: 'GAME_CREATE_FAILED', 
        error: error instanceof Error ? error.message : 'Failed to create game' 
      });
    }
  };

  const handleToggleSettings = () => {
    store.dispatch({ type: 'SETTINGS_TOGGLED' });
  };

  const handleCancel = () => {
    store.dispatch({ type: 'SETTINGS_TOGGLED' });
  };

  // Always render based on UI state - no complex conditionals
  if (settingsUI.type === 'button-visible') {
    return (
      <button
        className="retro-btn toggle-settings"
        onClick={handleToggleSettings}
        disabled={!settingsUI.enabled}
        title={settingsUI.enabled ? 'Game Settings' : 'Connect to server to access settings'}
        data-testid="settings-toggle-button"
      >
        ⚙️ Game Settings
      </button>
    );
  }

  // Panel is visible
  const settingsData: GameSettingsData = {
    mode: gameSettings.mode,
    ai_difficulty: gameSettings.ai_difficulty,
    ai_time_limit: gameSettings.ai_time_limit,
    board_size: gameSettings.board_size
  };

  return (
    <GameSettingsPanel
      settings={settingsData}
      isConnected={isConnected}
      gameId={gameId}
      onModeChange={handleModeChange}
      onDifficultyChange={handleDifficultyChange}
      onTimeLimitChange={handleTimeLimitChange}
      onBoardSizeChange={handleBoardSizeChange}
      onStartGame={startNewGame}
      onCancel={handleCancel}
    />
  );
};