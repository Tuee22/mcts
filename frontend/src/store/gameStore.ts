import { create } from 'zustand';
import { GameState, GameSettings, Move } from '../types/game';

interface GameStore {
  gameId: string | null;
  gameState: GameState | null;
  gameSettings: GameSettings;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  selectedHistoryIndex: number | null;
  
  setGameId: (id: string | null) => void;
  setGameState: (state: GameState | null) => void;
  setGameSettings: (settings: Partial<GameSettings>) => void;
  setIsConnected: (connected: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSelectedHistoryIndex: (index: number | null) => void;
  addMoveToHistory: (move: Move) => void;
  reset: () => void;
}

const defaultSettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'medium',
  ai_time_limit: 5000,
  board_size: 9,
};

export const useGameStore = create<GameStore>((set) => ({
  gameId: null,
  gameState: null,
  gameSettings: defaultSettings,
  isConnected: false,
  isLoading: false,
  error: null,
  selectedHistoryIndex: null,
  
  setGameId: (id) => set({ gameId: id }),
  setGameState: (state) => set({ gameState: state }),
  setGameSettings: (settings) => set((state) => ({
    gameSettings: { ...state.gameSettings, ...settings }
  })),
  setIsConnected: (connected) => set({ isConnected: connected }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setSelectedHistoryIndex: (index) => set({ selectedHistoryIndex: index }),
  addMoveToHistory: (move) => set((state) => ({
    gameState: state.gameState ? {
      ...state.gameState,
      move_history: [...state.gameState.move_history, move]
    } : null
  })),
  reset: () => set({
    gameId: null,
    gameState: null,
    gameSettings: defaultSettings,
    isConnected: false,
    isLoading: false,
    error: null,
    selectedHistoryIndex: null,
  }),
}));