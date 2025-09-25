/**
 * AI Configuration Utilities
 *
 * Extracted from GameSettings component to enable better testing
 * of AI configuration generation logic.
 */

import { GameMode } from '../types/game';

export interface AIConfiguration {
  difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  time_limit_ms: number;
  use_mcts: boolean;
  mcts_iterations: number;
}

export interface GameSettingsInput {
  mode: GameMode;
  ai_difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  ai_time_limit: number;
  board_size: number;
}

export interface GameCreationSettings {
  mode: GameMode;
  ai_config?: AIConfiguration;
  board_size: number;
}

/**
 * Generates AI configuration based on difficulty level
 * @param difficulty AI difficulty setting
 * @param timeLimit Time limit in milliseconds
 * @returns AI configuration object
 */
export const generateAIConfig = (
  difficulty: 'easy' | 'medium' | 'hard' | 'expert',
  timeLimit: number
): AIConfiguration => {
  const mctsIterationsMap = {
    easy: 100,
    medium: 1000,
    hard: 5000,
    expert: 10000
  };

  return {
    difficulty,
    time_limit_ms: timeLimit,
    use_mcts: difficulty !== 'easy',
    mcts_iterations: mctsIterationsMap[difficulty]
  };
};

/**
 * Creates game creation settings from game settings input
 * @param settings Game settings from UI
 * @returns Settings ready for game creation API
 */
export const createGameCreationSettings = (settings: GameSettingsInput): GameCreationSettings => {
  const gameSettings: GameCreationSettings = {
    mode: settings.mode,
    board_size: settings.board_size
  };

  // Only include AI config for modes that use AI
  if (settings.mode !== 'human_vs_human') {
    gameSettings.ai_config = generateAIConfig(
      settings.ai_difficulty,
      settings.ai_time_limit
    );
  }

  return gameSettings;
};

/**
 * Validates that all required settings are present
 * @param settings Game settings to validate
 * @returns true if settings are valid
 */
export const validateGameSettings = (settings: GameSettingsInput): boolean => {
  // Basic validation
  if (!settings.mode || !settings.board_size) {
    return false;
  }

  // AI modes require AI configuration
  if (settings.mode !== 'human_vs_human') {
    if (!settings.ai_difficulty || !settings.ai_time_limit) {
      return false;
    }
  }

  return true;
};