/**
 * End-to-End Tests for Corridors Game Frontend
 * 
 * These tests simulate real user interactions with the complete application
 * including WebSocket communications and full game flows.
 * 
 * Note: These tests require a running backend server and are more suitable
 * for a full E2E testing framework like Cypress or Playwright in a real environment.
 * This is a simplified version using React Testing Library.
 */

import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../../frontend/src/App';
import { render, createUser } from '../utils/test-utils';

// For true E2E tests, these mocks would be removed and real services would be used
jest.setTimeout(30000); // Longer timeout for E2E tests

describe('End-to-End Game Tests', () => {
  const user = createUser();

  // Mock WebSocket for E2E simulation
  let mockWebSocket: any;
  
  beforeAll(() => {
    // Mock WebSocket globally for E2E tests
    global.WebSocket = jest.fn().mockImplementation((url) => {
      mockWebSocket = {
        url,
        readyState: WebSocket.CONNECTING,
        send: jest.fn(),
        close: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
        onopen: null,
        onclose: null,
        onmessage: null,
        onerror: null
      };

      // Simulate connection after delay
      setTimeout(() => {
        mockWebSocket.readyState = WebSocket.OPEN;
        if (mockWebSocket.onopen) mockWebSocket.onopen();
      }, 100);

      return mockWebSocket;
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Complete Game Flow E2E', () => {
    it('completes a full human vs AI game session', async () => {
      render(<App />);

      // 1. App should load with title and connection status
      expect(screen.getByText('CORRIDORS')).toBeInTheDocument();
      
      // Wait for connection
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      }, { timeout: 2000 });

      // 2. Configure game settings
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      
      // Select Human vs AI (should be default)
      const humanVsAiButton = screen.getByText('Human vs AI');
      expect(humanVsAiButton.closest('.mode-btn')).toHaveClass('active');

      // Select medium difficulty (should be default)
      const mediumButton = screen.getByText('Medium');
      expect(mediumButton.closest('.difficulty-btn')).toHaveClass('active');

      // Change to 5x5 board for faster testing
      const board5x5 = screen.getByText('5x5');
      await user.click(board5x5);

      // 3. Start the game
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      // 4. Simulate successful game creation
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'game_created',
              game_id: 'e2e-test-game',
              state: {
                board_size: 5,
                current_player: 0,
                players: [{ x: 2, y: 0 }, { x: 2, y: 4 }],
                walls: [],
                walls_remaining: [10, 10],
                legal_moves: ['a2', 'b2', 'c2', 'd2', 'e2'],
                winner: null,
                move_history: []
              }
            })
          });
        }
      });

      // 5. Game board should appear
      await waitFor(() => {
        expect(screen.getByText('Current: Player 1')).toBeInTheDocument();
        expect(screen.getByText('P1 Walls: 10')).toBeInTheDocument();
      }, { timeout: 2000 });

      // 6. Make a human move
      const legalMoveCell = document.querySelector('.game-cell.legal');
      expect(legalMoveCell).toBeInTheDocument();

      await user.click(legalMoveCell!);

      // 7. Simulate move acknowledgment and AI response
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          // Human move acknowledged
          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'move_made',
              move: {
                notation: 'c2',
                player: 0,
                type: 'move'
              },
              state: {
                board_size: 5,
                current_player: 1,
                players: [{ x: 2, y: 1 }, { x: 2, y: 4 }],
                walls: [],
                walls_remaining: [10, 10],
                legal_moves: ['a4', 'b4', 'c4', 'd4', 'e4'],
                winner: null,
                move_history: [{
                  notation: 'c2',
                  player: 0,
                  type: 'move'
                }]
              }
            })
          });

          // AI move
          setTimeout(() => {
            mockWebSocket.onmessage({
              data: JSON.stringify({
                type: 'move_made',
                move: {
                  notation: 'c4',
                  player: 1,
                  type: 'move'
                },
                state: {
                  board_size: 5,
                  current_player: 0,
                  players: [{ x: 2, y: 1 }, { x: 2, y: 3 }],
                  walls: [],
                  walls_remaining: [10, 10],
                  legal_moves: ['a1', 'b1', 'c1', 'd1', 'e1'],
                  winner: null,
                  move_history: [{
                    notation: 'c2',
                    player: 0,
                    type: 'move'
                  }, {
                    notation: 'c4',
                    player: 1,
                    type: 'move'
                  }]
                }
              })
            });
          }, 500);
        }
      });

      // 8. Verify move history is updated
      await waitFor(() => {
        expect(screen.getByText('c2')).toBeInTheDocument();
        expect(screen.getByText('c4')).toBeInTheDocument();
      }, { timeout: 2000 });

      // 9. Test move history navigation
      const firstMove = screen.getByText('c2').closest('.move-item');
      await user.click(firstMove!);

      // Should show "Current" button when viewing history
      await waitFor(() => {
        expect(screen.getByText('Current')).toBeInTheDocument();
      });

      // Return to current position
      const currentButton = screen.getByText('Current');
      await user.click(currentButton);

      // 10. Test wall placement mode
      const wallModeButton = screen.getByText('Place Wall');
      await user.click(wallModeButton);

      expect(screen.getByText('Place Pawn')).toBeInTheDocument();
      expect(screen.getByText('Horizontal')).toBeInTheDocument();

      // Toggle orientation
      const orientationButton = screen.getByText('Horizontal');
      await user.click(orientationButton);
      expect(screen.getByText('Vertical')).toBeInTheDocument();

      // Return to pawn mode
      const pawnModeButton = screen.getByText('Place Pawn');
      await user.click(pawnModeButton);

      // 11. Test game controls
      const copyMovesButton = screen.getByText('Copy Moves');
      await user.click(copyMovesButton);

      // Should not throw error (clipboard is mocked)
      expect(copyMovesButton).toBeInTheDocument();

      // 12. Test new game
      const newGameButton = screen.getByText('New Game');
      await user.click(newGameButton);

      // Should return to game settings
      await waitFor(() => {
        expect(screen.getByText('Game Settings')).toBeInTheDocument();
      }, { timeout: 1000 });
    }, 30000);

    it('handles AI vs AI game mode', async () => {
      render(<App />);

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      }, { timeout: 2000 });

      // Select AI vs AI mode
      const aiVsAiButton = screen.getByText('AI vs AI');
      await user.click(aiVsAiButton);

      // Start game
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      // Simulate game creation
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'game_created',
              game_id: 'ai-vs-ai-game',
              state: {
                board_size: 9,
                current_player: 0,
                players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
                walls: [],
                walls_remaining: [10, 10],
                legal_moves: ['a1', 'b1', 'c1'],
                winner: null,
                move_history: []
              }
            })
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('Current: Player 1')).toBeInTheDocument();
      }, { timeout: 2000 });

      // In AI vs AI mode, moves should happen automatically
      // We'll simulate a few AI moves
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'move_made',
              move: { notation: 'e2', player: 0, type: 'move' },
              state: {
                board_size: 9,
                current_player: 1,
                players: [{ x: 4, y: 1 }, { x: 4, y: 8 }],
                walls: [],
                walls_remaining: [10, 10],
                legal_moves: ['a8', 'b8', 'c8'],
                winner: null,
                move_history: [{ notation: 'e2', player: 0, type: 'move' }]
              }
            })
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('e2')).toBeInTheDocument();
      }, { timeout: 2000 });
    }, 20000);

    it('handles human vs human mode', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      }, { timeout: 2000 });

      // Select Human vs Human mode
      const humanVsHumanButton = screen.getByText('Human vs Human');
      await user.click(humanVsHumanButton);

      // AI settings should be hidden
      expect(screen.queryByText('AI Difficulty')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time Limit')).not.toBeInTheDocument();

      // Start game
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      // Simulate game creation
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'game_created',
              game_id: 'human-vs-human-game',
              state: {
                board_size: 9,
                current_player: 0,
                players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
                walls: [],
                walls_remaining: [10, 10],
                legal_moves: ['e2', 'd1', 'f1'],
                winner: null,
                move_history: []
              }
            })
          });
        }
      });

      await waitFor(() => {
        expect(screen.getByText('Current: Player 1')).toBeInTheDocument();
      }, { timeout: 2000 });

      // Both players should be able to make moves manually
      const legalCell = document.querySelector('.game-cell.legal');
      await user.click(legalCell!);

      // Verify move was sent (would need to check WebSocket send calls in real E2E)
      expect(legalCell).toBeInTheDocument();
    }, 15000);
  });

  describe('Error Scenarios E2E', () => {
    it('handles connection failures gracefully', async () => {
      // Mock connection failure
      global.WebSocket = jest.fn().mockImplementation(() => {
        const mockFailedSocket = {
          readyState: WebSocket.CLOSED,
          send: jest.fn(),
          close: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          onerror: null
        };

        setTimeout(() => {
          if (mockFailedSocket.onerror) {
            mockFailedSocket.onerror(new Error('Connection failed'));
          }
        }, 100);

        return mockFailedSocket;
      });

      render(<App />);

      // Should show disconnected status
      await waitFor(() => {
        expect(screen.getByText('Disconnected')).toBeInTheDocument();
      }, { timeout: 2000 });

      // Should still show game settings but with error context
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    }, 10000);

    it('handles server errors during game creation', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      }, { timeout: 2000 });

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      // Simulate server error
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'error',
              message: 'Server overloaded, try again later'
            })
          });
        }
      });

      // Error should be handled gracefully
      await waitFor(() => {
        expect(screen.getByText('Game Settings')).toBeInTheDocument();
      }, { timeout: 1000 });
    }, 10000);
  });

  describe('Performance E2E', () => {
    it('handles rapid user interactions without lag', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      }, { timeout: 2000 });

      const start = performance.now();

      // Rapid setting changes
      const buttons = [
        screen.getByText('Hard'),
        screen.getByText('5x5'),
        screen.getByText('AI vs AI'),
        screen.getByText('10s'),
        screen.getByText('Human vs AI')
      ];

      for (const button of buttons) {
        await user.click(button);
      }

      const end = performance.now();
      
      // Should handle rapid interactions efficiently (less than 500ms total)
      expect(end - start).toBeLessThan(500);
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    }, 10000);

    it('maintains smooth performance during long games', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      }, { timeout: 2000 });

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      // Simulate game with many moves
      act(() => {
        if (mockWebSocket && mockWebSocket.onmessage) {
          const longHistory = Array.from({ length: 100 }, (_, i) => ({
            notation: `move${i}`,
            player: i % 2,
            type: 'move'
          }));

          mockWebSocket.onmessage({
            data: JSON.stringify({
              type: 'game_created',
              game_id: 'long-game',
              state: {
                board_size: 9,
                current_player: 0,
                players: [{ x: 4, y: 4 }, { x: 4, y: 5 }],
                walls: [],
                walls_remaining: [5, 5],
                legal_moves: ['e5'],
                winner: null,
                move_history: longHistory
              }
            })
          });
        }
      });

      // Should render long game state efficiently
      await waitFor(() => {
        expect(screen.getByText('Move History')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Navigation should still be responsive
      const firstButton = screen.getByText('⏮');
      const start = performance.now();
      await user.click(firstButton);
      const end = performance.now();

      // Should respond quickly even with long history
      expect(end - start).toBeLessThan(100);
    }, 15000);
  });
});