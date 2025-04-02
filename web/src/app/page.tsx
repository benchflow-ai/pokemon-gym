'use client';

import React from 'react';
import { io } from 'socket.io-client';
import GameScreen from '@/components/GameScreen';
import AILog from '@/components/AILog';
import GameStatus from '@/components/GameStatus';

export default function Home() {
  const [gameState, setGameState] = React.useState({
    location: '',
    coordinates: [0, 0] as [number, number],
    team: [],
    money: 0,
    badges: 0,
  });

  const [logs, setLogs] = React.useState<Array<{
    type: 'thinking' | 'action' | 'error';
    message: string;
    timestamp: string;
  }>>([]);

  const [screenData, setScreenData] = React.useState<string>('');
  const [isConnected, setIsConnected] = React.useState(false);
  const [streamUrl, setStreamUrl] = React.useState<string>('');

  React.useEffect(() => {
    const socket = io('http://localhost:8080');

    socket.on('connect', () => {
      setIsConnected(true);
      setLogs(prev => [...prev, {
        type: 'action',
        message: 'Connected to server',
        timestamp: new Date().toISOString()
      }]);
      
      // Initialize game environment
      fetch('http://localhost:8080/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          headless: true,
          sound: false
        })
      }).then(response => response.json())
        .then(data => {
          setLogs(prev => [...prev, {
            type: 'action',
            message: 'Game environment initialized',
            timestamp: new Date().toISOString()
          }]);
          // Set up video stream URL
          setStreamUrl('http://localhost:8080/video-stream');
        })
        .catch(error => {
          setLogs(prev => [...prev, {
            type: 'error',
            message: `Failed to initialize game: ${error.message}`,
            timestamp: new Date().toISOString()
          }]);
        });
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      setLogs(prev => [...prev, {
        type: 'error',
        message: 'Disconnected from server',
        timestamp: new Date().toISOString()
      }]);
    });

    socket.on('gameState', (state) => {
      setGameState(state);
    });

    socket.on('screenshot', (data) => {
      setScreenData(data);
    });

    socket.on('aiLog', (log) => {
      setLogs(prev => [...prev, {
        type: log.type,
        message: log.message,
        timestamp: new Date().toISOString()
      }]);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-pixel text-white">Claude Plays Pokémon</h1>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm font-pixel text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </header>

        {/* Main content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Game screen */}
          <div className="lg:col-span-2 aspect-video">
            <GameScreen 
              imageData={screenData} 
              isLive={isConnected} 
              streamUrl={streamUrl}
            />
          </div>

          {/* Game status */}
          <div className="lg:col-span-1">
            <GameStatus 
              location={gameState.location}
              coordinates={gameState.coordinates}
              team={gameState.team}
              money={gameState.money}
              badges={gameState.badges}
            />
          </div>
        </div>

        {/* AI Log */}
        <div className="mt-6">
          <AILog logs={logs} />
        </div>
      </div>
    </main>
  );
}
