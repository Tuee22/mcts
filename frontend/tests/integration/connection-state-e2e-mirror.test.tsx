import React from 'react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
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

describe('Connection State Tests Mirroring E2E Scenarios', () => {
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

  it('mirrors e2e connection stability during rapid UI transitions', async () => {
    const user = userEvent.setup();
    
    // Start with disconnected state (like e2e test)
    (wsService.isConnected as any).mockReturnValue(false);
    
    render(<App />);
    
    // Initial state should be disconnected
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });

    // Settings should be visible (no game active)
    expect(screen.getByText('Game Settings')).toBeInTheDocument();
    
    // Start Game button should be disabled when disconnected
    const startButton = screen.getByTestId('start-game-button');
    expect(startButton).toBeDisabled();
    
    // Simulate connection establishment (mirrors e2e WebSocket connection)
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    // Trigger store state update for connection
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'test-client-123' 
    });
    
    // Connection text should update
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Start Game button should now be enabled
    await waitFor(() => {
      expect(startButton).toBeEnabled();
    });
    
    // Test rapid game creation (mirrors e2e New Game click sequence)
    await user.click(startButton);
    expect(wsService.createGame).toHaveBeenCalled();
    
    // Simulate game creation success
    useGameStore.getState().dispatch({
      type: 'GAME_CREATED',
      gameId: 'test-game-123',
      state: {
        gameId: 'test-game-123',
        status: 'in_progress',
        current_turn: 1,
        move_history: [],
        player1_position: [4, 0],
        player2_position: [4, 8],
        walls: [],
        player1_walls: 10,
        player2_walls: 10,
        winner: null,
        board_size: 9
      }
    });
    
    // Game container should appear
    await waitFor(() => {
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
    });
    
    // This mirrors the e2e test's critical check: Settings button should be available
    // and functional after game creation
    const settingsButton = screen.getByRole('button', { name: /game settings/i });
    expect(settingsButton).toBeEnabled();
    
    // Test rapid New Game click (mirrors e2e scenario that was failing)
    const newGameButton = screen.getByRole('button', { name: /new game/i });
    await user.click(newGameButton);
    
    // Should transition through game-ending state
    expect(useGameStore.getState().session.type).toBe('game-ending');
    
    // Complete the transition
    useGameStore.getState().dispatch({ type: 'GAME_ENDING_COMPLETE' });
    
    // Should be back to no-game state with settings visible
    await waitFor(() => {
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });
    
    // Connection should remain stable throughout
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    
    // Start Game button should still work
    const newStartButton = screen.getByTestId('start-game-button');
    expect(newStartButton).toBeEnabled();
  });

  it('mirrors e2e multi-instance connection behavior', async () => {
    const user = userEvent.setup();
    
    // Simulate first "browser tab" connecting
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    // Establish connection
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'client-tab-1' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Create a game
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);
    
    // Simulate successful game creation
    useGameStore.getState().dispatch({
      type: 'GAME_CREATED',
      gameId: 'multi-tab-game',
      state: {
        gameId: 'multi-tab-game',
        status: 'in_progress',
        current_turn: 1,
        move_history: [],
        player1_position: [4, 0],
        player2_position: [4, 8],
        walls: [],
        player1_walls: 10,
        player2_walls: 10,
        winner: null,
        board_size: 9
      }
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
    });
    
    // Simulate connection conflict (what happens in multi-tab scenario)
    // This would normally cause the connection to be lost and re-established
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_LOST', 
      error: 'Connection conflict detected' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });
    
    // Game should still be visible but settings button should be disabled
    expect(screen.getByTestId('game-container')).toBeInTheDocument();
    const settingsButton = screen.getByRole('button', { name: /game settings/i });
    expect(settingsButton).toBeDisabled();
    
    // Simulate reconnection
    useGameStore.getState().dispatch({ type: 'CONNECTION_RETRY' });
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'client-tab-1-reconnected' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Settings button should be enabled again
    expect(settingsButton).toBeEnabled();
    
    // New Game should work after reconnection
    const newGameButton = screen.getByRole('button', { name: /new game/i });
    expect(newGameButton).toBeEnabled();
  });

  it('mirrors e2e Settings button timeout scenarios', async () => {
    const user = userEvent.setup();
    
    // Start connected
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'timeout-test-client' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Create game rapidly (mirrors e2e rapid game creation)
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);
    
    // Don't immediately complete game creation - simulate delay
    useGameStore.getState().dispatch({ type: 'START_GAME' });
    
    // Store should be in creating-game state
    expect(useGameStore.getState().session.type).toBe('creating-game');
    
    // Settings should show loading state
    expect(screen.getByTestId('start-game-button')).toBeDisabled();
    
    // Simulate the timeout scenario that was causing e2e failures
    // Complete game creation immediately
    useGameStore.getState().dispatch({
      type: 'GAME_CREATED',
      gameId: 'timeout-test-game',
      state: {
        gameId: 'timeout-test-game',
        status: 'in_progress',
        current_turn: 1,
        move_history: [],
        player1_position: [4, 0],
        player2_position: [4, 8],
        walls: [],
        player1_walls: 10,
        player2_walls: 10,
        winner: null,
        board_size: 9
      }
    });
    
    // After game creation completes, settings button should become available
    await waitFor(() => {
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
    }, { timeout: 5000 });
    
    // In active game state, settings should be accessible via button
    const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
    expect(settingsButton).toBeEnabled();
    
    // This mirrors the specific e2e test expectation
    expect(screen.getByTestId('game-container')).toBeInTheDocument();
  });

  it('mirrors e2e session state consistency across rapid operations', async () => {
    const user = userEvent.setup();
    
    // Establish connection
    (wsService.isConnected as any).mockReturnValue(true);
    render(<App />);
    
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'consistency-test' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Perform rapid operations that mirror e2e test sequence
    const operations = [
      () => user.click(screen.getByTestId('start-game-button')),
      () => useGameStore.getState().dispatch({
        type: 'GAME_CREATED',
        gameId: 'rapid-op-game',
        state: {
          gameId: 'rapid-op-game',
          status: 'in_progress',
          current_turn: 1,
          move_history: [],
          player1_position: [4, 0],
          player2_position: [4, 8],
          walls: [],
          player1_walls: 10,
          player2_walls: 10,
          winner: null,
          board_size: 9
        }
      }),
      () => user.click(screen.getByRole('button', { name: /new game/i })),
      () => useGameStore.getState().dispatch({ type: 'GAME_ENDING_COMPLETE' }),
    ];
    
    // Execute operations rapidly
    for (const operation of operations) {
      await operation();
      // Small delay to allow React to process
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    
    // Final state should be consistent
    await waitFor(() => {
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });
    
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    expect(screen.getByTestId('start-game-button')).toBeEnabled();
    
    // Store state should be consistent
    const finalState = useGameStore.getState();
    expect(finalState.connection.type).toBe('connected');
    expect(finalState.session.type).toBe('no-game');
  });

  it('handles connection state validation like e2e expects', async () => {
    // This test mirrors the e2e expectations about connection state validation
    render(<App />);
    
    // Start disconnected
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    
    // Attempt to start game while disconnected should be prevented
    const startButton = screen.getByTestId('start-game-button');
    expect(startButton).toBeDisabled();
    
    // Connect
    (wsService.isConnected as any).mockReturnValue(true);
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'validation-test' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      expect(startButton).toBeEnabled();
    });
    
    // Test that connection state changes are reflected immediately
    useGameStore.getState().dispatch({ type: 'CONNECTION_LOST' });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });
    
    // All interactive elements should be disabled when disconnected
    expect(screen.getByTestId('start-game-button')).toBeDisabled();
  });
});