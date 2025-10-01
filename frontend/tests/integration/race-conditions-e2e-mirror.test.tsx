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

describe('Race Conditions E2E Mirror Tests', () => {
  let mockWebSocket: any;
  
  beforeEach(() => {
    vi.useFakeTimers();
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
    vi.useRealTimers();
    cleanup();
  });

  it('mirrors e2e simultaneous new game and settings clicks race condition', async () => {
    const user = userEvent.setup();
    
    // Start connected with no game initially (settings panel visible)
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    // Simulate connected state
    act(() => {
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-1'
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    // Create a game first
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);

    // Simulate game created
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

    await waitFor(() => {
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
    });

    // Now test the race condition: rapid New Game click
    const newGameButton = screen.getByText('New Game');
    
    // Simulate rapid clicking (the key race condition from e2e tests)
    await act(async () => {
      await user.click(newGameButton);
      // Immediately try to access settings (race condition scenario)
      const settingsButton = screen.queryByTestId('settings-toggle-button');
      if (settingsButton) {
        await user.click(settingsButton);
      }
    });

    // Should remain connected and functional after race condition
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    // Should be back at game setup and settings should be accessible
    expect(screen.getByTestId('game-setup')).toBeInTheDocument();
    expect(screen.getByText('Game Settings')).toBeInTheDocument();
    
    console.log('✅ Race condition between New Game and Settings handled correctly');
  });

  it('mirrors e2e rapid start game clicks behavior', async () => {
    const user = userEvent.setup();
    
    // Start connected with no game (settings panel visible)
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    act(() => {
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-1'
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    // Should show settings panel (no game active)
    await waitFor(() => {
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    const startButton = screen.getByTestId('start-game-button');
    expect(startButton).toBeEnabled();

    // Simulate rapid fire clicking on Start Game (5 clicks like e2e test)
    const clickPromises: Promise<void>[] = [];
    for (let i = 0; i < 5; i++) {
      clickPromises.push(user.click(startButton));
    }

    // Wait for all clicks to complete
    await act(async () => {
      await Promise.all(clickPromises);
    });

    // Should handle multiple clicks gracefully - only create one game
    expect(wsService.createGame).toHaveBeenCalledTimes(1);
    
    console.log('✅ Rapid Start Game clicking handled correctly');
  });

  it('mirrors e2e WebSocket reconnection during new game scenario', async () => {
    const user = userEvent.setup();
    
    // Start connected with existing game
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    act(() => {
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-1'
      });
    });

    // Create initial game
    act(() => {
      useGameStore.getState().dispatch({
        type: 'GAME_CREATED',
        gameId: 'initial-game-123',
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

    await waitFor(() => {
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
    });

    // Simulate WebSocket disconnection like e2e test
    act(() => {
      (wsService.isConnected as any).mockReturnValue(false);
      mockWebSocket.readyState = WebSocket.CLOSED;
      useGameStore.getState().dispatch({
        type: 'CONNECTION_LOST'
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });

    // Click New Game during reconnection (like e2e test)
    const newGameButton = screen.getByText('New Game');
    await user.click(newGameButton);

    // Simulate connection recovery
    act(() => {
      (wsService.isConnected as any).mockReturnValue(true);
      mockWebSocket.readyState = WebSocket.OPEN;
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-2'
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    // Should be back at game setup and functional
    expect(screen.getByTestId('game-setup')).toBeInTheDocument();
    
    console.log('✅ WebSocket reconnection during New Game handled correctly');
  });

  it('mirrors e2e component state transitions during rapid changes', async () => {
    const user = userEvent.setup();
    
    (wsService.isConnected as any).mockReturnValue(true);
    render(<App />);
    
    // Rapid connection state changes
    const states = [
      { type: 'CONNECTION_ESTABLISHED' as const, clientId: 'client-1' },
      { type: 'CONNECTION_LOST' as const },
      { type: 'CONNECTION_ESTABLISHED' as const, clientId: 'client-2' },
    ];

    for (const state of states) {
      act(() => {
        useGameStore.getState().dispatch(state);
      });
      await vi.advanceTimersByTimeAsync(50);
    }

    // Should stabilize in connected state
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    // Settings should be accessible after rapid changes
    expect(
      screen.getByText('Game Settings') || screen.queryByTestId('settings-toggle-button')
    ).toBeTruthy();

    console.log('✅ Rapid connection state changes handled correctly');
  });

  it('mirrors e2e slow game creation network delay race condition', async () => {
    const user = userEvent.setup();
    
    (wsService.isConnected as any).mockReturnValue(true);
    render(<App />);
    
    act(() => {
      useGameStore.getState().dispatch({
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-1'
      });
    });

    await waitFor(() => {
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    // Mock slow game creation (2 second delay like e2e test)
    (wsService.createGame as any).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ gameId: 'slow-game' }), 2000))
    );

    const startButton = screen.getByTestId('start-game-button');
    
    // Click start game
    await user.click(startButton);

    // Should show loading state
    expect(startButton).toHaveTextContent('Starting...');

    // Simulate clicking settings during game creation (race condition)
    const settingsButton = screen.queryByTestId('settings-toggle-button');
    if (settingsButton) {
      await user.click(settingsButton);
    }

    // Advance timers to complete game creation
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2500);
    });

    // Should handle race condition gracefully
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    
    console.log('✅ Slow game creation race condition handled correctly');
  });
});