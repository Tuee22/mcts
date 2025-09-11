import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { createMockGameStore, createMockWebSocketService } from '../fixtures/mocks';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

// Create mock instances
const mockGameStore = createMockGameStore({
  gameSettings: mockDefaultGameSettings,
  isConnected: true,
  isLoading: false
});

const mockWsService = createMockWebSocketService();

// Mock dependencies
vi.mock('@/store/gameStore', () => ({
  useGameStore: vi.fn(() => mockGameStore)
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

// Import component after mocking
import { GameSettings } from '@/components/GameSettings';

describe('GameSettings Component', () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = userEvent.setup();
    
    // Reset mock returns
    mockGameStore.resetMocks();
    mockWsService.reset();
  });

  // Helper function to expand settings panel
  const expandSettings = async () => {
    const toggleButton = screen.getByRole('button', { name: /game settings/i });
    await user.click(toggleButton);
  };

  describe('Basic Rendering', () => {
    it('renders game settings toggle button', () => {
      render(<GameSettings />);
      
      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toHaveTextContent('⚙️ Game Settings');
    });

    it('expands settings panel when clicked', async () => {
      render(<GameSettings />);
      
      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      await user.click(toggleButton);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    it('renders all game mode options when expanded', async () => {
      render(<GameSettings />);
      await expandSettings();

      // Use test IDs for reliable element selection
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
      
      // Check text content
      expect(screen.getByText('Human vs Human')).toBeInTheDocument();
      expect(screen.getByText('Human vs AI')).toBeInTheDocument();
      expect(screen.getByText('AI vs AI')).toBeInTheDocument();
    });

    it('renders difficulty options when AI mode is selected', async () => {
      // Update mock store for AI mode
      mockGameStore.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };

      render(<GameSettings />);
      await expandSettings();

      expect(screen.getByText('Easy')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Hard')).toBeInTheDocument();
      expect(screen.getByText('Expert')).toBeInTheDocument();
    });
  });

  describe('Game Mode Selection', () => {
    it('highlights currently selected mode', async () => {
      // Set up store with specific mode
      mockGameStore.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };

      render(<GameSettings />);
      await expandSettings();

      const humanVsAIButton = screen.getByTestId('mode-human-vs-ai');
      expect(humanVsAIButton).toHaveClass('active');
    });

    it('changes mode when clicked', async () => {
      render(<GameSettings />);
      await expandSettings();

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
      await expandSettings();

      const mediumButton = screen.getByText('Medium');
      expect(mediumButton).toHaveClass('active');
    });

    it('changes difficulty when clicked', async () => {
      render(<GameSettings />);
      await expandSettings();

      const hardButton = screen.getByText('Hard');
      await user.click(hardButton);

      expect(mockGameStore.setGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'hard' });
    });
  });

  describe('Connection Status', () => {
    it('disables settings when not connected', () => {
      mockGameStore.isConnected = false;

      render(<GameSettings />);
      
      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      expect(toggleButton).toBeDisabled();
    });

    it('enables all controls when connected', async () => {
      mockGameStore.isConnected = true;

      render(<GameSettings />);
      await expandSettings();

      const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
      expect(humanVsHumanButton).not.toBeDisabled();
    });
  });
});