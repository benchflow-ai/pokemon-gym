import React from 'react';

interface Pokemon {
  nickname: string;
  species: string;
  level: number;
  hp: {
    current: number;
    max: number;
  };
}

interface GameStatusProps {
  location: string;
  coordinates: [number, number];
  team: Pokemon[];
  money: number;
  badges: number;
}

const GameStatus: React.FC<GameStatusProps> = ({
  location,
  coordinates,
  team,
  money,
  badges,
}) => {
  return (
    <div className="w-full bg-gray-900 rounded-lg overflow-hidden border-4 border-gray-700 p-4">
      <div className="grid grid-cols-3 gap-4">
        {/* Location Info */}
        <div className="space-y-2">
          <h3 className="text-gray-400 font-pixel text-sm">Location</h3>
          <div className="bg-gray-800 rounded p-2">
            <p className="text-white font-pixel text-xs">{location}</p>
            <p className="text-gray-400 font-pixel text-xs">
              ({coordinates[0]}, {coordinates[1]})
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="space-y-2">
          <h3 className="text-gray-400 font-pixel text-sm">Stats</h3>
          <div className="bg-gray-800 rounded p-2 space-y-1">
            <p className="text-white font-pixel text-xs">
              Money: ${money}
            </p>
            <p className="text-white font-pixel text-xs">
              Badges: {badges}
            </p>
          </div>
        </div>

        {/* Team */}
        <div className="space-y-2">
          <h3 className="text-gray-400 font-pixel text-sm">Team</h3>
          <div className="bg-gray-800 rounded p-2 space-y-1 max-h-20 overflow-y-auto">
            {team.map((pokemon, index) => (
              <div key={index} className="flex justify-between items-center">
                <span className="text-white font-pixel text-xs">
                  {pokemon.nickname} (Lv.{pokemon.level})
                </span>
                <span className="text-green-400 font-pixel text-xs">
                  HP: {pokemon.hp.current}/{pokemon.hp.max}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameStatus; 