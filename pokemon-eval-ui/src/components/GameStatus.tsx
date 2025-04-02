import { Box } from '@mui/material';
import type { GameState } from '@/types';

interface GameStatusProps {
  gameState: GameState;
}

export default function GameStatus({ gameState }: GameStatusProps) {
  return (
    <Box sx={{ 
      p: 1,
      color: '#fff',
      fontSize: '12px',
      bgcolor: '#000',
      fontFamily: 'inherit',
    }}>
      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(6, 1fr)',
        gap: 1,
        alignItems: 'center',
      }}>
        {gameState.pokemons.map((pokemon, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
              p: 0.5,
              border: '1px solid #333',
              borderRadius: 0.5,
              fontFamily: 'inherit',
            }}
          >
            <Box sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 1,
            }}>
              <Box sx={{ color: '#4fd1c5', fontFamily: 'inherit' }}>{pokemon.nickname}</Box>
              <Box sx={{ color: '#fbbf24', fontFamily: 'inherit' }}>Lv.{pokemon.level}</Box>
            </Box>
            <Box sx={{ color: '#f472b6', fontFamily: 'inherit' }}>
              HP: {pokemon.hp.current}/{pokemon.hp.max}
            </Box>
          </Box>
        ))}
      </Box>

      <Box sx={{ 
        mt: 1,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderTop: '1px solid #333',
        pt: 1,
        fontFamily: 'inherit',
      }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Box sx={{ fontFamily: 'inherit' }}>
            <Box component="span" sx={{ color: '#4fd1c5', fontFamily: 'inherit' }}>Location: </Box>
            {gameState.location}
          </Box>
          <Box sx={{ fontFamily: 'inherit' }}>
            <Box component="span" sx={{ color: '#4fd1c5', fontFamily: 'inherit' }}>Coords: </Box>
            {`(${gameState.coordinates[0]}, ${gameState.coordinates[1]})`}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Box sx={{ fontFamily: 'inherit' }}>
            <Box component="span" sx={{ color: '#fbbf24', fontFamily: 'inherit' }}>Money: </Box>
            ₽{gameState.money}
          </Box>
          <Box sx={{ fontFamily: 'inherit' }}>
            <Box component="span" sx={{ color: '#fbbf24', fontFamily: 'inherit' }}>Badges: </Box>
            {gameState.badges}
          </Box>
        </Box>
      </Box>
    </Box>
  );
} 