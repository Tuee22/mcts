import { useGameStore } from '../store/gameStore';

class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(url?: string) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    // Use relative WebSocket URL for single-server architecture
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = url || `${protocol}//${window.location.host}/ws`;

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
            // Connection confirmed from server
            useGameStore.getState().setIsConnected(true);
            useGameStore.getState().setError(null);
            console.log('WebSocket connection confirmed by server');
            break;
          case 'game_created':
            // Handle game creation response
            if (data.game_id) {
              useGameStore.getState().setGameId(data.game_id);
              useGameStore.getState().setIsLoading(false);
              console.log('Game created:', data.game_id);
            }
            break;
          case 'pong':
            // Handle ping/pong for keepalive
            console.log('WebSocket pong received');
            break;
          // Add other message types as needed
          default:
            console.log('Unknown WebSocket message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

  }

  async createGame(settings: any) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().setError('Not connected to server');
      return;
    }

    useGameStore.getState().setIsLoading(true);

    try {
      // Convert frontend game settings to backend format
      const gameRequest = {
        player1_type: 'human',
        player2_type: settings.mode === 'human_vs_human' ? 'human' : 'machine',
        player1_name: 'Player 1',
        player2_name: settings.mode === 'human_vs_human' ? 'Player 2' : 'AI',
        settings: {
          board_size: settings.board_size,
          ai_config: settings.ai_config
        }
      };

      // Create game via REST API
      const response = await fetch('/games', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(gameRequest)
      });

      if (!response.ok) {
        throw new Error(`Failed to create game: ${response.statusText}`);
      }

      const gameData = await response.json();
      useGameStore.getState().setGameId(gameData.game_id);
      useGameStore.getState().setGameState(gameData.state);
      useGameStore.getState().setIsLoading(false);
      
    } catch (error) {
      console.error('Error creating game:', error);
      useGameStore.getState().setError(`Failed to create game: ${error}`);
      useGameStore.getState().setIsLoading(false);
    }
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