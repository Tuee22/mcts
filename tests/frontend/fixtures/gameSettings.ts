// Game settings fixtures for frontend testing

export interface GameSettings {
  mode: 'human_vs_human' | 'human_vs_ai' | 'ai_vs_ai';
  ai_difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  ai_time_limit: number; // milliseconds
  board_size: number;
}

// Default settings
export const mockDefaultGameSettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'medium',
  ai_time_limit: 5000,
  board_size: 9
};

// Human vs Human settings
export const mockHumanVsHumanSettings: GameSettings = {
  mode: 'human_vs_human',
  ai_difficulty: 'medium', // Not used but must be present
  ai_time_limit: 5000,     // Not used but must be present
  board_size: 9
};

// Easy AI settings
export const mockEasyAISettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'easy',
  ai_time_limit: 1000,
  board_size: 9
};

// Hard AI settings
export const mockHardAISettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'hard',
  ai_time_limit: 10000,
  board_size: 9
};

// Expert AI settings
export const mockExpertAISettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'expert',
  ai_time_limit: 30000,
  board_size: 9
};

// AI vs AI settings
export const mockAIVsAISettings: GameSettings = {
  mode: 'ai_vs_ai',
  ai_difficulty: 'medium',
  ai_time_limit: 5000,
  board_size: 9
};

// Small board settings
export const mockSmallBoardSettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'easy',
  ai_time_limit: 3000,
  board_size: 5
};

// Large board settings
export const mockLargeBoardSettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'hard',
  ai_time_limit: 15000,
  board_size: 13
};

// Fast AI settings (for performance testing)
export const mockFastAISettings: GameSettings = {
  mode: 'ai_vs_ai',
  ai_difficulty: 'easy',
  ai_time_limit: 100, // Very fast for testing
  board_size: 5
};

// Settings for testing edge cases
export const mockEdgeCaseSettings = {
  invalidMode: {
    mode: 'invalid_mode' as any,
    ai_difficulty: 'medium',
    ai_time_limit: 5000,
    board_size: 9
  },
  invalidDifficulty: {
    mode: 'human_vs_ai',
    ai_difficulty: 'invalid' as any,
    ai_time_limit: 5000,
    board_size: 9
  },
  zeroTimeLimit: {
    mode: 'human_vs_ai',
    ai_difficulty: 'medium',
    ai_time_limit: 0,
    board_size: 9
  },
  invalidBoardSize: {
    mode: 'human_vs_ai',
    ai_difficulty: 'medium',
    ai_time_limit: 5000,
    board_size: 0
  }
};