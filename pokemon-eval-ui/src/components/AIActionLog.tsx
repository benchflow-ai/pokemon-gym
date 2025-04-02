import { Box } from '@mui/material';
import type { AIAction } from '@/types';

interface AIActionLogProps {
  actions: AIAction[];
}

export default function AIActionLog({ actions }: AIActionLogProps) {
  const formatDetails = (action: AIAction) => {
    if (typeof action.details === 'string') {
      return action.details;
    }
    if (action.type === 'press_key' && 'button' in action.details) {
      return `Button: ${action.details.button}`;
    }
    if (action.type === 'wait' && 'frames' in action.details) {
      return `Frames: ${action.details.frames}`;
    }
    return JSON.stringify(action.details, null, 2);
  };

  return (
    <Box
      sx={{
        height: 'calc(100% - 32px)',
        overflow: 'auto',
        p: 1,
        color: '#4fd1c5',
        fontSize: '12px',
        bgcolor: '#000',
        fontFamily: 'inherit',
        '&::-webkit-scrollbar': {
          width: '4px',
        },
        '&::-webkit-scrollbar-track': {
          background: '#000',
        },
        '&::-webkit-scrollbar-thumb': {
          background: '#333',
          borderRadius: '2px',
        },
      }}
    >
      {actions.map((action, index) => (
        <Box
          key={index}
          sx={{
            mb: 1.5,
            '&:last-child': {
              mb: 0,
            },
          }}
        >
          {/* Reasoning process */}
          {action.reasoning && (
            <Box sx={{ mb: 1 }}>
              <Box sx={{ 
                color: '#666',
                mb: 0.5,
                fontSize: '11px',
                fontFamily: 'inherit',
              }}>
                {'<thinking>'}
              </Box>
              {action.reasoning.split('\n').map((line, i) => (
                <Box 
                  key={i} 
                  sx={{ 
                    pl: 1,
                    color: '#e2e8f0',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    lineHeight: 1.4,
                    fontFamily: 'inherit',
                  }}
                >
                  {line}
                </Box>
              ))}
              <Box sx={{ 
                color: '#666',
                mt: 0.5,
                fontSize: '11px',
                fontFamily: 'inherit',
              }}>
                {'</thinking>'}
              </Box>
            </Box>
          )}

          {/* Action */}
          <Box sx={{ 
            color: '#fbbf24',
            fontSize: '11px',
            fontFamily: 'inherit',
          }}>
            Using tool: {action.type}
          </Box>
          <Box 
            sx={{ 
              pl: 1,
              color: '#e2e8f0',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: 1.4,
              fontFamily: 'inherit',
            }}
          >
            {formatDetails(action)}
          </Box>
        </Box>
      ))}
    </Box>
  );
} 