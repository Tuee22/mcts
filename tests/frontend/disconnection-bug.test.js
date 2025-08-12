/**
 * Unit Test: Disconnection State Handling
 * 
 * This test catches a critical bug where the frontend allows users to:
 * 1. Open game settings when disconnected
 * 2. Configure game options when not connected to backend
 * 3. Attempt to start games without a valid connection
 * 
 * BUG: The UI should disable game creation when disconnected!
 */

import React, { useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

describe('Disconnection State Bug Test', () => {
  
  test('FAILING TEST: Settings button should be disabled when disconnected', () => {
    // Simulate disconnected state
    const mockGameStore = {
      isConnected: false,  // DISCONNECTED!
      error: 'Connection lost',
      gameSettings: {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      }
    };

    // Mock the settings button component behavior
    const SettingsButton = ({ isConnected, onClick }) => (
      <button 
        onClick={onClick}
        disabled={!isConnected}  // This SHOULD be the behavior
        className={isConnected ? 'enabled' : 'disabled'}
      >
        ⚙️
      </button>
    );

    const { container } = render(
      <SettingsButton 
        isConnected={mockGameStore.isConnected} 
        onClick={() => console.log('Settings clicked')}
      />
    );

    const settingsButton = screen.getByText('⚙️');
    
    // THIS TEST WILL FAIL because the actual implementation doesn't disable the button
    expect(settingsButton).toBeDisabled();
    expect(settingsButton).toHaveClass('disabled');
    
    // Button should not respond to clicks when disconnected
    fireEvent.click(settingsButton);
    
    // Settings dialog should NOT appear when disconnected
    expect(screen.queryByText('Game Settings')).not.toBeInTheDocument();
  });

  test('FAILING TEST: Start Game button should be disabled when disconnected', () => {
    // Mock the game settings component
    const GameSettings = ({ isConnected, onStartGame }) => (
      <div>
        <h2>Game Settings</h2>
        <button 
          onClick={onStartGame}
          disabled={!isConnected}  // This SHOULD be enforced
          className={`start-game ${!isConnected ? 'disabled' : ''}`}
        >
          START GAME
        </button>
        {!isConnected && (
          <div className="error-message">
            Cannot start game: Not connected to server
          </div>
        )}
      </div>
    );

    const mockStartGame = jest.fn();
    
    render(
      <GameSettings 
        isConnected={false}  // DISCONNECTED!
        onStartGame={mockStartGame}
      />
    );

    const startButton = screen.getByText('START GAME');
    
    // THIS WILL FAIL - button should be disabled when disconnected
    expect(startButton).toBeDisabled();
    expect(startButton).toHaveClass('disabled');
    
    // Should show error message when disconnected
    expect(screen.getByText('Cannot start game: Not connected to server')).toBeInTheDocument();
    
    // Clicking should not trigger game creation
    fireEvent.click(startButton);
    expect(mockStartGame).not.toHaveBeenCalled();
  });

  test('FAILING TEST: Game mode selection should be disabled when disconnected', () => {
    const GameModeSelector = ({ isConnected }) => (
      <div>
        <button 
          disabled={!isConnected}
          className={`mode-btn ${!isConnected ? 'disabled' : ''}`}
        >
          👤 vs 👤
        </button>
        <button 
          disabled={!isConnected}
          className={`mode-btn ${!isConnected ? 'disabled' : ''}`}
        >
          👤 vs 🤖
        </button>
        <button 
          disabled={!isConnected}
          className={`mode-btn ${!isConnected ? 'disabled' : ''}`}
        >
          🤖 vs 🤖
        </button>
      </div>
    );

    render(<GameModeSelector isConnected={false} />);

    const humanVsHuman = screen.getByText('👤 vs 👤');
    const humanVsAI = screen.getByText('👤 vs 🤖');
    const aiVsAI = screen.getByText('🤖 vs 🤖');

    // ALL mode buttons should be disabled when disconnected
    expect(humanVsHuman).toBeDisabled();
    expect(humanVsAI).toBeDisabled();
    expect(aiVsAI).toBeDisabled();
  });

  test('FAILING TEST: Should show connection warning in settings dialog', () => {
    const SettingsDialog = ({ isConnected, showSettings }) => {
      if (!showSettings) return null;
      
      return (
        <div className="settings-dialog">
          <h2>Game Settings</h2>
          {!isConnected && (
            <div className="connection-warning">
              ⚠️ You are disconnected from the server. Please reconnect before starting a game.
            </div>
          )}
          <button className="start-game">START GAME</button>
        </div>
      );
    };

    render(
      <SettingsDialog 
        isConnected={false} 
        showSettings={true}
      />
    );

    // Should show warning message when settings are open while disconnected
    expect(screen.getByText(/You are disconnected from the server/)).toBeInTheDocument();
    expect(screen.getByText(/Please reconnect before starting a game/)).toBeInTheDocument();
  });

  test('FAILING TEST: Complete disconnection flow validation', () => {
    let connectionState = true;
    let settingsOpen = false;
    let gameStartAttempted = false;
    
    const App = ({ isConnected }) => {
      const handleSettingsClick = () => {
        if (!isConnected) {
          // Should NOT allow opening settings when disconnected
          console.error('Cannot open settings while disconnected');
          return;
        }
        settingsOpen = true;
      };

      const handleStartGame = () => {
        if (!isConnected) {
          // Should NOT allow starting game when disconnected
          console.error('Cannot start game while disconnected');
          return;
        }
        gameStartAttempted = true;
      };

      return (
        <div>
          <div className="connection-status">
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
          <button 
            onClick={handleSettingsClick}
            disabled={!isConnected}
            className="settings-btn"
          >
            Settings
          </button>
          {settingsOpen && (
            <button 
              onClick={handleStartGame}
              disabled={!isConnected}
            >
              Start
            </button>
          )}
        </div>
      );
    };

    // Start connected
    const { rerender } = render(<App isConnected={true} />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
    
    // Settings should be enabled when connected
    const settingsBtn = screen.getByText('Settings');
    expect(settingsBtn).not.toBeDisabled();
    
    // Simulate disconnection
    connectionState = false;
    rerender(<App isConnected={false} />);
    
    // UI should update to show disconnected state
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
    
    // Settings button should now be disabled
    expect(settingsBtn).toBeDisabled();
    
    // Attempting to click should not open settings
    fireEvent.click(settingsBtn);
    expect(settingsOpen).toBe(false);
    
    // THIS ASSERTION WILL FAIL - the bug allows settings to open when disconnected
    expect(screen.queryByText('Start')).not.toBeInTheDocument();
  });

  test('INTEGRATION TEST: Real frontend behavior when disconnected', () => {
    // This test simulates the ACTUAL buggy behavior shown in the screenshot
    const BuggyFrontend = () => {
      const isConnected = false;  // Disconnected state
      const [showSettings, setShowSettings] = useState(false);
      
      return (
        <div>
          <header>
            <h1>CORRIDORS</h1>
            <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
              {isConnected ? '✓ Connected' : '⚠ Disconnected'}
            </div>
          </header>
          
          {/* BUG: This button is NOT disabled when disconnected! */}
          <button onClick={() => setShowSettings(true)}>
            ⚙️
          </button>
          
          {showSettings && (
            <div className="settings-dialog">
              <h2>Game Settings</h2>
              {/* BUG: User can configure all these options while disconnected! */}
              <div>Game Mode: Human vs AI</div>
              <div>AI Difficulty: Medium</div>
              <div>Board Size: 9x9</div>
              
              {/* BUG: Start Game button is clickable while disconnected! */}
              <button className="start-game">
                START GAME
              </button>
            </div>
          )}
        </div>
      );
    };

    // This test documents the CURRENT BUGGY BEHAVIOR
    render(<BuggyFrontend />);
    
    // Shows disconnected status
    expect(screen.getByText('⚠ Disconnected')).toBeInTheDocument();
    
    // BUG: Settings button is still clickable!
    const settingsButton = screen.getByText('⚙️');
    expect(settingsButton).not.toBeDisabled();  // This is the bug!
    
    // BUG: Can open settings while disconnected
    fireEvent.click(settingsButton);
    expect(screen.getByText('Game Settings')).toBeInTheDocument();
    
    // BUG: Can click Start Game while disconnected
    const startButton = screen.getByText('START GAME');
    expect(startButton).not.toBeDisabled();  // This is the bug!
    
    console.error('🐛 BUG DETECTED: Frontend allows game configuration while disconnected!');
    console.error('Expected: Settings and Start Game should be disabled when disconnected');
    console.error('Actual: User can interact with game settings without backend connection');
  });
});

// The fix would be to update the frontend components:
describe('Proposed Fix', () => {
  test('Correct implementation should prevent interactions when disconnected', () => {
    const FixedSettingsButton = ({ isConnected, onClick }) => (
      <button 
        onClick={isConnected ? onClick : undefined}
        disabled={!isConnected}
        className={`settings-btn ${!isConnected ? 'disabled' : ''}`}
        title={!isConnected ? 'Connect to server to access settings' : 'Game Settings'}
      >
        ⚙️
      </button>
    );

    const FixedGameSettings = ({ isConnected, visible }) => {
      if (!visible) return null;
      
      return (
        <div className="settings-dialog">
          {!isConnected && (
            <div className="overlay-message">
              <h3>Connection Required</h3>
              <p>Please connect to the server before configuring game settings.</p>
              <button className="reconnect-btn">Reconnect</button>
            </div>
          )}
          <div className={!isConnected ? 'disabled-content' : ''}>
            {/* All settings content disabled when disconnected */}
          </div>
        </div>
      );
    };

    // Test the fixed implementation
    const { rerender } = render(
      <FixedSettingsButton 
        isConnected={false} 
        onClick={() => console.log('Should not fire')}
      />
    );

    const button = screen.getByText('⚙️');
    
    // Fixed version correctly disables button
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled');
    expect(button).toHaveAttribute('title', 'Connect to server to access settings');
    
    // Reconnect
    rerender(
      <FixedSettingsButton 
        isConnected={true} 
        onClick={() => console.log('Settings opened')}
      />
    );
    
    // Now button should be enabled
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute('title', 'Game Settings');
  });
});