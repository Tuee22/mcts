import React from 'react';
import { useGameStore } from '../store/gameStore';
import './MoveHistory.css';

export const MoveHistory: React.FC = () => {
  const { gameState, selectedHistoryIndex, setSelectedHistoryIndex } = useGameStore();

  if (!gameState) {
    return <div className="move-history-empty">No moves yet</div>;
  }

  const handleMoveClick = (index: number) => {
    if (index === gameState.move_history.length) {
      setSelectedHistoryIndex(null);
    } else {
      setSelectedHistoryIndex(index);
    }
  };


  return (
    <div className="move-history-container">
      <div className="move-history-header">
        <h3>Move History</h3>
        {selectedHistoryIndex !== null && (
          <button 
            className="retro-btn-small"
            onClick={() => setSelectedHistoryIndex(null)}
          >
            Current
          </button>
        )}
      </div>
      
      <div className="move-history-list">
        <div 
          className={`move-item ${selectedHistoryIndex === null ? 'selected' : ''}`}
          onClick={() => handleMoveClick(gameState.move_history.length)}
        >
          <span className="move-number">Start</span>
          <span className="move-notation">Initial position</span>
        </div>
        
        {gameState.move_history.map((move, index) => {
          const isSelected = selectedHistoryIndex === index;
          const moveNum = index + 1;
          const isWhiteMove = index % 2 === 0;
          
          return (
            <div
              key={index}
              className={`move-item ${isSelected ? 'selected' : ''} ${isWhiteMove ? 'white-move' : 'black-move'}`}
              onClick={() => handleMoveClick(index)}
            >
              <span className="move-number">
                {isWhiteMove && `${Math.floor(moveNum / 2) + 1}.`}
              </span>
              <span className="move-notation">
                {move.notation}
              </span>
              {move.type === 'wall' && <span className="move-type-icon">🧱</span>}
              {move.type === 'move' && <span className="move-type-icon">👣</span>}
            </div>
          );
        })}
        
        {gameState.winner !== null && (
          <div className="move-item game-result">
            <span className="result-text">
              {gameState.winner === 0 ? '1-0' : '0-1'}
            </span>
            <span className="winner-text">
              Player {gameState.winner + 1} wins!
            </span>
          </div>
        )}
      </div>
      
      <div className="move-history-controls">
        <button
          className="retro-btn-small"
          onClick={() => setSelectedHistoryIndex(0)}
          disabled={!gameState.move_history.length}
        >
          ⏮
        </button>
        <button
          className="retro-btn-small"
          onClick={() => {
            if (selectedHistoryIndex === null) {
              setSelectedHistoryIndex(gameState.move_history.length - 1);
            } else if (selectedHistoryIndex > 0) {
              setSelectedHistoryIndex(selectedHistoryIndex - 1);
            }
          }}
          disabled={selectedHistoryIndex === 0}
        >
          ◀
        </button>
        <button
          className="retro-btn-small"
          onClick={() => {
            if (selectedHistoryIndex !== null && selectedHistoryIndex < gameState.move_history.length - 1) {
              setSelectedHistoryIndex(selectedHistoryIndex + 1);
            } else {
              setSelectedHistoryIndex(null);
            }
          }}
          disabled={selectedHistoryIndex === null}
        >
          ▶
        </button>
        <button
          className="retro-btn-small"
          onClick={() => setSelectedHistoryIndex(null)}
          disabled={selectedHistoryIndex === null}
        >
          ⏭
        </button>
      </div>
    </div>
  );
};