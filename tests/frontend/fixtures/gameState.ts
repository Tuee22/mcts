// Game state fixtures for frontend testing
// These are focused on frontend rendering concerns, not backend logic

export interface Player {
  x: number;
  y: number;
}

export interface Wall {
  x: number;
  y: number;
  orientation: 'horizontal' | 'vertical';
}

export interface MoveHistoryEntry {
  notation: string;
  player: 0 | 1;
  type: 'move' | 'wall';
  position?: { x: number; y: number };
  wall?: Wall;
  board_state?: GameState;
}

export interface GameState {
  board_size: number;
  current_player: 0 | 1;
  players: Player[];
  walls: Wall[];
  walls_remaining: [number, number];
  legal_moves: string[];
  winner: number | null;
  move_history: MoveHistoryEntry[];
}

// Basic 9x9 game state at start
export const mockInitialGameState: GameState = {
  board_size: 9,
  current_player: 0,
  players: [
    { x: 4, y: 0 }, // Player 1 at bottom
    { x: 4, y: 8 }  // Player 2 at top
  ],
  walls: [],
  walls_remaining: [10, 10],
  legal_moves: ['e2'], // Player can move forward
  winner: null,
  move_history: []
};

// Game state with some moves played
export const mockMidGameState: GameState = {
  board_size: 9,
  current_player: 1,
  players: [
    { x: 4, y: 2 }, // Player 1 moved up
    { x: 4, y: 6 }  // Player 2 moved down
  ],
  walls: [
    { x: 2, y: 4, orientation: 'horizontal' },
    { x: 6, y: 5, orientation: 'vertical' }
  ],
  walls_remaining: [9, 9],
  legal_moves: ['e6', 'd7', 'f7', 'e7-wall-h', 'e7-wall-v'],
  winner: null,
  move_history: [
    {
      notation: 'e2',
      player: 0,
      type: 'move',
      position: { x: 4, y: 1 }
    },
    {
      notation: 'e8',
      player: 1,
      type: 'move', 
      position: { x: 4, y: 7 }
    },
    {
      notation: 'e3',
      player: 0,
      type: 'move',
      position: { x: 4, y: 2 }
    },
    {
      notation: 'c5h',
      player: 1,
      type: 'wall',
      wall: { x: 2, y: 4, orientation: 'horizontal' }
    },
    {
      notation: 'e7',
      player: 1,
      type: 'move',
      position: { x: 4, y: 6 }
    },
    {
      notation: 'g6v',
      player: 0,
      type: 'wall',
      wall: { x: 6, y: 5, orientation: 'vertical' }
    }
  ]
};

// Game state with winner determined
export const mockCompletedGameState: GameState = {
  board_size: 9,
  current_player: 0,
  players: [
    { x: 4, y: 8 }, // Player 1 reached the top - wins!
    { x: 4, y: 4 }  // Player 2 in middle
  ],
  walls: [
    { x: 1, y: 2, orientation: 'horizontal' },
    { x: 7, y: 6, orientation: 'vertical' },
    { x: 3, y: 3, orientation: 'horizontal' }
  ],
  walls_remaining: [8, 7],
  legal_moves: [], // Game over, no legal moves
  winner: 0,
  move_history: [
    // Shortened for readability - just show final winning move
    {
      notation: 'e9',
      player: 0,
      type: 'move',
      position: { x: 4, y: 8 }
    }
  ]
};

// State with no legal moves (edge case)
export const mockStalemateGameState: GameState = {
  ...mockMidGameState,
  legal_moves: [],
  current_player: 0
};

// State with many walls (rendering stress test)
export const mockWallHeavyGameState: GameState = {
  board_size: 9,
  current_player: 1,
  players: [
    { x: 1, y: 1 },
    { x: 7, y: 7 }
  ],
  walls: [
    { x: 0, y: 0, orientation: 'horizontal' },
    { x: 1, y: 0, orientation: 'horizontal' },
    { x: 2, y: 1, orientation: 'vertical' },
    { x: 3, y: 2, orientation: 'horizontal' },
    { x: 4, y: 3, orientation: 'vertical' },
    { x: 5, y: 4, orientation: 'horizontal' },
    { x: 6, y: 5, orientation: 'vertical' },
    { x: 7, y: 6, orientation: 'horizontal' },
    { x: 0, y: 7, orientation: 'vertical' }
  ],
  walls_remaining: [1, 1],
  legal_moves: ['a2', 'b1'],
  winner: null,
  move_history: []
};

// Long game history (performance test)
export const mockLongGameHistory: MoveHistoryEntry[] = Array.from({ length: 100 }, (_, i) => ({
  notation: `move${i + 1}`,
  player: (i % 2) as 0 | 1,
  type: 'move' as const,
  position: { x: i % 9, y: Math.floor(i / 9) % 9 }
}));

export const mockLongHistoryGameState: GameState = {
  ...mockMidGameState,
  move_history: mockLongGameHistory
};

// Different board sizes for testing responsiveness
export const mockSmallBoardState: GameState = {
  board_size: 5,
  current_player: 0,
  players: [
    { x: 2, y: 0 },
    { x: 2, y: 4 }
  ],
  walls: [],
  walls_remaining: [5, 5],
  legal_moves: ['c2'],
  winner: null,
  move_history: []
};

export const mockLargeBoardState: GameState = {
  board_size: 13,
  current_player: 1,
  players: [
    { x: 6, y: 0 },
    { x: 6, y: 12 }
  ],
  walls: [],
  walls_remaining: [15, 15],
  legal_moves: ['g12'],
  winner: null,
  move_history: []
};

// Edge case: Invalid/corrupted state for error handling tests
export const mockInvalidGameState = {
  board_size: 0, // Invalid
  current_player: 2 as any, // Invalid player
  players: [], // No players
  walls: [
    { x: -1, y: -1, orientation: 'horizontal' } // Invalid position
  ],
  walls_remaining: [-1, -1] as [number, number], // Invalid counts
  legal_moves: [],
  winner: null,
  move_history: []
};