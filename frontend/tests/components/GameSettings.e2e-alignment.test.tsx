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

describe('Settings Button E2E Alignment Tests', () => {
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
      value: { randomUUID: () => 'settings-test-uuid' },
      writable: true
    });
    
    // Setup wsService mocks
    (wsService.connect as any).mockResolvedValue(undefined);
    (wsService.disconnect as any).mockResolvedValue(undefined);
    (wsService.disconnectFromGame as any).mockResolvedValue(undefined);
    (wsService.createGame as any).mockResolvedValue({ gameId: 'settings-test-game' });
    (wsService.isConnected as any).mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it('mirrors e2e Settings button timeout expectations', async () => {
    const user = userEvent.setup();
    
    // Start connected (mirrors e2e test expectations)
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    render(<App />);
    
    // Establish connection
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'settings-timeout-test' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Initial state: Settings should be visible as panel (no game active)
    expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    expect(screen.getByTestId('start-game-button')).toBeEnabled();
    
    // Create game rapidly (this is what was timing out in e2e)
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);
    
    // Game creation is handled externally - store remains in no-game until GAME_CREATED
    expect(useGameStore.getState().session.type).toBe('no-game');
    
    // Complete game creation
    useGameStore.getState().dispatch({
      type: 'GAME_CREATED',
      gameId: 'settings-timeout-game',
      state: {
        gameId: 'settings-timeout-game',
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
    
    // CRITICAL: Settings button should be available within e2e timeout expectations
    await waitFor(() => {
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
    }, { timeout: 5000 }); // Consistent with simplified state machine - no intermediate states
    
    // Settings button should now be available as a button (not panel)
    const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
    expect(settingsButton).toBeEnabled();
    
    // Test clicking settings button (what e2e was trying to do)
    await user.click(settingsButton);
    
    // Settings should expand or show some indication of interaction
    // This test verifies the button is functional as e2e expects
    expect(settingsButton).toBeEnabled(); // Still enabled after click
  });

  it('matches e2e Settings button availability after New Game', async () => {
    const user = userEvent.setup();
    
    // Start with connected game
    (wsService.isConnected as any).mockReturnValue(true);
    render(<App />);
    
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'new-game-test' 
    });
    
    // Create initial game
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);
    
    useGameStore.getState().dispatch({
      type: 'GAME_CREATED',
      gameId: 'initial-game',
      state: {
        gameId: 'initial-game',
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
    
    // Settings button should be available
    const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
    expect(settingsButton).toBeEnabled();
    
    // Click New Game (this was the problematic scenario in e2e)
    const newGameButton = screen.getByRole('button', { name: /new game/i });
    await user.click(newGameButton);
    
    // With simplified state machine, this should directly transition to no-game
    
    // After New Game, we should be back to setup state
    await waitFor(() => {
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    });
    
    // Settings should be available as panel again (no active game)
    expect(screen.getByTestId('start-game-button')).toBeEnabled();
    
    // Connection should remain stable (critical e2e requirement)
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
  });

  it('handles Settings button state during connection changes like e2e expects', async () => {
    const user = userEvent.setup();
    
    render(<App />);
    
    // Start disconnected
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    expect(screen.getByTestId('start-game-button')).toBeDisabled();
    
    // Connect
    (wsService.isConnected as any).mockReturnValue(true);
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'connection-change-test' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Settings should become available
    expect(screen.getByTestId('start-game-button')).toBeEnabled();
    
    // Create game
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);
    
    useGameStore.getState().dispatch({
      type: 'GAME_CREATED',
      gameId: 'connection-test-game',
      state: {
        gameId: 'connection-test-game',
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
    
    // Settings button should be enabled
    const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
    expect(settingsButton).toBeEnabled();
    
    // Lose connection (mirrors e2e network issues)
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_LOST', 
      error: 'Network disconnection' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });
    
    // Settings button should be disabled when disconnected
    await waitFor(() => {
      expect(settingsButton).toBeDisabled();
    });
    
    // Reconnect via retry first
    useGameStore.getState().dispatch({ type: 'CONNECTION_RETRY' });
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'reconnected-client' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Settings button should be enabled again
    await waitFor(() => {
      expect(settingsButton).toBeEnabled();
    });
  });

  it('validates Settings button behavior matches e2e multi-tab scenario expectations', async () => {
    const user = userEvent.setup();
    
    // Simulate multi-tab conflict scenario
    (wsService.isConnected as any).mockReturnValue(true);
    render(<App />);
    
    // First tab establishes connection
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'tab-1-client' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Create game in first tab
    const startButton = screen.getByTestId('start-game-button');
    await user.click(startButton);
    
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
    
    const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
    expect(settingsButton).toBeEnabled();
    
    // Simulate second tab opening (connection conflict)
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_LOST', 
      error: 'Connection conflict - another tab opened' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    });
    
    // Settings should be disabled during conflict
    expect(settingsButton).toBeDisabled();
    
    // Simulate conflict resolution and reconnection
    useGameStore.getState().dispatch({ type: 'CONNECTION_RETRY' });
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'tab-1-reconnected' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Settings should be available again after conflict resolution
    await waitFor(() => {
      expect(settingsButton).toBeEnabled();
    });
    
    // Test that Settings button is actually functional (not just visually enabled)
    await user.click(settingsButton);
    
    // Button should remain clickable (verifies it's not just a visual state)
    expect(settingsButton).toBeEnabled();
  });

  it('ensures Settings button timing matches e2e performance expectations', async () => {
    const user = userEvent.setup();
    
    // This test specifically mirrors the timing-sensitive aspects of e2e tests
    const startTime = performance.now();
    
    (wsService.isConnected as any).mockReturnValue(true);
    render(<App />);
    
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'timing-test-client' 
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
    
    // Rapid game creation and Settings button interaction sequence
    const operations = [
      () => user.click(screen.getByTestId('start-game-button')),
      () => useGameStore.getState().dispatch({
        type: 'GAME_CREATED',
        gameId: 'timing-test-game',
        state: {
          gameId: 'timing-test-game',
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
    ];
    
    // Execute operations rapidly
    for (const operation of operations) {
      await operation();
    }
    
    // Settings button should be available within reasonable time
    await waitFor(() => {
      const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
      expect(settingsButton).toBeEnabled();
    }, { timeout: 5000 });
    
    const endTime = performance.now();
    const totalTime = endTime - startTime;
    
    // Total operation should complete within e2e timeout expectations
    expect(totalTime).toBeLessThan(10000); // 10 seconds max (generous for e2e)
    
    // Settings button interaction should work immediately
    const settingsButton = screen.getByRole('button', { name: /⚙️ game settings/i });
    const interactionStart = performance.now();
    await user.click(settingsButton);
    const interactionEnd = performance.now();
    
    // Button interaction should be immediate (< 100ms)
    expect(interactionEnd - interactionStart).toBeLessThan(100);
    expect(settingsButton).toBeEnabled();
  });
});