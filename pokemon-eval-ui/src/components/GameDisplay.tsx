import { Box, Paper } from '@mui/material';
import type { GameState } from '@/types';

interface GameDisplayProps {
  gameState: GameState;
}

export default function GameDisplay({ gameState }: GameDisplayProps) {
  return (
    <Paper
      elevation={3}
      sx={{
        overflow: 'hidden',
        background: '#000',
        border: '2px solid rgba(0, 255, 255, 0.3)',
        borderRadius: '8px',
        position: 'relative',
        maxWidth: '720px',
        margin: '0 auto',
        '&::after': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          boxShadow: 'inset 0 0 50px rgba(0, 255, 255, 0.1)',
          pointerEvents: 'none',
        },
      }}
    >
      <Box
        sx={{
          position: 'relative',
          width: '100%',
          paddingTop: 'calc(144 / 160 * 100%)', // 保持 Game Boy 的 160:144 宽高比
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(45deg, rgba(0, 255, 255, 0.1) 0%, transparent 100%)',
            pointerEvents: 'none',
            zIndex: 1,
          },
        }}
      >
        <Box
          component="img"
          src={`data:image/png;base64,${gameState.screenshot_base64}`}
          alt="Pokemon Game Screen"
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            imageRendering: 'pixelated',
          }}
        />
      </Box>
    </Paper>
  );
} 