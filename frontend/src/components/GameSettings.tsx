import React, { useState, useEffect } from 'react';
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
  const { gameSettings, setGameSettings, isLoading, isConnected, gameId, isCreatingGame } = useGameStore();
  const [showSettings, setShowSettings] = useState(false);
  const { setIsCreatingGame } = useGameStore();

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

  const startNewGame = async () => {
    if (!isConnected) {
      return;
    }

    // Prevent multiple simultaneous game creation attempts
    if (isLoading) {
      return;
    }

    try {
      // Mark that we're actively creating a game
      setIsCreatingGame(true);

      const settingsInput: GameSettingsInput = {
        mode: gameSettings.mode,
        ai_difficulty: gameSettings.ai_difficulty,
        ai_time_limit: gameSettings.ai_time_limit,
        board_size: gameSettings.board_size
      };

      const gameCreationSettings = createGameCreationSettings(settingsInput);
      await wsService.createGame(gameCreationSettings);
      setShowSettings(false);
    } catch (error) {
      // Error handling is done by the WebSocket service through the store
      // Just ensure we don't stay in loading state
      console.error('Failed to create game:', error);
      // Force clear loading state if we're still loading after error
      const { setIsLoading } = useGameStore.getState();
      setIsLoading(false);
    } finally {
      // Always clear the creating game flag
      setIsCreatingGame(false);
    }
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
      isCreatingGame={isCreatingGame}
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