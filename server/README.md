# Pokemon Evaluator Server

This module provides a FastAPI server that exposes the Pokemon emulator functionality through a RESTful API. The server allows agents to interact with the Pokemon game remotely.

## Overview

The server provides the following functionality:
- Initialize a Pokemon game environment
- Take actions (press buttons, wait)
- Retrieve game state information
- Check environment status
- Stop the environment

## Usage

### Starting the Server

Start the server using the provided script:

```bash
python evaluator_server.py --host 0.0.0.0 --port 8000 --rom pokemon.gb
```

Command-line arguments:
- `--host`: Host address to bind the server to (default: 0.0.0.0)
- `--port`: Port to listen on (default: 8000)
- `--rom`: Path to the Pokemon ROM file (default: pokemon.gb)
- `--reload`: Enable auto-reload for development

### API Endpoints

#### Initialize Environment

```http
POST /initialize
```

Request body:
```json
{
  "headless": true,
  "sound": false
}
```

Response:
```json
{
  "memory_info": { ... },
  "screenshot_base64": "base64_encoded_image",
  "location": "PALLET TOWN",
  "coordinates": [5, 6],
  "pokemons": [ ... ],
  "collision_map": "text representation of collision map",
  "valid_moves": ["up", "down", "left", "right"],
  "step_number": 0,
  "execution_time": 0.0
}
```

#### Take Action

```http
POST /action
```

Request body (press buttons):
```json
{
  "action_type": "press_key",
  "keys": ["a"],
  "wait": true
}
```

Request body (wait):
```json
{
  "action_type": "wait",
  "frames": 60
}
```

Response: Same format as the initialize endpoint.

#### Get Status

```http
GET /status
```

Response:
```json
{
  "status": "running",
  "steps_taken": 10
}
```

#### Stop Environment

```http
POST /stop
```

Response:
```json
{
  "status": "stopped"
}
```

## Client Usage

The `agent/client.py` module provides a client for interacting with the server:

```python
from agent.client import PokemonServerClient

# Create client
client = PokemonServerClient(server_url="http://localhost:8000")

# Initialize environment
state = client.initialize(headless=True, sound=False)

# Press buttons
state = client.press_buttons(keys=["a"])

# Wait for frames
state = client.wait(frames=30)

# Stop the environment
client.stop()
```

## Example Agent

An example agent that interacts with the server is provided in `agent/server_agent.py`. Run it with:

```bash
python -m agent.server_agent --steps 10 --server http://localhost:8000
``` 