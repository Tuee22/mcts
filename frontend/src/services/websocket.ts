import io from 'socket.io-client';
import { useGameStore } from '../store/gameStore';
import { GameState, Move } from '../types/game';

class WebSocketService {
  private socket: any | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(url: string = 'http://localhost:8000') {
    if (this.socket?.connected) {
      return;
    }

    this.socket = io(url, {
      path: '/socket.io/',
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
    });

    this.setupEventListeners();
  }

  private setupEventListeners() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('Connected to server');
      useGameStore.getState().setIsConnected(true);
      useGameStore.getState().setError(null);
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from server');
      useGameStore.getState().setIsConnected(false);
    });

    this.socket.on('connect_error', (error: any) => {
      console.error('Connection error:', error);
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        useGameStore.getState().setError('Failed to connect to server. Please check if the server is running.');
      }
    });

    this.socket.on('game_created', (data: { game_id: string; state: GameState }) => {
      console.log('Game created:', data);
      useGameStore.getState().setGameId(data.game_id);
      useGameStore.getState().setGameState(data.state);
      useGameStore.getState().setIsLoading(false);
    });

    this.socket.on('game_state', (data: { state: GameState }) => {
      console.log('Game state updated:', data);
      useGameStore.getState().setGameState(data.state);
    });

    this.socket.on('move_made', (data: { move: Move; state: GameState }) => {
      console.log('Move made:', data);
      useGameStore.getState().setGameState(data.state);
      useGameStore.getState().addMoveToHistory(data.move);
    });

    this.socket.on('game_over', (data: { winner: number; state: GameState }) => {
      console.log('Game over:', data);
      useGameStore.getState().setGameState({
        ...data.state,
        winner: data.winner as 0 | 1
      });
    });

    this.socket.on('error', (data: { message: string }) => {
      console.error('Server error:', data);
      useGameStore.getState().setError(data.message);
      useGameStore.getState().setIsLoading(false);
    });
  }

  createGame(settings: any) {
    if (!this.socket?.connected) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    useGameStore.getState().setIsLoading(true);
    this.socket.emit('create_game', settings);
  }

  joinGame(gameId: string) {
    if (!this.socket?.connected) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    useGameStore.getState().setIsLoading(true);
    this.socket.emit('join_game', { game_id: gameId });
  }

  makeMove(gameId: string, move: string) {
    if (!this.socket?.connected) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    this.socket.emit('make_move', { game_id: gameId, move });
  }

  getAIMove(gameId: string) {
    if (!this.socket?.connected) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    this.socket.emit('get_ai_move', { game_id: gameId });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

export const wsService = new WebSocketService();