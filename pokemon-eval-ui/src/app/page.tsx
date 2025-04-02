'use client';

import { useEffect, useState, useCallback } from 'react';
import { Box, Container, Typography } from '@mui/material';
import GameDisplay from '@/components/GameDisplay';
import AIActionLog from '@/components/AIActionLog';
import GameStatus from '@/components/GameStatus';
import type { GameState, AIAction, GameStateUpdate } from '@/types';

const WEBSOCKET_URL = 'ws://localhost:8080/ws';
const API_BASE_URL = 'http://localhost:8080';

const initialGameState: GameState = {
  screenshot_base64: '',
  location: 'Loading...',
  coordinates: [0, 0],
  valid_moves: [],
  money: 0,
  badges: 0,
  pokemons: [],
  inventory: [],
};

export default function Home() {
  const [gameState, setGameState] = useState<GameState>(initialGameState);
  const [actions, setActions] = useState<AIAction[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const connectWebSocket = useCallback(() => {
    const websocket = new WebSocket(WEBSOCKET_URL);

    websocket.onopen = () => {
      setConnectionError(null);
    };

    websocket.onmessage = (event) => {
      const data: GameStateUpdate = JSON.parse(event.data);
      setGameState(data.state);
      const action = data.action;
      if (action && 'type' in action && 'details' in action) {
        setActions(prev => [action as AIAction, ...prev].slice(0, 50));
      }
    };

    websocket.onclose = () => {
      setConnectionError('WebSocket connection closed. Reconnecting...');
      setTimeout(connectWebSocket, 5000);
    };

    websocket.onerror = () => {
      setConnectionError('Failed to connect to game server');
      websocket.close();
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  useEffect(() => {
    const initializeGame = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/initialize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            headless: true,
            sound: false,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to initialize game');
        }

        const data = await response.json();
        setGameState(data);
      } catch (error) {
        setConnectionError('Failed to initialize game');
      }
    };

    initializeGame();
    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [connectWebSocket]);

  return (
    <Box
      component="main"
      sx={{
        minHeight: '100vh',
        background: '#000',
        display: 'flex',
        flexDirection: 'column',
        p: 2,
      }}
    >
      {/* Header */}
      <Box sx={{
        textAlign: 'center',
        mb: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
      }}>
        <Typography
          variant="h1"
          sx={{
            fontSize: '24px',
            color: '#fff',
            textShadow: '2px 2px 0px rgba(0,0,0,0.5)',
            fontFamily: 'inherit',
          }}
        >
          Pokémon Gym
        </Typography>
        {/* Control buttons */}
        <Box sx={{
          display: 'flex',
          gap: 1,
        }}>
          {['↑', 'A', '↓', '←', '→', 'B'].map((button) => (
            <Box
              key={button}
              sx={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                bgcolor: '#333',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#666',
                fontSize: '14px',
                fontFamily: 'inherit',
              }}
            >
              {button}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Main content */}
      <Box sx={{ 
        flex: 1,
        display: 'flex',
        gap: 2,
      }}>
        {/* Left: Claude's thinking process */}
        <Box sx={{ 
          width: '400px',
          bgcolor: '#000',
          border: '1px solid #333',
          borderRadius: 1,
          overflow: 'hidden',
        }}>
          <Box sx={{
            p: 1,
            borderBottom: '1px solid #333',
            color: '#4fd1c5',
            fontSize: '14px',
            fontFamily: 'inherit',
          }}>
            Claude
          </Box>
          <AIActionLog actions={actions} />
        </Box>

        {/* Center: Game screen */}
        <Box sx={{ 
          flex: 1,
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: -1,
            left: -1,
            right: -1,
            bottom: -1,
            border: '1px solid #4fd1c5',
            borderRadius: 1,
            pointerEvents: 'none',
          },
        }}>
          <GameDisplay gameState={gameState} />
        </Box>

        {/* Right: Stream chat */}
        <Box sx={{ 
          width: '300px',
          bgcolor: '#000',
          border: '1px solid #333',
          borderRadius: 1,
          p: 1,
          color: '#fff',
          fontSize: '14px',
          fontFamily: 'inherit',
        }}>
          Stream Chat
        </Box>
      </Box>

      {/* Status bar */}
      <Box sx={{
        mt: 2,
        bgcolor: '#000',
        border: '1px solid #333',
        borderRadius: 1,
      }}>
        <GameStatus gameState={gameState} />
      </Box>

      {/* Error message */}
      {connectionError && (
        <Box
          sx={{
            position: 'fixed',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            bgcolor: 'rgba(255, 0, 0, 0.1)',
            color: '#ff6b6b',
            border: '1px solid #ff6b6b',
            borderRadius: 1,
            p: 1,
            fontSize: '12px',
            fontFamily: 'inherit',
          }}
        >
          {connectionError}
        </Box>
      )}
    </Box>
  );
} 