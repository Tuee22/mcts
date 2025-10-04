import { useGameStore } from '../store/gameStore';
import { GameState, Position, Wall, Player } from '../types/game';

class WebSocketService {
  private socket: WebSocket | null = null;
  private gameSocket: WebSocket | null = null;
  private currentGameId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private shouldReconnect = true;
  private connectionMonitor: NodeJS.Timeout | null = null;
  private connectionMutex = false;

  connect(url?: string) {
    console.log('WebSocket connect called with URL:', url);

    // Prevent concurrent connection attempts
    if (this.connectionMutex) {
      console.log('Connection attempt blocked by mutex');
      return;
    }
    this.connectionMutex = true;

    this.shouldReconnect = true;
    
    // Start connection monitoring if not already running
    this.startConnectionMonitoring();

    // Close any existing connection first (including game-specific ones)
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      console.log('Closing existing socket');
      this.socket.close();
    }

    // Use provided URL or construct from window.location
    let wsUrl: string;
    if (url) {
      wsUrl = url;
      console.log('Using provided URL:', wsUrl);
    } else {
      // Use relative WebSocket URL for single-server architecture
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws`;
      console.log('Constructed URL from window.location:', wsUrl);
    }

    try {
      console.log('Creating WebSocket with URL:', wsUrl);
      this.socket = new WebSocket(wsUrl);
      console.log('WebSocket created successfully');
      this.setupEventListeners();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      // Only access useGameStore if it exists (for testing)
      if (typeof useGameStore !== 'undefined') {
        useGameStore.getState().dispatch({
          type: 'NOTIFICATION_ADDED',
          notification: {
            id: crypto.randomUUID(),
            type: 'error',
            message: 'Failed to connect to server',
            timestamp: new Date()
          }
        });
      }
    }
  }

  connectToGame(gameId: string) {
    // Close existing game connection if switching games
    if (this.gameSocket && this.gameSocket.readyState === WebSocket.OPEN) {
      this.gameSocket.close();
    }

    // Update current game ID
    this.currentGameId = gameId;

    // Create game-specific WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const gameWsUrl = `${protocol}//${window.location.host}/games/${gameId}/ws`;

    try {
      this.gameSocket = new WebSocket(gameWsUrl);
      this.setupGameEventListeners();
    } catch (error) {
      console.error('Game WebSocket connection error:', error);
      useGameStore.getState().dispatch({
        type: 'NOTIFICATION_ADDED',
        notification: {
          id: crypto.randomUUID(),
          type: 'error',
          message: 'Failed to connect to game',
          timestamp: new Date()
        }
      });
    }
  }

  disconnectFromGame() {
    if (this.gameSocket && typeof this.gameSocket.close === 'function') {
      this.gameSocket.close();
      this.gameSocket = null;
    }
    this.currentGameId = null;
  }


