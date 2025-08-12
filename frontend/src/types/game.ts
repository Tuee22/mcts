export type Player = 0 | 1;

export interface Position {
  x: number;
  y: number;
}

export interface Wall {
  x: number;
  y: number;
  orientation: 'horizontal' | 'vertical';
}

export interface GameState {
  board_size: number;
  current_player: Player;
  players: Position[];
  walls: Wall[];
  walls_remaining: [number, number];
  legal_moves: string[];
  winner: Player | null;
  move_history: Move[];
}

export interface Move {
  notation: string;
  player: Player;
  type: 'move' | 'wall';
  position?: Position;
  wall?: Wall;
  board_state?: GameState;
}

export type GameMode = 'ai_vs_ai' | 'human_vs_ai' | 'human_vs_human';

export interface GameSettings {
  mode: GameMode;
  ai_difficulty: 'easy' | 'medium' | 'hard' | 'expert';
  ai_time_limit: number;
  board_size: number;
}