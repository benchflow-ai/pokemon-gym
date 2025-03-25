# Claude Pokemon Player

## Project Structure

- `run.py`: Main entry point for the application
- `emulator_setup_rom.py`: Handles setting up the Morph Cloud environment with BizHawk emulator
- `claude.py`: Contains the Claude gameplay logic and memory system

## Prerequisites

- A Morph Cloud API key (get one at [cloud.morph.so](https://cloud.morph.so))
- An Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))
- A Pokemon ROM file (.gb or .gbc format for Game Boy/Game Boy Color games)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/benchflow-ai/pokemon-gym.git
cd pokemon-gym
```

2. Install the required dependencies:

```bash
pip install morphcloud anthropic dotenv
```

3. Create a `.env` file in the project root with your API keys:

```
MORPH_API_KEY=your_morph_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL=claude-3-7-sonnet-20250219
ROM_PATH=your_rom_path
```

## Usage

### Setting up the Emulator Only

To set up the emulator without starting Claude:

```bash
python run.py --rom $ROM_PATH --setup-only
```

This will:

1. Create a Morph Cloud VM with a desktop environment
2. Install the BizHawk emulator
3. Upload and configure your ROM
4. Provide a URL to access the emulator via your browser

### Running the Full Claude Player

To set up the emulator and let Claude play the game:

```bash
python run.py --rom path/to/pokemon_game.gbc
```

Additional options:

- `--max-turns 200`: Set a maximum number of turns (default: 100)
- `--snapshot snapshot_id`: Use an existing Morph Cloud snapshot instead of creating a new environment

### Using an Existing Snapshot

If you've already set up the emulator and want to continue from a snapshot:

```bash
python run.py --snapshot your_snapshot_id
```

## How It Works

1. **Emulator Setup**: The project creates a cloud VM with a desktop environment, BizHawk emulator, and a web-based VNC client.

2. **Screenshot Analysis**: Claude receives screenshots of the game and analyzes them to understand the current game state.

3. **Decision Making**: Claude decides which buttons to press based on its understanding of the game and Pokemon mechanics.

4. **Memory System**: Claude maintains a memory system to remember important information about the game, such as:

   - Items collected
   - NPCs encountered
   - Locations visited
   - Pokemon in the team and their stats
   - Active quests
   - Game mechanics

5. **Continuous Play**: Claude plays through the game turn by turn, with each turn consisting of:
   - Receiving a screenshot
   - Deciding on actions
   - Sending button inputs
   - Observing the results

## Output Locations

- **Logs**: Log files are saved in the `logs` directory
- **Screenshots**: Screenshots of the game are saved in the `screenshots` directory
- **Data**: Conversation history and memory data are saved in the `data` directory
- **Emulator Access**: When running, the script will output a URL where you can view the emulator in your browser
