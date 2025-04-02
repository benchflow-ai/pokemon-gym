export interface Pokemon {
  nickname: string;
  species: string;
  level: number;
  hp: {
    current: number;
    max: number;
  };
}

export interface InventoryItem {
  item: string;
  quantity: number;
}

export interface GameState {
  screenshot_base64: string;
  location: string;
  coordinates: [number, number];
  valid_moves: string[];
  money: number;
  badges: number;
  dialog?: string;
  pokemons: Pokemon[];
  inventory: InventoryItem[];
  collision_map?: string;
}

export interface AIAction {
  type: 'press_key' | 'wait';
  details: {
    button?: string;
    frames?: number;
  };
  reasoning: string;
  timestamp: number;
}

export interface GameStateUpdate {
  state: GameState;
  action?: AIAction;
} 