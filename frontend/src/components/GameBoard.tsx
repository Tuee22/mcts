import React, { useState } from 'react';
import { useGameStore } from '../store/gameStore';
import { wsService } from '../services/websocket';
import { Position, Wall } from '../types/game';
import './GameBoard.css';

export const GameBoard: React.FC = () => {
  const { gameState, gameId, selectedHistoryIndex } = useGameStore();
  const [hoveredCell, setHoveredCell] = useState<Position | null>(null);
  const [hoveredWall, setHoveredWall] = useState<Wall | null>(null);
  const [wallPlacementMode, setWallPlacementMode] = useState(false);
  const [wallOrientation, setWallOrientation] = useState<'horizontal' | 'vertical'>('horizontal');

  const displayState = selectedHistoryIndex !== null && gameState?.move_history[selectedHistoryIndex]
    ? gameState.move_history[selectedHistoryIndex].board_state || gameState
    : gameState;

  if (!displayState) {
    return <div className="game-board-empty">No game in progress</div>;
  }

  const boardSize = displayState.board_size;
  const cellSize = 50;
  const wallWidth = 8;

  const isLegalMove = (x: number, y: number): boolean => {
    const moveNotation = `${String.fromCharCode(97 + x)}${boardSize - y}`;
    return displayState.legal_moves.includes(moveNotation);
  };

  const isLegalWall = (wall: Wall): boolean => {
    const wallNotation = `${String.fromCharCode(97 + wall.x)}${boardSize - wall.y}${wall.orientation[0]}`;
    return displayState.legal_moves.includes(wallNotation);
  };

  const handleCellClick = (x: number, y: number) => {
    if (!gameId || selectedHistoryIndex !== null) return;

    if (wallPlacementMode) {
      return;
    }

    const moveNotation = `${String.fromCharCode(97 + x)}${boardSize - y}`;
    if (isLegalMove(x, y)) {
      wsService.makeMove(gameId, moveNotation);
    }
  };

  const handleWallClick = (x: number, y: number, orientation: 'horizontal' | 'vertical') => {
    if (!gameId || selectedHistoryIndex !== null) return;

    const wallNotation = `${String.fromCharCode(97 + x)}${boardSize - y}${orientation[0]}`;
    if (displayState.legal_moves.includes(wallNotation)) {
      wsService.makeMove(gameId, wallNotation);
    }
  };

  const toggleWallMode = () => {
    setWallPlacementMode(!wallPlacementMode);
    setHoveredWall(null);
    setHoveredCell(null);
  };

  const toggleWallOrientation = () => {
    setWallOrientation(wallOrientation === 'horizontal' ? 'vertical' : 'horizontal');
  };

  const renderCell = (x: number, y: number) => {
    const player0 = displayState.players?.[0];
    const player1 = displayState.players?.[1];
    const isPlayer0 = player0?.x === x && player0?.y === y;
    const isPlayer1 = player1?.x === x && player1?.y === y;
    const isHovered = hoveredCell?.x === x && hoveredCell?.y === y;
    const isLegal = isLegalMove(x, y);

    return (
      <div
        key={`cell-${x}-${y}`}
        className={`game-cell ${isHovered && isLegal && !wallPlacementMode ? 'hovered' : ''} ${isLegal && !wallPlacementMode ? 'legal' : ''}`}
        style={{
          left: x * cellSize,
          top: y * cellSize,
          width: cellSize,
          height: cellSize,
        }}
        onMouseEnter={() => !wallPlacementMode && setHoveredCell({ x, y })}
        onMouseLeave={() => setHoveredCell(null)}
        onClick={() => handleCellClick(x, y)}
      >
        {isPlayer0 && <div className="player player-0">P1</div>}
        {isPlayer1 && <div className="player player-1">P2</div>}
      </div>
    );
  };

  const renderWall = (wall: Wall) => {
    const key = `wall-${wall.x}-${wall.y}-${wall.orientation}`;
    const style = wall.orientation === 'horizontal'
      ? {
          left: wall.x * cellSize,
          top: wall.y * cellSize + cellSize - wallWidth / 2,
          width: cellSize * 2,
          height: wallWidth,
        }
      : {
          left: wall.x * cellSize + cellSize - wallWidth / 2,
          top: wall.y * cellSize,
          width: wallWidth,
          height: cellSize * 2,
        };

    return (
      <div
        key={key}
        className={`game-wall ${wall.orientation}`}
        style={style}
      />
    );
  };

  const renderWallSlot = (x: number, y: number, orientation: 'horizontal' | 'vertical') => {
    if (x >= boardSize - 1 || y >= boardSize - 1) return null;

    const wall = { x, y, orientation };
    const isHovered = hoveredWall?.x === x && hoveredWall?.y === y && hoveredWall?.orientation === orientation;
    const isLegal = wallPlacementMode && isLegalWall(wall);

    const style = orientation === 'horizontal'
      ? {
          left: x * cellSize,
          top: y * cellSize + cellSize - wallWidth / 2,
          width: cellSize * 2,
          height: wallWidth,
        }
      : {
          left: x * cellSize + cellSize - wallWidth / 2,
          top: y * cellSize,
          width: wallWidth,
          height: cellSize * 2,
        };

    return (
      <div
        key={`wall-slot-${x}-${y}-${orientation}`}
        className={`wall-slot ${orientation} ${isHovered && isLegal ? 'hovered' : ''} ${isLegal ? 'legal' : ''}`}
        style={style}
        onMouseEnter={() => wallPlacementMode && setHoveredWall(wall)}
        onMouseLeave={() => setHoveredWall(null)}
        onClick={() => wallPlacementMode && handleWallClick(x, y, orientation)}
      />
    );
  };

  return (
    <div className="game-board-container">
      <div className="game-controls">
        <button 
          className={`retro-btn ${wallPlacementMode ? 'active' : ''}`}
          onClick={toggleWallMode}
          aria-label={wallPlacementMode ? 'Switch to pawn placement mode' : 'Switch to wall placement mode'}
        >
          {wallPlacementMode ? 'Place Pawn' : 'Place Wall'}
        </button>
        {wallPlacementMode && (
          <button 
            className="retro-btn"
            onClick={toggleWallOrientation}
          >
            {wallOrientation === 'horizontal' ? 'Horizontal' : 'Vertical'}
          </button>
        )}
        <div className="walls-remaining">
          <div>P1 Walls: {displayState.walls_remaining[0]}</div>
          <div>P2 Walls: {displayState.walls_remaining[1]}</div>
        </div>
        <div className="current-player">
          Current: Player {displayState.current_player + 1}
        </div>
      </div>

      <div 
        className="game-board"
        data-testid="game-board"
        style={{
          width: boardSize * cellSize,
          height: boardSize * cellSize,
        }}
      >
        {Array.from({ length: boardSize }, (_, y) =>
          Array.from({ length: boardSize }, (_, x) => renderCell(x, y))
        )}

        {displayState.walls.map(renderWall)}

        {wallPlacementMode && Array.from({ length: boardSize - 1 }, (_, y) =>
          Array.from({ length: boardSize - 1 }, (_, x) => (
            <React.Fragment key={`wall-slots-${x}-${y}`}>
              {wallOrientation === 'horizontal' && renderWallSlot(x, y, 'horizontal')}
              {wallOrientation === 'vertical' && renderWallSlot(x, y, 'vertical')}
            </React.Fragment>
          ))
        )}
      </div>

      {displayState.winner !== null && (
        <div className="game-over">
          <h2>Game Over!</h2>
          <p>Player {displayState.winner + 1} Wins!</p>
        </div>
      )}
    </div>
  );
};