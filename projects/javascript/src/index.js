///////////////////////
// Welcome to Cursor //
///////////////////////

/*
Step 1: Try generating a react component that lets you play tictactoe with Cmd+K or Ctrl+K on a new line.
  - Then integrate it into the code below and run with npm start

Step 2: Try highlighting all the code with your mouse, then hit Cmd+k or Ctrl+K. 
  - Instruct it to change the game in some way (e.g. add inline styles, add a start screen, make it 4x4 instead of 3x3)

Step 3: Hit Cmd+L or Ctrl+L and ask the chat what the code does

Step 4: To try out cursor on your own projects, go to the file menu (top left) and open a folder.
*/


import React, { useState, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom/client';

const GAME_WIDTH = 600;
const GAME_HEIGHT = 150;
const DINO_WIDTH = 40;
const DINO_HEIGHT = 40;
const CACTUS_WIDTH = 20;
const CACTUS_HEIGHT = 40;
const GROUND_HEIGHT = 20;

function App() {
  const [dinoY, setDinoY] = useState(GAME_HEIGHT - DINO_HEIGHT - GROUND_HEIGHT);
  const [cactusX, setCactusX] = useState(GAME_WIDTH);
  const [isJumping, setIsJumping] = useState(false);
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(0);
  const [gameOver, setGameOver] = useState(false);

  const jump = useCallback(() => {
    if (!isJumping && !gameOver) {
      setIsJumping(true);
      let jumpHeight = 0;
      const jumpInterval = setInterval(() => {
        if (jumpHeight < 60) {
          setDinoY(y => y - 3);
          jumpHeight += 3;
        } else if (jumpHeight < 120) {
          setDinoY(y => y + 3);
          jumpHeight += 3;
        } else {
          clearInterval(jumpInterval);
          setIsJumping(false);
          setDinoY(GAME_HEIGHT - DINO_HEIGHT - GROUND_HEIGHT);
        }
      }, 20);
    }
  }, [isJumping, gameOver]);

  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.code === 'Space') {
        jump();
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => {
      window.removeEventListener('keydown', handleKeyPress);
    };
  }, [jump]);

  useEffect(() => {
    if (!gameOver) {
      const gameInterval = setInterval(() => {
        setCactusX(x => {
          if (x <= -CACTUS_WIDTH) {
            setScore(score => score + 1);
            return GAME_WIDTH;
          }
          return x - 5;
        });
      }, 20);

      return () => {
        clearInterval(gameInterval);
      };
    }
  }, [gameOver]);

  useEffect(() => {
    if (
      cactusX < DINO_WIDTH &&
      cactusX + CACTUS_WIDTH > 0 &&
      dinoY + DINO_HEIGHT > GAME_HEIGHT - CACTUS_HEIGHT - GROUND_HEIGHT
    ) {
      setGameOver(true);
      if (score > highScore) {
        setHighScore(score);
      }
    }
  }, [cactusX, dinoY, score, highScore]);

  const restartGame = () => {
    setGameOver(false);
    setScore(0);
    setCactusX(GAME_WIDTH);
    setDinoY(GAME_HEIGHT - DINO_HEIGHT - GROUND_HEIGHT);
  };

  return (
    <div className="App" style={{ fontFamily: 'Press Start 2P, cursive' }}>
      <h1 style={{ textAlign: 'center', color: '#4a4a4a' }}>Dino Runner</h1>
      <div style={{
        width: GAME_WIDTH,
        height: GAME_HEIGHT,
        border: '2px solid #4a4a4a',
        position: 'relative',
        overflow: 'hidden',
        margin: '0 auto',
      }}>
        <div style={{
          width: DINO_WIDTH,
          height: DINO_HEIGHT,
          backgroundColor: '#4a4a4a',
          position: 'absolute',
          bottom: GROUND_HEIGHT,
          left: 20,
          transform: `translateY(${GAME_HEIGHT - dinoY - DINO_HEIGHT - GROUND_HEIGHT}px)`,
        }} />
        <div style={{
          width: CACTUS_WIDTH,
          height: CACTUS_HEIGHT,
          backgroundColor: '#4a4a4a',
          position: 'absolute',
          bottom: GROUND_HEIGHT,
          left: cactusX,
        }} />
        <div style={{
          width: '100%',
          height: GROUND_HEIGHT,
          backgroundColor: '#4a4a4a',
          position: 'absolute',
          bottom: 0,
        }} />
      </div>
      <div style={{ textAlign: 'center', marginTop: '20px' }}>
        <p>Score: {score}</p>
        <p>High Score: {highScore}</p>
        {gameOver && (
          <button onClick={restartGame} style={{
            fontFamily: 'Press Start 2P, cursive',
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#4a4a4a',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
          }}>
            Restart
          </button>
        )}
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);