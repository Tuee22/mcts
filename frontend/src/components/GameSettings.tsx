import React, { useMemo } from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';
import { GameMode } from '../types/game';
import { SettingsUIState } from '../types/appState';
import { GameSettingsPanel, GameSettingsData } from './GameSettingsPanel';
import { createGameCreationSettings, GameSettingsInput } from '../utils/aiConfig';
import './GameSettings.css';

export const GameSettings: React.FC = () => {
  // Select primitive values to avoid object creation in selectors
  const connection = useGameStore((store) => store.connection);
  const session = useGameStore((store) => store.session);
  const settingsExpanded = useGameStore((store) => store.ui.settingsExpanded);
  const gameSettings = useGameStore((store) => store.settings.gameSettings);
  const dispatch = useGameStore((store) => store.dispatch);
  
  // Compute derived values using useMemo to prevent infinite loops
  const isConnected = useMemo(() => connection.type === 'connected', [connection.type]);
  const gameId = useMemo(() => {
    return (session.type === 'active-game' || session.type === 'game-over') 
      ? session.gameId : null;
  }, [session]);
  const canStartGame = useMemo(() => isConnected && session.type === 'no-game', [isConnected, session.type]);
  const settingsUI = useMemo((): SettingsUIState => {
    if (settingsExpanded) {
      return { type: 'panel-visible', canStartGame };
    }
    switch (session.type) {
      case 'no-game':
        return { type: 'panel-visible', canStartGame };
      case 'active-game':
      case 'game-over':
        return { type: 'button-visible', enabled: isConnected };
      default:
        return { type: 'button-visible', enabled: false };
    }
  }, [settingsExpanded, canStartGame, session.type, isConnected]);

  const handleModeChange = (mode: GameMode) => {
    dispatch({ type: 'SETTINGS_UPDATED', settings: { mode } });
  };

  const handleDifficultyChange = (difficulty: 'easy' | 'medium' | 'hard' | 'expert') => {
    dispatch({ type: 'SETTINGS_UPDATED', settings: { ai_difficulty: difficulty } });
  };

  const handleTimeLimitChange = (time: number) => {
    dispatch({ type: 'SETTINGS_UPDATED', settings: { ai_time_limit: time } });
  };

  const handleBoardSizeChange = (size: number) => {
    dispatch({ type: 'SETTINGS_UPDATED', settings: { board_size: size } });
  };

  const startNewGame = async () => {
    // Type-safe: can only start game in valid state
    if (!canStartGame) {
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
      dispatch({ 
        type: 'GAME_CREATE_FAILED', 
        error: error instanceof Error ? error.message : 'Failed to create game' 
      });
    }
  };

  const handleToggleSettings = () => {
    dispatch({ type: 'SETTINGS_TOGGLED' });
  };

  const handleCancel = () => {
    dispatch({ type: 'SETTINGS_TOGGLED' });
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