import React, { useEffect, useRef } from 'react';
import classNames from 'classnames';

interface GameScreenProps {
  imageData?: string;
  isLive?: boolean;
  streamUrl?: string;
}

const GameScreen: React.FC<GameScreenProps> = ({ imageData, isLive = false, streamUrl }) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current && streamUrl) {
      videoRef.current.srcObject = new MediaStream();
    }
  }, [streamUrl]);

  return (
    <div className="relative w-full h-full flex items-center justify-center bg-gray-900 rounded-lg overflow-hidden border-4 border-gray-700">
      {streamUrl ? (
        <div className="relative w-full h-full">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-contain"
          />
          {isLive && (
            <div className="absolute top-4 right-4 flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
              <span className="text-white text-xs font-pixel uppercase">Live</span>
            </div>
          )}
        </div>
      ) : imageData ? (
        <div className="relative w-full h-full">
          <img
            src={`data:image/png;base64,${imageData}`}
            alt="Pokemon Game Screen"
            className="w-full h-full object-contain pixelated"
            style={{ imageRendering: 'pixelated' }}
          />
          {isLive && (
            <div className="absolute top-4 right-4 flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
              <span className="text-white text-xs font-pixel uppercase">Live</span>
            </div>
          )}
        </div>
      ) : (
        <div className="text-gray-500 font-pixel text-center">
          Waiting for game screen...
        </div>
      )}
    </div>
  );
};

export default GameScreen; 