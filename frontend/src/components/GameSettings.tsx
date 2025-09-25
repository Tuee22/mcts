import React, { useState } from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';
import { GameMode } from '../types/game';
import { GameSettingsPanel, GameSettingsData } from './GameSettingsPanel';
import {
  shouldShowSettingsPanel,
  shouldShowToggleButton,
  getToggleButtonTitle,
  SettingsVisibilityState
} from '../utils/settingsVisibility';
import { createGameCreationSettings, GameSettingsInput } from '../utils/aiConfig';
import './GameSettings.css';

export const GameSettings: React.FC = () => {
  const { gameSettings, setGameSettings, isLoading, isConnected, gameId } = useGameStore();
  const [showSettings, setShowSettings] = useState(false);

  const visibilityState: SettingsVisibilityState = {
    showSettings,
    gameId,
    isConnected
  };

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
    if (!isConnected) {
      return;
    }

    const settingsInput: GameSettingsInput = {
      mode: gameSettings.mode,
      ai_difficulty: gameSettings.ai_difficulty,
      ai_time_limit: gameSettings.ai_time_limit,
      board_size: gameSettings.board_size
    };

    const gameCreationSettings = createGameCreationSettings(settingsInput);
    wsService.createGame(gameCreationSettings);
    setShowSettings(false);
  };

  // Use extracted visibility logic for better testability
  if (shouldShowToggleButton(visibilityState)) {
    return (
      <button
        className="retro-btn toggle-settings"
        onClick={() => setShowSettings(true)}
        disabled={!isConnected}
        title={getToggleButtonTitle(isConnected)}
        data-testid="settings-toggle-button"
      >
        ⚙️ Game Settings
      </button>
    );
  }

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
      isLoading={isLoading}
      gameId={gameId}
      onModeChange={handleModeChange}
      onDifficultyChange={handleDifficultyChange}
      onTimeLimitChange={handleTimeLimitChange}
      onBoardSizeChange={handleBoardSizeChange}
      onStartGame={startNewGame}
      onCancel={() => setShowSettings(false)}
    />
  );
};