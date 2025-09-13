import { useGameStore } from '../store/gameStore';
import { GameState, Position, Wall, Player } from '../types/game';

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

  connectToGame(gameId: string) {
    // Close existing connection
    if (this.socket) {
      this.socket.close();
    }

    // Connect to game-specific WebSocket endpoint
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/games/${gameId}/ws`;

    try {
      this.socket = new WebSocket(wsUrl);
      this.setupEventListeners();
    } catch (error) {
      useGameStore.getState().setError('Failed to connect to game');
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
            break;
          case 'game_created':
            // Handle game creation response
            if (data.game_id) {
              useGameStore.getState().setGameId(data.game_id);
              useGameStore.getState().setIsLoading(false);
            }
            break;
          case 'pong':
            // Handle ping/pong for keepalive
            break;
          case 'game_state':
            // Handle game state updates
            if (data.data) {
              const gameState = this.transformApiResponseToGameState(data.data);
              if (gameState) {
                useGameStore.getState().setGameState(gameState);
              }
            }
            break;
          case 'move':
            // Handle move updates
            if (data.data) {
              // Fetch updated game state after a move
              this.requestGameState(data.data.game_id);
            }
            break;
          case 'game_ended':
            // Handle game end
            if (data.data) {
              const gameState = this.transformApiResponseToGameState(data.data);
              if (gameState) {
                useGameStore.getState().setGameState(gameState);
              }
            }
            break;
          case 'player_connected':
          case 'player_disconnected':
            // Handle player connection changes
            break;
          // Add other message types as needed
          default:
            break;
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

  }

  private transformApiResponseToGameState(apiResponse: any, boardSize?: number): GameState | null {
    try {
      
      // Extract board size from response or use provided/default
      const board_size = apiResponse.board_size || boardSize || 9;
      
      // Convert current_turn to current_player (API uses 1-based, GameState uses 0-based)
      const current_player = ((apiResponse.current_turn || 1) - 1) as 0 | 1;
      
      // Parse player positions from board_display if available
      let players: Position[] = [];
      if (apiResponse.board_display) {
        players = this.parsePlayerPositionsFromBoard(apiResponse.board_display, board_size);
      } else {
        // Fallback to default starting positions
        const centerX = Math.floor(board_size / 2);
        players = [
          { x: centerX, y: board_size - 1 }, // Player 1 starting position (bottom center)
          { x: centerX, y: 0 }                // Player 2 starting position (top center)
        ];
      }
      
      // Extract walls remaining from player data
      const walls_remaining: [number, number] = [
        apiResponse.player1?.walls_remaining ?? 10,
        apiResponse.player2?.walls_remaining ?? 10
      ];
      
      // Extract winner (can be null for ongoing games)
      const winner = apiResponse.winner;
      
      // Parse walls from board_display if available
      const walls = apiResponse.board_display ? 
        this.parseWallsFromBoard(apiResponse.board_display, board_size) : [];
      
      // Use legal moves from API response if available
      const legal_moves = apiResponse.legal_moves || [];
      
      // Create basic move history from move count (simplified)
      const move_history = Array.from({ length: apiResponse.move_count || 0 }, (_, i) => ({
        player: (i % 2) as Player,
        notation: `m${i}`,
        type: 'move' as const
        // board_state is undefined (omitted) - would need full history from API
      }));
      
      const gameState: GameState = {
        board_size,
        current_player,
        players,
        walls,
        walls_remaining,
        legal_moves,
        winner,
        move_history
      };
      
      return gameState;
    } catch (error) {
      console.error('Error transforming API response to GameState:', error);
      return null;
    }
  }

  private parsePlayerPositionsFromBoard(boardDisplay: string, boardSize: number): Position[] {
    // This is a simplified parser - in a real implementation you'd parse the full board representation
    // For now, use heuristics to find player positions
    const lines = boardDisplay.split('\n');
    const players: Position[] = [];
    
    // Look for player markers (typically 'h' for human/player1, 'v' for opponent/player2)
    for (let y = 0; y < lines.length && y < boardSize; y++) {
      const line = lines[y] || '';
      for (let x = 0; x < line.length && x < boardSize; x++) {
        const char = line[x];
        if (char === 'h' || char === '1') {
          players[0] = { x, y };
        } else if (char === 'v' || char === '2') {
          players[1] = { x, y };
        }
      }
    }
    
    // If positions not found, use defaults
    if (players.length < 2) {
      const centerX = Math.floor(boardSize / 2);
      return [
        players[0] || { x: centerX, y: boardSize - 1 },
        players[1] || { x: centerX, y: 0 }
      ];
    }
    
    return players;
  }

  private parseWallsFromBoard(boardDisplay: string, boardSize: number): Wall[] {
    // Simplified wall parser - would need more sophisticated parsing in real implementation
    return []; // For now, return empty array
  }

  async createGame(settings: any) {
    try {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        useGameStore.getState().setError('Not connected to server');
        return;
      }

      useGameStore.getState().setIsLoading(true);
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
      
      // First try to get game state via REST API immediately
      await this.requestGameState(gameData.game_id);
      
      // Connect to game-specific WebSocket for real-time updates
      this.connectToGame(gameData.game_id);
      
      // Give WebSocket time to connect and send initial game state
      await new Promise(resolve => setTimeout(resolve, 1000));
      
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

  async makeMove(gameId: string, move: string) {
    try {
      const response = await fetch(`/games/${gameId}/moves`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: move,
          player_id: 'player1' // For now, assuming player1 - would need proper player tracking
        })
      });

      if (!response.ok) {
        throw new Error(`Move failed: ${response.statusText}`);
      }

      const moveResult = await response.json();
      
      // After successful move, fetch updated game state
      await this.requestGameState(gameId);
      
    } catch (error) {
      useGameStore.getState().setError(`Failed to make move: ${error}`);
    }
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

  async requestGameState(gameId: string) {
    try {
      // Fetch both game state and legal moves
      const [gameResponse, legalMovesResponse] = await Promise.all([
        fetch(`/games/${gameId}`),
        fetch(`/games/${gameId}/legal-moves`)
      ]);

      if (gameResponse.ok) {
        const gameData = await gameResponse.json();
        
        // Add legal moves if available
        if (legalMovesResponse.ok) {
          const legalMovesData = await legalMovesResponse.json();
          gameData.legal_moves = legalMovesData.legal_moves || [];
        } else {
          gameData.legal_moves = [];
        }

        const gameState = this.transformApiResponseToGameState(gameData);
        if (gameState) {
          useGameStore.getState().setGameState(gameState);
        }
      }
    } catch (error) {
      console.error('Error fetching game state:', error);
    }
  }
}

export const wsService = new WebSocketService();