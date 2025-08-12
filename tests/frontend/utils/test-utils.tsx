import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock game state for testing
export const mockGameState = {
  board_size: 9,
  current_player: 0 as 0 | 1,
  players: [
    { x: 4, y: 0 },
    { x: 4, y: 8 }
  ],
  walls: [],
  walls_remaining: [10, 10] as [number, number],
  legal_moves: ['a1', 'a2', 'b1', 'e2'],
  winner: null,
  move_history: []
};

// Mock game state with walls
export const mockGameStateWithWalls = {
  ...mockGameState,
  walls: [
    { x: 2, y: 3, orientation: 'horizontal' as 'horizontal' | 'vertical' },
    { x: 5, y: 1, orientation: 'vertical' as 'horizontal' | 'vertical' }
  ],
  walls_remaining: [8, 10] as [number, number]
};

// Mock game state with move history
export const mockGameStateWithHistory = {
  ...mockGameState,
  move_history: [
    {
      notation: 'e2',
      player: 0 as 0 | 1,
      type: 'move' as 'move' | 'wall',
      position: { x: 4, y: 7 },
      board_state: mockGameState
    },
    {
      notation: 'e8',
      player: 1 as 0 | 1,
      type: 'move' as 'move' | 'wall',
      position: { x: 4, y: 1 },
      board_state: mockGameState
    }
  ]
};

// Mock completed game state
export const mockCompletedGameState = {
  ...mockGameState,
  winner: 0 as 0 | 1,
  current_player: 0 as 0 | 1
};

// Mock game settings
export const mockGameSettings = {
  mode: 'human_vs_ai' as const,
  ai_difficulty: 'medium' as const,
  ai_time_limit: 5000,
  board_size: 9
};

// Helper to create a user event instance
export const createUser = () => userEvent.setup();

// Helper to wait for async operations
export const waitFor = (callback: () => void, timeout = 1000) => {
  return new Promise<void>((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      try {
        callback();
        resolve();
      } catch (error) {
        if (Date.now() - start > timeout) {
          reject(error);
        } else {
          setTimeout(check, 10);
        }
      }
    };
    check();
  });
};

// Helper to mock WebSocket events
export const mockWebSocketEvent = (eventName: string, data: any) => {
  return act(() => {
    const event = new CustomEvent(eventName, { detail: data });
    window.dispatchEvent(event);
  });
};

// Custom render function with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  // Add any global providers here if needed
}

export const customRender = (
  ui: ReactElement,
  options?: CustomRenderOptions
) => {
  return render(ui, {
    ...options
  });
};

// Re-export everything from testing-library
export * from '@testing-library/react';
export { customRender as render };

// Test data generators
export const generateMockMove = (notation: string, player: 0 | 1, type: 'move' | 'wall' = 'move') => ({
  notation,
  player,
  type,
  position: type === 'move' ? { x: 0, y: 0 } : undefined,
  wall: type === 'wall' ? { x: 0, y: 0, orientation: 'horizontal' as const } : undefined,
  board_state: mockGameState
});

export const generateMockGameState = (overrides: any = {}) => ({
  ...mockGameState,
  ...overrides
});

// Mock localStorage
export const mockLocalStorage = () => {
  const store: { [key: string]: string } = {};
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    })
  };
};

// Mock clipboard
export const mockClipboard = {
  writeText: jest.fn(() => Promise.resolve()),
  readText: jest.fn(() => Promise.resolve(''))
};