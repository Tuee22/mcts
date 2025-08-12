import { wsService } from '../../../frontend/src/services/websocket';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { MockWebSocket, mockWebSocketEvents } from '../mocks/websocket.mock';

// Mock dependencies
jest.mock('../../../frontend/src/store/gameStore');
jest.mock('socket.io-client', () => ({
  __esModule: true,
  default: jest.fn(() => new MockWebSocket('http://localhost:8000')),
  Socket: MockWebSocket
}));

const mockUseGameStore = useGameStore as jest.MockedFunction<typeof useGameStore>;

describe('WebSocket Service', () => {
  let mockSocket: MockWebSocket;
  let mockStore: any;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockStore = {
      setIsConnected: jest.fn(),
      setError: jest.fn(),
      setGameId: jest.fn(),
      setGameState: jest.fn(),
      setIsLoading: jest.fn(),
      addMoveToHistory: jest.fn(),
      getState: () => mockStore
    };
    
    mockUseGameStore.mockReturnValue(mockStore);
    
    // Reset the service
    wsService.disconnect();
  });

  describe('Connection Management', () => {
    it('connects to default URL', () => {
      wsService.connect();
      
      expect(wsService.isConnected()).toBe(false); // Initially connecting
      
      // Simulate connection
      setTimeout(() => {
        expect(mockStore.setIsConnected).toHaveBeenCalledWith(true);
        expect(mockStore.setError).toHaveBeenCalledWith(null);
      }, 20);
    });

    it('connects to custom URL', () => {
      const customUrl = 'http://localhost:3001';
      wsService.connect(customUrl);
      
      // The mock socket should be created with custom URL
      expect(wsService.isConnected()).toBe(false);
    });

    it('does not reconnect if already connected', () => {
      wsService.connect();
      const firstConnection = wsService.isConnected();
      
      wsService.connect();
      const secondConnection = wsService.isConnected();
      
      expect(firstConnection).toBe(secondConnection);
    });

    it('handles connection events', (done) => {
      wsService.connect();
      
      // Wait for connection event
      setTimeout(() => {
        expect(mockStore.setIsConnected).toHaveBeenCalledWith(true);
        expect(mockStore.setError).toHaveBeenCalledWith(null);
        done();
      }, 20);
    });

    it('handles disconnect events', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        wsService.disconnect();
        expect(mockStore.setIsConnected).toHaveBeenCalledWith(false);
        done();
      }, 20);
    });

    it('handles connection errors', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        // Simulate connection error multiple times to trigger max attempts
        for (let i = 0; i < 6; i++) {
          mockSocket.emit('connect_error', new Error('Connection failed'));
        }
        
        expect(mockStore.setError).toHaveBeenCalledWith(
          'Failed to connect to server. Please check if the server is running.'
        );
        done();
      }, 20);
    });

    it('resets reconnection attempts on successful connection', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        // Simulate some failed attempts
        mockSocket.emit('connect_error', new Error('Connection failed'));
        mockSocket.emit('connect_error', new Error('Connection failed'));
        
        // Then successful connection
        mockSocket.emit('connect');
        
        // Should reset attempts counter
        expect(mockStore.setError).toHaveBeenCalledWith(null);
        done();
      }, 20);
    });
  });

  describe('Game Events', () => {
    beforeEach((done) => {
      wsService.connect();
      setTimeout(done, 20); // Wait for connection
    });

    it('handles game_created event', () => {
      mockSocket.emit('game_created', mockWebSocketEvents.gameCreated);
      
      expect(mockStore.setGameId).toHaveBeenCalledWith('test-game-123');
      expect(mockStore.setGameState).toHaveBeenCalledWith(mockWebSocketEvents.gameCreated.state);
      expect(mockStore.setIsLoading).toHaveBeenCalledWith(false);
    });

    it('handles game_state event', () => {
      mockSocket.emit('game_state', mockWebSocketEvents.gameState);
      
      expect(mockStore.setGameState).toHaveBeenCalledWith(mockWebSocketEvents.gameState.state);
    });

    it('handles move_made event', () => {
      mockSocket.emit('move_made', mockWebSocketEvents.moveMade);
      
      expect(mockStore.setGameState).toHaveBeenCalledWith(mockWebSocketEvents.moveMade.state);
      expect(mockStore.addMoveToHistory).toHaveBeenCalledWith(mockWebSocketEvents.moveMade.move);
    });

    it('handles game_over event', () => {
      mockSocket.emit('game_over', mockWebSocketEvents.gameOver);
      
      const expectedState = {
        ...mockWebSocketEvents.gameOver.state,
        winner: 0
      };
      
      expect(mockStore.setGameState).toHaveBeenCalledWith(expectedState);
    });

    it('handles error event', () => {
      mockSocket.emit('error', mockWebSocketEvents.error);
      
      expect(mockStore.setError).toHaveBeenCalledWith('Invalid move');
      expect(mockStore.setIsLoading).toHaveBeenCalledWith(false);
    });
  });

  describe('Game Actions', () => {
    beforeEach((done) => {
      wsService.connect();
      setTimeout(done, 20); // Wait for connection
    });

    describe('createGame', () => {
      it('creates game with settings', () => {
        const settings = {
          mode: 'human_vs_ai',
          ai_difficulty: 'medium',
          board_size: 9
        };
        
        const emitSpy = jest.spyOn(mockSocket, 'emit');
        wsService.createGame(settings);
        
        expect(mockStore.setIsLoading).toHaveBeenCalledWith(true);
        expect(emitSpy).toHaveBeenCalledWith('create_game', settings);
      });

      it('handles disconnected state', () => {
        wsService.disconnect();
        
        const settings = { mode: 'human_vs_ai' };
        wsService.createGame(settings);
        
        expect(mockStore.setError).toHaveBeenCalledWith('Not connected to server');
      });
    });

    describe('joinGame', () => {
      it('joins existing game', () => {
        const gameId = 'test-game-123';
        
        const emitSpy = jest.spyOn(mockSocket, 'emit');
        wsService.joinGame(gameId);
        
        expect(mockStore.setIsLoading).toHaveBeenCalledWith(true);
        expect(emitSpy).toHaveBeenCalledWith('join_game', { game_id: gameId });
      });

      it('handles disconnected state', () => {
        wsService.disconnect();
        
        wsService.joinGame('test-game');
        
        expect(mockStore.setError).toHaveBeenCalledWith('Not connected to server');
      });
    });

    describe('makeMove', () => {
      it('makes a move', () => {
        const gameId = 'test-game-123';
        const move = 'e2';
        
        const emitSpy = jest.spyOn(mockSocket, 'emit');
        wsService.makeMove(gameId, move);
        
        expect(emitSpy).toHaveBeenCalledWith('make_move', {
          game_id: gameId,
          move: move
        });
      });

      it('handles disconnected state', () => {
        wsService.disconnect();
        
        wsService.makeMove('test-game', 'e2');
        
        expect(mockStore.setError).toHaveBeenCalledWith('Not connected to server');
      });
    });

    describe('getAIMove', () => {
      it('requests AI move', () => {
        const gameId = 'test-game-123';
        
        const emitSpy = jest.spyOn(mockSocket, 'emit');
        wsService.getAIMove(gameId);
        
        expect(emitSpy).toHaveBeenCalledWith('get_ai_move', { game_id: gameId });
      });

      it('handles disconnected state', () => {
        wsService.disconnect();
        
        wsService.getAIMove('test-game');
        
        expect(mockStore.setError).toHaveBeenCalledWith('Not connected to server');
      });
    });
  });

  describe('Connection State', () => {
    it('reports connected state correctly', (done) => {
      expect(wsService.isConnected()).toBe(false);
      
      wsService.connect();
      
      setTimeout(() => {
        expect(wsService.isConnected()).toBe(true);
        done();
      }, 20);
    });

    it('reports disconnected state correctly', () => {
      wsService.disconnect();
      
      expect(wsService.isConnected()).toBe(false);
    });
  });

  describe('Error Scenarios', () => {
    it('handles multiple connection errors gracefully', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        // Simulate multiple errors
        for (let i = 0; i < 3; i++) {
          mockSocket.emit('connect_error', new Error(`Error ${i}`));
        }
        
        // Should not crash
        expect(mockStore.setError).not.toHaveBeenCalledWith(
          expect.stringContaining('Failed to connect')
        );
        done();
      }, 20);
    });

    it('handles malformed server events', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        // Send malformed events
        mockSocket.emit('game_created', { invalid: 'data' });
        mockSocket.emit('game_state', null);
        mockSocket.emit('move_made', undefined);
        
        // Should not crash
        expect(mockStore.setError).not.toHaveBeenCalledWith(
          expect.stringContaining('crash')
        );
        done();
      }, 20);
    });

    it('handles rapid connect/disconnect cycles', (done) => {
      for (let i = 0; i < 5; i++) {
        wsService.connect();
        wsService.disconnect();
      }
      
      setTimeout(() => {
        // Should handle gracefully without crashes
        expect(mockStore.setIsConnected).toHaveBeenCalled();
        done();
      }, 50);
    });
  });

  describe('Memory Management', () => {
    it('cleans up event listeners on disconnect', () => {
      wsService.connect();
      wsService.disconnect();
      
      // After disconnect, events should not trigger store updates
      mockSocket.emit('game_created', mockWebSocketEvents.gameCreated);
      
      // Should not be called after disconnect
      expect(mockStore.setGameId).not.toHaveBeenCalled();
    });

    it('handles multiple disconnect calls safely', () => {
      wsService.connect();
      
      // Multiple disconnects should not cause errors
      expect(() => {
        wsService.disconnect();
        wsService.disconnect();
        wsService.disconnect();
      }).not.toThrow();
    });
  });

  describe('Reconnection Logic', () => {
    it('attempts reconnection on connection loss', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        // Simulate connection loss
        mockSocket.emit('disconnect');
        expect(mockStore.setIsConnected).toHaveBeenCalledWith(false);
        
        // Simulate reconnection attempt
        mockSocket.emit('connect_error', new Error('Reconnection attempt'));
        
        // Should track reconnection attempts
        expect(mockStore.setError).not.toHaveBeenCalledWith(
          'Failed to connect to server. Please check if the server is running.'
        );
        
        done();
      }, 20);
    });

    it('stops reconnection after max attempts', (done) => {
      wsService.connect();
      
      setTimeout(() => {
        // Simulate max reconnection attempts
        for (let i = 0; i <= 5; i++) {
          mockSocket.emit('connect_error', new Error('Connection failed'));
        }
        
        expect(mockStore.setError).toHaveBeenCalledWith(
          'Failed to connect to server. Please check if the server is running.'
        );
        
        done();
      }, 20);
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined gameId in actions', () => {
      wsService.connect();
      
      // Should not crash with undefined gameId
      expect(() => {
        wsService.makeMove(undefined as any, 'e2');
        wsService.getAIMove(undefined as any);
        wsService.joinGame(undefined as any);
      }).not.toThrow();
    });

    it('handles null moves', () => {
      wsService.connect();
      
      // Should not crash with null move
      expect(() => {
        wsService.makeMove('test-game', null as any);
        wsService.makeMove('test-game', undefined as any);
      }).not.toThrow();
    });

    it('handles empty settings', () => {
      wsService.connect();
      
      // Should not crash with empty settings
      expect(() => {
        wsService.createGame({} as any);
        wsService.createGame(null as any);
        wsService.createGame(undefined as any);
      }).not.toThrow();
    });
  });
});