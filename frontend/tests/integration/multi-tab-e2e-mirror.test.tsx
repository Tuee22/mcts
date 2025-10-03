import React from 'react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '@/App';
import { wsService } from '@/services/websocket';
import { useGameStore } from '@/store/gameStore';

// Mock react-hot-toast
const mockToast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
}));

vi.mock('react-hot-toast', () => ({
  default: mockToast,
  toast: mockToast,
  Toaster: () => React.createElement('div', { 'data-testid': 'toaster' }),
}));

// Mock WebSocket service
vi.mock('@/services/websocket', () => ({
  wsService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    disconnectFromGame: vi.fn(),
    createGame: vi.fn(),
    isConnected: vi.fn(),
    subscribeToGameEvents: vi.fn(),
    unsubscribeFromGameEvents: vi.fn(),
  }
}));

describe('Multi-Tab E2E Mirror Tests', () => {
  let mockWebSocket: any;
  
  beforeEach(() => {
    vi.clearAllMocks();
    cleanup();
    
    // Clear store state
    useGameStore.getState().dispatch({ type: 'RESET_GAME' });
    
    // Mock WebSocket constructor
    mockWebSocket = {
      close: vi.fn(),
      send: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: WebSocket.CONNECTING,
    };
    
    global.WebSocket = vi.fn(() => mockWebSocket) as any;
    
    // Mock crypto.randomUUID
    Object.defineProperty(global, 'crypto', {
      value: { randomUUID: () => 'test-uuid-123' },
      writable: true
    });
    
    // Setup wsService mocks
    (wsService.connect as any).mockResolvedValue(undefined);
    (wsService.disconnect as any).mockResolvedValue(undefined);
    (wsService.disconnectFromGame as any).mockResolvedValue(undefined);
    (wsService.createGame as any).mockResolvedValue({ gameId: 'test-game-123' });
    (wsService.isConnected as any).mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it('mirrors e2e multi-tab settings button behavior', async () => {
    const user = userEvent.setup();
    
    // Start with disconnected state (like e2e test)
    (wsService.isConnected as any).mockReturnValue(false);
    
    render(<App />);
    
    // Initial state should be disconnected
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });

    // When disconnected with no game, settings should be visible as PANEL (not button)
    expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    expect(screen.queryByTestId('settings-toggle-button')).not.toBeInTheDocument();
    
    // Start Game button should be disabled when disconnected
    const startButton = screen.getByTestId('start-game-button');
    expect(startButton).toBeDisabled();
    
    // Simulate connection establishment
    act(() => {
      (wsService.isConnected as any).mockReturnValue(true);
      mockWebSocket.readyState = WebSocket.OPEN;
      
      // Trigger store state update for connection
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-1'
      });
    });
    
    // After connection with no game, should still show PANEL (not button)
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Settings should still be panel, not button (no game active)
    expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    expect(screen.queryByTestId('settings-toggle-button')).not.toBeInTheDocument();
    
    // Now Start Game button should be enabled
    expect(startButton).toBeEnabled();
    
    // Click start game to create a game
    await act(async () => {
      await user.click(startButton);
    });
    
    // Simulate game creation
    act(() => {
      useGameStore.getState().dispatch({
        type: 'GAME_CREATED',
        gameId: 'test-game-123',
        state: {
          status: 'active',
          current_player: 0,
          players: [
            { id: 'player-1', name: 'Human', position: { row: 8, col: 4 }, walls: 10 },
            { id: 'player-2', name: 'AI', position: { row: 0, col: 4 }, walls: 10 }
          ],
          board_size: 9,
          move_history: [],
          last_move: null,
          winner: null
        }
      });
    });
    
    // Now with game active, settings should appear as BUTTON
    await waitFor(() => {
      expect(screen.getByTestId('settings-toggle-button')).toBeInTheDocument();
    });
    
    expect(screen.queryByText('⚙️ Game Settings')).not.toBeInTheDocument(); // Panel should be hidden
    
    // This is the key test: when game is active, e2e tests expect the button
    const settingsButton = screen.getByTestId('settings-toggle-button');
    expect(settingsButton).toBeEnabled();
    
    // Click the settings button to expand settings
    await act(async () => {
      await user.click(settingsButton);
    });
    
    // After clicking button, panel should appear
    await waitFor(() => {
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    });
    
    console.log('✅ Multi-tab settings UI behavior correctly reproduced');
  });

  it('reproduces the exact multi-tab connection flow issue', async () => {
    // This test reproduces the exact scenario where e2e test fails
    
    // Tab 1: Connect
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    // Simulate connection established
    act(() => {
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'tab-1-client'
      });
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // At this point, no game is active, so settings should be PANEL
    // This is where the e2e test fails - it expects a button but gets a panel
    
    const settingsPanel = screen.queryByText('⚙️ Game Settings');
    const settingsButton = screen.queryByTestId('settings-toggle-button');
    
    // The e2e test assumes settings-toggle-button exists at this point, but it shouldn't
    expect(settingsPanel).toBeInTheDocument(); // Panel should exist
    expect(settingsButton).not.toBeInTheDocument(); // Button should NOT exist
    
    console.log('✅ Identified the exact disconnect between e2e expectations and functional reality');
  });
});