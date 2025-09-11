import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the store and services first (hoisted)
vi.mock('@/store/gameStore', () => ({
  useGameStore: vi.fn()
}));

vi.mock('@/services/websocket', () => ({
  wsService: {
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    isConnected: vi.fn(() => true),
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    makeMove: vi.fn(() => Promise.resolve()),
    getAIMove: vi.fn(() => Promise.resolve()),
  }
}));

vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn()
  },
  Toaster: () => React.createElement('div', { 'data-testid': 'toaster' })
}));

// Import components and test utilities
import App from '@/App';
import { render, screen, waitFor } from '../utils/testHelpers';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockCompletedGameState 
} from '../fixtures/gameState';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';
import { createMockGameStore } from '../fixtures/mocks';
import { useGameStore } from '@/store/gameStore';

describe('App Component', () => {
  let mockStore: ReturnType<typeof createMockGameStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStore = createMockGameStore();
    (useGameStore as any).mockReturnValue(mockStore);
  });

  describe('Rendering Structure', () => {
    it('renders main app structure correctly', () => {
      render(<App />);

      expect(screen.getByText('CORRIDORS')).toBeInTheDocument();
      expect(screen.getByTestId('connection-status')).toBeInTheDocument();
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
      expect(screen.getByText('© 2024 Corridors MCTS - Retro Gaming Edition')).toBeInTheDocument();
    });

    it('shows game setup when no game ID exists', () => {
      mockStore.gameId = null;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      expect(screen.getByTestId('game-setup')).toBeInTheDocument();
      expect(screen.queryByTestId('game-container')).not.toBeInTheDocument();
    });

    it('shows game container when game ID exists', () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockInitialGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.queryByTestId('game-setup')).not.toBeInTheDocument();
    });
  });

  describe('Connection Status Display', () => {
    it('shows connected status when connected', () => {
      mockStore.isConnected = true;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      const indicator = screen.getByTestId('connection-indicator');
      const text = screen.getByTestId('connection-text');

      expect(indicator).toHaveClass('connected');
      expect(text).toHaveTextContent('Connected');
    });

    it('shows disconnected status when not connected', () => {
      mockStore.isConnected = false;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      const indicator = screen.getByTestId('connection-indicator');
      const text = screen.getByTestId('connection-text');

      expect(indicator).toHaveClass('disconnected');
      expect(text).toHaveTextContent('Disconnected');
    });
  });

  describe('Game Info Panel', () => {
    beforeEach(() => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockMidGameState;
      mockStore.gameSettings = mockDefaultGameSettings;
      (useGameStore as any).mockReturnValue(mockStore);
    });

    it('displays game mode correctly', () => {
      render(<App />);

      expect(screen.getByText('human vs ai')).toBeInTheDocument();
    });

    it('displays AI settings for AI games', () => {
      render(<App />);

      expect(screen.getByText('medium')).toBeInTheDocument();
      expect(screen.getByText('5s')).toBeInTheDocument();
    });

    it('hides AI settings for human vs human games', () => {
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_human'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      expect(screen.queryByText('AI Level:')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time:')).not.toBeInTheDocument();
    });

    it('displays board size correctly', () => {
      render(<App />);

      expect(screen.getByText('9x9')).toBeInTheDocument();
    });

    it('displays truncated game ID', () => {
      render(<App />);

      expect(screen.getByText('test-gam')).toBeInTheDocument();
    });
  });

  describe('Game Controls', () => {
    beforeEach(() => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockMidGameState;
      (useGameStore as any).mockReturnValue(mockStore);
    });

    it('renders New Game button', async () => {
      const { user } = render(<App />);

      const newGameButton = screen.getByText('New Game');
      expect(newGameButton).toBeInTheDocument();

      await user.click(newGameButton);

      expect(mockStore.reset).toHaveBeenCalled();
    });

    it('renders Copy Moves button and handles clipboard operation', async () => {
      // Mock clipboard API
      const mockWriteText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText
        }
      });

      const { user } = render(<App />);

      const copyButton = screen.getByText('Copy Moves');
      expect(copyButton).toBeInTheDocument();

      await user.click(copyButton);

      expect(mockWriteText).toHaveBeenCalledWith('e2 e8 e3 c5h e7 g6v');
      expect(mockToast.success).toHaveBeenCalledWith(
        'Moves copied to clipboard!',
        expect.objectContaining({
          style: expect.objectContaining({
            background: '#00ff00',
            color: '#000000'
          })
        })
      );
    });

    it('handles clipboard failure gracefully', async () => {
      // Mock clipboard API to fail
      const mockWriteText = vi.fn().mockRejectedValue(new Error('Clipboard access denied'));
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText
        }
      });

      const { user } = render(<App />);

      const copyButton = screen.getByText('Copy Moves');
      await user.click(copyButton);

      expect(mockWriteText).toHaveBeenCalled();
      // Component should not crash on clipboard failure
    });

    it('does not copy moves when no game state exists', async () => {
      mockStore.gameState = null;
      (useGameStore as any).mockReturnValue(mockStore);

      const mockWriteText = vi.fn();
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText
        }
      });

      const { user } = render(<App />);

      const copyButton = screen.getByText('Copy Moves');
      await user.click(copyButton);

      expect(mockWriteText).not.toHaveBeenCalled();
    });
  });

  describe('WebSocket Connection Management', () => {
    it('connects to WebSocket on mount', () => {
      render(<App />);

      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('disconnects from WebSocket on unmount', () => {
      const { unmount } = render(<App />);

      unmount();

      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('displays error toast when error exists in store', async () => {
      mockStore.error = 'Connection failed';
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith(
          'Connection failed',
          expect.objectContaining({
            duration: 4000,
            style: expect.objectContaining({
              background: '#ff4444',
              color: '#ffffff'
            })
          })
        );
      });

      expect(mockStore.setError).toHaveBeenCalledWith(null);
    });

    it('does not show toast when no error exists', () => {
      mockStore.error = null;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      expect(mockToast.error).not.toHaveBeenCalled();
    });
  });

  describe('AI Move Automation', () => {
    it('triggers AI move for AI vs AI games', async () => {
      vi.useFakeTimers();
      
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      vi.advanceTimersByTime(1000);

      await waitFor(() => {
        expect(mockWebSocketService.getAIMove).toHaveBeenCalledWith('test-game-123');
      });

      vi.useRealTimers();
    });

    it('triggers AI move for human vs AI when AI turn', async () => {
      vi.useFakeTimers();
      
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = { ...mockInitialGameState, current_player: 1 };
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_ai'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      vi.advanceTimersByTime(500);

      await waitFor(() => {
        expect(mockWebSocketService.getAIMove).toHaveBeenCalledWith('test-game-123');
      });

      vi.useRealTimers();
    });

    it('does not trigger AI move for human vs AI when human turn', async () => {
      vi.useFakeTimers();
      
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_ai'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      vi.advanceTimersByTime(1000);

      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('does not trigger AI move when game is over', async () => {
      vi.useFakeTimers();
      
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockCompletedGameState;
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      vi.advanceTimersByTime(1000);

      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });

  describe('Component Integration', () => {
    it('renders all child components when game is active', () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockMidGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      // These components are mocked, but we can verify they're rendered
      // by checking for elements that would only exist if they're present
      expect(screen.getByText('New Game')).toBeInTheDocument();
      expect(screen.getByText('Copy Moves')).toBeInTheDocument();
    });
  });

  describe('Performance and Memory', () => {
    it('does not create memory leaks with timers', () => {
      vi.useFakeTimers();
      
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      const { unmount } = render(<App />);

      // Unmount component before timer fires
      unmount();
      
      vi.advanceTimersByTime(1000);

      // AI move should not be called after unmount
      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('cleans up timers when game state changes', () => {
      vi.useFakeTimers();
      
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      (useGameStore as any).mockReturnValue(mockStore);

      const { rerender } = render(<App />);

      // Change game state to completed
      mockStore.gameState = mockCompletedGameState;
      (useGameStore as any).mockReturnValue(mockStore);
      rerender(<App />);

      vi.advanceTimersByTime(1000);

      // Should not trigger AI move for completed game
      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });

  describe('Accessibility', () => {
    it('provides proper semantic structure', () => {
      render(<App />);

      expect(screen.getByRole('banner')).toBeInTheDocument(); // header
      expect(screen.getByRole('main')).toBeInTheDocument();   // main
      expect(screen.getByRole('contentinfo')).toBeInTheDocument(); // footer
    });

    it('provides proper button accessibility', () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockMidGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<App />);

      const newGameButton = screen.getByRole('button', { name: /new game/i });
      const copyButton = screen.getByRole('button', { name: /copy moves/i });

      expect(newGameButton).toBeInTheDocument();
      expect(copyButton).toBeInTheDocument();
    });
  });
});