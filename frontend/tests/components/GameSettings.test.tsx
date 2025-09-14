import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the game store first with vi.hoisted (same pattern as other tests)
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
    isConnected: true,
    isLoading: false,
    error: null,
    selectedHistoryIndex: null,
    setGameId: vi.fn(),
    setGameState: vi.fn(),
    setGameSettings: vi.fn(),
    setIsConnected: vi.fn(),
    setIsLoading: vi.fn(),
    setError: vi.fn(),
    setSelectedHistoryIndex: vi.fn(),
    addMoveToHistory: vi.fn(),
    reset: vi.fn()
  };

  // Create a proper Zustand-style mock that returns the store
  const useGameStoreMock = vi.fn(() => store);
  // CRITICAL: getState must return the same store object with all methods
  useGameStoreMock.getState = vi.fn(() => store);
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

vi.mock('@/services/websocket', () => ({
  wsService: {
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    disconnectFromGame: vi.fn(),
    isConnected: vi.fn(() => true),
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    makeMove: vi.fn(() => Promise.resolve()),
    getAIMove: vi.fn(() => Promise.resolve()),
    joinGame: vi.fn(),
    requestGameState: vi.fn(() => Promise.resolve()),
    connectToGame: vi.fn(),
  }
}));

// Import components and utilities
import { GameSettings } from '@/components/GameSettings';
import { render, screen, createUser } from '../utils/testHelpers';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

describe('GameSettings Component', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the game store state for each test
    Object.assign(mockGameStore, {
      gameId: null,
      gameState: null,
      gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
      isConnected: true,
      isLoading: false,
      error: null,
      selectedHistoryIndex: null
    });
  });

  // Helper function to expand settings panel (assumes component is already rendered with toggle button)
  const expandSettings = async () => {
    const user = createUser();
    const toggleButton = screen.getByRole('button', { name: /game settings/i });
    await user.click(toggleButton);
  };

  describe('Basic Rendering', () => {
    it('renders game settings panel when no game is active', () => {
      // When gameId is null, settings panel should be shown directly
      render(<GameSettings />);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
    });

    it('renders game settings toggle button when game is active', () => {
      // Set gameId to show toggle button instead of panel
      Object.assign(mockGameStore, { gameId: 'test-game-123' });

      render(<GameSettings />);

      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toHaveTextContent('⚙️ Game Settings');
    });

    it('expands settings panel when clicked', async () => {
      // Set gameId to show toggle button instead of panel
      Object.assign(mockGameStore, { gameId: 'test-game-123' });

      render(<GameSettings />);
      const user = createUser();

      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      await user.click(toggleButton);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    it('renders all game mode options directly', () => {
      // When gameId is null, settings panel shows directly (no need to expand)
      render(<GameSettings />);

      // Use test IDs for reliable element selection
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();

      // Check text content
      expect(screen.getByText('Human vs Human')).toBeInTheDocument();
      expect(screen.getByText('Human vs AI')).toBeInTheDocument();
      expect(screen.getByText('AI vs AI')).toBeInTheDocument();
    });

    it('renders difficulty options when AI mode is selected', () => {
      // Update mock store for AI mode
      mockGameStore.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };

      render(<GameSettings />);

      expect(screen.getByText('Easy')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Hard')).toBeInTheDocument();
      expect(screen.getByText('Expert')).toBeInTheDocument();
    });
  });

  describe('Game Mode Selection', () => {
    it('highlights currently selected mode', () => {
      // Set up store with specific mode
      mockGameStore.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };

      render(<GameSettings />);

      const humanVsAIButton = screen.getByTestId('mode-human-vs-ai');
      expect(humanVsAIButton).toHaveClass('active');
    });

    it('changes mode when clicked', async () => {
      render(<GameSettings />);
      const user = createUser();

      const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
      await user.click(humanVsHumanButton);

      expect(mockGameStore.setGameSettings).toHaveBeenCalledWith({ mode: 'human_vs_human' });
    });
  });

  describe('Difficulty Selection', () => {
    beforeEach(() => {
      // Set up AI mode for difficulty tests
      mockGameStore.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };
    });

    it('highlights currently selected difficulty', async () => {
      render(<GameSettings />);

      const mediumButton = screen.getByText('Medium');
      expect(mediumButton).toHaveClass('active');
    });

    it('changes difficulty when clicked', async () => {
      render(<GameSettings />);
      const user = createUser();

      const hardButton = screen.getByText('Hard');
      await user.click(hardButton);

      expect(mockGameStore.setGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'hard' });
    });
  });

  describe('Connection Status', () => {
    it('disables settings when not connected', () => {
      mockGameStore.isConnected = false;

      render(<GameSettings />);

      // When disconnected and no gameId, shows connection warning and disabled controls
      expect(screen.getByTestId('connection-warning')).toBeInTheDocument();
      expect(screen.getByText('⚠️ Connection Required')).toBeInTheDocument();

      // All buttons should be disabled
      const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
      const startGameButton = screen.getByTestId('start-game-button');
      expect(humanVsHumanButton).toBeDisabled();
      expect(startGameButton).toBeDisabled();
      expect(startGameButton).toHaveTextContent('Disconnected');
    });

    it('disables toggle button when not connected and game is active', () => {
      mockGameStore.isConnected = false;
      mockGameStore.gameId = 'test-game-123'; // This makes toggle button show

      render(<GameSettings />);

      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
    });

    it('enables all controls when connected', async () => {
      mockGameStore.isConnected = true;

      render(<GameSettings />);

      const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
      expect(humanVsHumanButton).not.toBeDisabled();
    });
  });
});