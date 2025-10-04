import React from 'react';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
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
    createGame: vi.fn(),
    isConnected: vi.fn(),
  }
}));

describe('E2E Test Alignment - Game Creation Flow', () => {
  let mockWebSocket: any;
  
  beforeEach(() => {
    vi.clearAllMocks();
    
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
    (wsService.createGame as any).mockResolvedValue({ gameId: 'test-game-123' });
    (wsService.isConnected as any).mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should enable Start Game button only when connected (E2E scenario reproduction)', async () => {
    const user = userEvent.setup();
    
    // Start with disconnected state
    (wsService.isConnected as any).mockReturnValue(false);
    
    render(<App />);

    // Wait for initial render
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toBeInTheDocument();
    });

    // Should initially show "Disconnected"
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

    // Settings should be visible (no game active)
    expect(screen.getByText('Game Settings')).toBeInTheDocument();

    // Start Game button should exist but be disabled
    const startButton = screen.getByTestId('start-game-button');
    expect(startButton).toBeDisabled();
    
    // Now simulate connection establishment
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    // Trigger connection event manually to simulate WebSocket connection
    const connectHandler = mockWebSocket.addEventListener.mock.calls.find(
      call => call[0] === 'open'
    )?.[1];
    
    if (connectHandler) {
      connectHandler(new Event('open'));
    }
    
    // Also manually dispatch to store to ensure connection state is updated
    // This simulates what the WebSocket service would do internally
    act(() => {
      useGameStore.getState().dispatch({ 
        type: 'CONNECTION_ESTABLISHED', 
        clientId: 'test-client-123' 
      });
    });

    // Wait for connection state to update
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    }, { timeout: 10000 });

    // Now Start Game button should be enabled
    await waitFor(() => {
      expect(startButton).toBeEnabled();
    }, { timeout: 5000 });

    // Test clicking the Start Game button
    await user.click(startButton);

    // Should call the WebSocket service
    expect(wsService.createGame).toHaveBeenCalled();
  });

  it('should handle connection timing like e2e tests expect', async () => {
    const user = userEvent.setup();
    
    render(<App />);

    // Initial state - disconnected
    expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
    
    // Simulate the WebSocket service connection process
    (wsService.isConnected as any).mockReturnValue(false);
    mockWebSocket.readyState = WebSocket.CONNECTING;
    
    // Start connection process
    const connectingHandler = mockWebSocket.addEventListener.mock.calls.find(
      call => call[0] === 'connecting' || call[0] === 'open'
    )?.[1];
    
    // Simulate connection established
    (wsService.isConnected as any).mockReturnValue(true);
    mockWebSocket.readyState = WebSocket.OPEN;
    
    const openHandler = mockWebSocket.addEventListener.mock.calls.find(
      call => call[0] === 'open'
    )?.[1];
    
    if (openHandler) {
      openHandler(new Event('open'));
    }

    // Also manually dispatch to store to ensure connection state is updated
    act(() => {
      useGameStore.getState().dispatch({ 
        type: 'CONNECTION_ESTABLISHED', 
        clientId: 'test-client-2' 
      });
    });

    // Connection text should update to Connected
    await waitFor(() => {
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    // Settings panel should be visible for human_vs_human mode selection
    expect(screen.getByText('Human vs Human')).toBeInTheDocument();

    // Select human vs human mode
    const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
    await user.click(humanVsHumanButton);

    // Board size selection (default 9, but test might use 5)
    const boardSize5Button = screen.queryByText('5x5');
    if (boardSize5Button) {
      await user.click(boardSize5Button);
    }

    // Start Game button should now be enabled
    const startButton = screen.getByTestId('start-game-button');
    await waitFor(() => {
      expect(startButton).toBeEnabled();
    });

    // This should match the e2e test flow exactly
    await user.click(startButton);
    expect(wsService.createGame).toHaveBeenCalled();
  });
});