  private setupEventListeners() {
    if (!this.socket) return;

    this.socket.onopen = () => {
      console.log('WebSocket onopen event fired');
      // Don't set connection state here - wait for server confirmation message
      this.reconnectAttempts = 0;
      this.connectionMutex = false; // Release mutex on successful connection
    };

    this.socket.onclose = () => {
      useGameStore.getState().dispatch({ type: 'CONNECTION_LOST' });
      
      // Attempt to reconnect if we should (not manually disconnected)
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 5000); // Exponential backoff, max 5s
        console.log(`WebSocket closed, attempting reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
        
        this.reconnectTimeout = setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, delay);
      }
    };

    this.socket.onerror = (error: any) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.connectionMutex = false; // Release mutex on connection error
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        useGameStore.getState().dispatch({ type: 'CONNECTION_LOST', error: 'Max reconnection attempts reached' });
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle different message types
        switch (data.type) {
          case 'connect':
            // Connection confirmed from server
            console.log('Received connection confirmation from server');
            useGameStore.getState().dispatch({ 
              type: 'CONNECTION_ESTABLISHED', 
              clientId: data.data?.connection_id || data.clientId || 'ws-client' 
            });
            break;
          case 'pong':
            // Handle ping/pong for keepalive
            break;
          case 'error':
            // Handle server errors
            if (data.error) {
              useGameStore.getState().dispatch({
                type: 'NOTIFICATION_ADDED',
                notification: {
                  id: crypto.randomUUID(),
                  type: 'error',
                  message: data.error,
                  timestamp: new Date()
                }
              });
            }
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

  private setupGameEventListeners() {
    if (!this.gameSocket) return;

    this.gameSocket.onopen = () => {
      // Game WebSocket connected - already connected to main WS
    };

    this.gameSocket.onclose = () => {
      // Game WebSocket disconnected
    };

    this.gameSocket.onerror = (error: any) => {
      console.error('Game WebSocket connection error:', error);
    };

    this.gameSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle game-specific messages
        switch (data.type) {
          case 'game_state':
            // Only handle game state if we're still connected to the same game
            if (data.data && data.data.game_id === this.currentGameId) {
              const gameState = this.transformApiResponseToGameState(data.data);
              if (gameState) {
                useGameStore.getState().dispatch({ type: 'GAME_STATE_UPDATED', state: gameState });
              }
            }
            break;
          case 'move':
            // Handle move updates for current game
            if (data.data && data.data.game_id === this.currentGameId) {
              this.requestGameState(data.data.game_id);
            }
            break;
          case 'game_ended':
            // Handle game end for current game
            if (data.data && data.data.game_id === this.currentGameId) {
              const gameState = this.transformApiResponseToGameState(data.data);
              if (gameState) {
                useGameStore.getState().dispatch({ type: 'GAME_STATE_UPDATED', state: gameState });
              }
            }
            break;
          case 'error':
            if (data.error) {
              useGameStore.getState().dispatch({ 
                type: 'NOTIFICATION_ADDED', 
                notification: { 
                  id: Date.now().toString(), 
                  type: 'error', 
                  message: data.error, 
                  timestamp: new Date() 
                } 
              });
            }
            break;
          default:
            break;
        }
      } catch (error) {
        console.error('Error parsing game WebSocket message:', error);
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
      
      // Use legal moves from API response if available and transform them
      const backend_legal_moves = apiResponse.legal_moves || [];
      const legal_moves = this.transformLegalMoves(backend_legal_moves, board_size);
      
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

  private transformLegalMoves(backendMoves: string[], boardSize: number): string[] {
    const frontendMoves: string[] = [];

    for (const move of backendMoves) {
      if (move.startsWith('*(')) {
        // Parse piece move: "*(4,7)" -> "e2"
        const match = move.match(/\*\((\d+),(\d+)\)/);
        if (match) {
          const x = parseInt(match[1]);
          const y = parseInt(match[2]);
          const notation = `${String.fromCharCode(97 + x)}${boardSize - y}`;
          frontendMoves.push(notation);
        }
      } else if (move.startsWith('H(') || move.startsWith('V(')) {
        // Parse wall move: "H(1,2)" -> "b7h", "V(3,4)" -> "d5v"
        const match = move.match(/([HV])\((\d+),(\d+)\)/);
        if (match) {
          const orientation = match[1] === 'H' ? 'h' : 'v';
          const x = parseInt(match[2]);
          const y = parseInt(match[3]);
          const notation = `${String.fromCharCode(97 + x)}${boardSize - y}${orientation}`;
          frontendMoves.push(notation);
        }
      }
    }

    return frontendMoves;
  }

  async createGame(settings: any) {
    try {
      if (!this.isConnected()) {
        useGameStore.getState().dispatch({ 
          type: 'NOTIFICATION_ADDED', 
          notification: { 
            id: Date.now().toString(), 
            type: 'error', 
            message: 'Not connected to server', 
            timestamp: new Date() 
          } 
        });
        return;
      }


      // Create game via REST API instead of WebSocket
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

      const response = await fetch('/games', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(gameRequest),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const gameData = await response.json();

      // Transform API response to GameState and create game
      if (gameData) {
        const gameState = this.transformApiResponseToGameState(gameData);
        if (gameState) {
          useGameStore.getState().dispatch({ 
            type: 'GAME_CREATED', 
            gameId: gameData.game_id, 
            state: gameState 
          });
        }
      }


      // Connect to game-specific WebSocket for real-time updates
      this.connectToGame(gameData.game_id);

    } catch (error) {
      console.error('Error creating game:', error);
      
      // Dispatch game creation failure
      useGameStore.getState().dispatch({ 
        type: 'GAME_CREATE_FAILED', 
        error: `Failed to create game: ${error}` 
      });
      
      // Also add notification for user visibility
      useGameStore.getState().dispatch({ 
        type: 'NOTIFICATION_ADDED', 
        notification: { 
          id: Date.now().toString(), 
          type: 'error', 
          message: `Failed to create game: ${error}`, 
          timestamp: new Date() 
        } 
      });
    }
  }

  joinGame(gameId: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().dispatch({ 
        type: 'NOTIFICATION_ADDED', 
        notification: { 
          id: Date.now().toString(), 
          type: 'error', 
          message: 'Not connected to server', 
          timestamp: new Date() 
        } 
      });
      return;
    }

    this.socket.send(JSON.stringify({
      type: 'join_game',
      game_id: gameId
    }));
  }

  async makeMove(gameId: string, move: string) {
    try {
      if (!this.isConnected()) {
        useGameStore.getState().dispatch({ 
          type: 'NOTIFICATION_ADDED', 
          notification: { 
            id: Date.now().toString(), 
            type: 'error', 
            message: 'Not connected to server', 
            timestamp: new Date() 
          } 
        });
        return;
      }

      // Make move via REST API
      const response = await fetch(`/games/${gameId}/moves`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          player_id: 'player1', // For now, assuming player1 - would need proper player tracking
          action: move
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await response.json();

      // Request updated game state after successful move
      await this.requestGameState(gameId);

    } catch (error) {
      console.error('Error making move:', error);
      useGameStore.getState().dispatch({ 
        type: 'NOTIFICATION_ADDED', 
        notification: { 
          id: Date.now().toString(), 
          type: 'error', 
          message: `Failed to make move: ${error}`, 
          timestamp: new Date() 
        } 
      });
    }
  }

  getAIMove(gameId: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      useGameStore.getState().dispatch({ 
        type: 'NOTIFICATION_ADDED', 
        notification: { 
          id: Date.now().toString(), 
          type: 'error', 
          message: 'Not connected to server', 
          timestamp: new Date() 
        } 
      });
      return;
    }

    this.socket.send(JSON.stringify({
      type: 'get_ai_move',
      game_id: gameId
    }));
  }

  private startConnectionMonitoring() {
    // Only start if not already running
    if (this.connectionMonitor !== null) {
      return;
    }
    
    this.connectionMonitor = setInterval(() => {
      // Check if we should be connected but aren't
      if (this.shouldReconnect && !this.isConnected() && !this.connectionMutex) {
        console.log('Connection monitor detected disconnected state, attempting reconnection...');
        this.connect();
      }
    }, 1000); // Check every 1 second for faster reconnection
  }
  
  private stopConnectionMonitoring() {
    if (this.connectionMonitor) {
      clearInterval(this.connectionMonitor);
      this.connectionMonitor = null;
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopConnectionMonitoring();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket && typeof this.socket.close === 'function') {
      this.socket.close();
      this.socket = null;
    }
    this.disconnectFromGame();
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
          useGameStore.getState().dispatch({ type: 'GAME_STATE_UPDATED', state: gameState });
        }
      }
    } catch (error) {
      console.error('Error fetching game state:', error);
    }
  }

  resetGameConnection() {
    // Disconnect from any game-specific connection and reconnect to main endpoint
    // This is called when starting a new game to ensure clean state
    this.disconnect();
    this.connect();
  }
}

export const wsService = new WebSocketService();