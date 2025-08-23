import { useGameStore } from '../store/gameStore';
import { GameState, Move } from '../types/game';

class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(url?: string) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    // Support environment variable for API URL
    const wsUrl = url || process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

    try {
      this.socket = new WebSocket(wsUrl);
      this.setupEventListeners();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      useGameStore.getState().setError('Failed to connect to server');
    }
  }

  private setupEventListeners() {
    if (!this.socket) return;

    this.socket.onopen = () => {
      useGameStore.getState().setIsConnected(true);
      useGameStore.getState().setError(null);
      this.reconnectAttempts = 0;
    };

    this.socket.onclose = () => {
      useGameStore.getState().setIsConnected(false);
    };

    this.socket.onerror = (error: any) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        useGameStore.getState().setIsConnected(false);
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle different message types
        switch (data.type) {
          case 'connect':
            // Connection confirmed
            break;
          case 'game_created':
            // Handle game creation
            break;
          // Add other message types as needed
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

  }

  createGame(settings: any) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    useGameStore.getState().setIsLoading(true);
    this.socket.send(JSON.stringify({
      type: 'create_game',
      data: settings
    }));
  }

  joinGame(gameId: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    useGameStore.getState().setIsLoading(true);
    this.socket.send(JSON.stringify({
      type: 'join_game',
      data: { game_id: gameId }
    }));
  }

  makeMove(gameId: string, move: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    this.socket.send(JSON.stringify({
      type: 'make_move',
      data: { game_id: gameId, move }
    }));
  }

  getAIMove(gameId: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    this.socket.send(JSON.stringify({
      type: 'get_ai_move',
      data: { game_id: gameId }
    }));
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN || false;
  }
}

export const wsService = new WebSocketService();