#!/usr/bin/env python3
"""
Claude Pokemon Player - Let Claude play Pokemon games using Morph Cloud's emulator.
This script handles Claude's ability to play the game and interfaces with the emulator.
"""

import os
import sys
import time
import base64
import logging
import json
import argparse
from io import BytesIO
from datetime import datetime
import requests
import anthropic
from dotenv import load_dotenv
from morphcloud.api import MorphCloudClient

# Create necessary directories
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Configure logging to write to logs directory
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/claude_pokemon_player.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")

# Initialize Anthropic client
claude = anthropic.Client(api_key=ANTHROPIC_API_KEY)

# Global variables for game state
instance = None
chat_history = []
memory_items = []
next_memory_id = 1
turn_count = 0
structured_memory = {
    "items": [],
    "npcs": [],
    "locations": [],
    "pokemons": [],
    "quests": [],
    "game_mechanics": [],
    "stats": []
}

def capture_screenshot(instance):
    """
    Capture a screenshot of the current game state.
    
    Returns:
        Dict containing the screenshot as a base64 encoded string.
    """
    logging.info("Capturing screenshot")
    
    # Command to capture screenshot - ensure ImageMagick is installed
    screenshot_command = """
    if ! command -v import &> /dev/null; then
        apt-get update -qq && apt-get install -y -qq imagemagick
    fi
    
    # Make sure the display is correctly set
    export DISPLAY=:1
    
    # Make sure screenshot directory exists
    mkdir -p /root/screenshots
    
    # Try to capture screenshot
    import -window root /tmp/screenshot.png
    
    # Check if the file exists and has size
    if [ -s /tmp/screenshot.png ]; then
        cat /tmp/screenshot.png | base64
        exit 0
    else
        # If import fails, try scrot
        if ! command -v scrot &> /dev/null; then
            apt-get update -qq && apt-get install -y -qq scrot
        fi
        
        # Try scrot
        scrot -o /tmp/screenshot.png
        
        # Check again
        if [ -s /tmp/screenshot.png ]; then
            cat /tmp/screenshot.png | base64
            exit 0
        else
            echo "Failed to capture screenshot with import or scrot" >&2
            exit 1
        fi
    fi
    """
    
    # Execute the screenshot command
    result = instance.exec(screenshot_command)
    
    if result.exit_code != 0 or not result.stdout:
        logging.error(f"Error capturing screenshot: {result.stderr}")
        raise RuntimeError(f"Error capturing screenshot: {result.stderr}")
    
    try:
        # Directly use the base64 encoded image
        image_data = result.stdout
        mime_type = "image/png"
        
        # Save a local copy of the screenshot in the screenshots directory
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            local_path = f"screenshots/turn_{turn_count}_{timestamp}.png"
            with open(local_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            logging.info(f"Saved local screenshot to {local_path}")
        except Exception as e:
            logging.warning(f"Could not save local screenshot: {e}")
        
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": image_data
            }
        }
    except Exception as e:
        logging.error(f"Error processing screenshot: {e}")
        raise

def send_inputs(instance, inputs):
    """
    Send a sequence of button inputs to the emulator.
    
    Args:
        inputs: String of inputs to send (e.g., "A B Up Down Left Right")
        
    Returns:
        True if successful, False otherwise.
    """
    logging.info(f"Sending inputs: {inputs}")
    
    # Convert inputs to key sequences
    key_mapping = {
        "A": "a",
        "B": "b",
        "Start": "Return",
        "Select": "BackSpace",
        "Up": "Up",
        "Down": "Down",
        "Left": "Left",
        "Right": "Right"
    }
    
    # Process each input
    for input_name in inputs.split():
        if input_name in key_mapping:
            key = key_mapping[input_name]
            
            # Press and release the key
            cmd = f"DISPLAY=:1 xdotool key {key}"
            result = instance.exec(cmd)
            
            if result.exit_code != 0:
                logging.error(f"Error sending input {input_name}: {result.stderr}")
                return False
            
            # Small delay between inputs
            instance.exec("sleep 0.2")
        else:
            logging.warning(f"Unknown input: {input_name}")
    
    return True

def add_memory_item(item, category=None, metadata=None):
    """
    Add an item to memory.
    
    Args:
        item: Information to remember
        category: Optional category for organizing memory
        metadata: Optional metadata about the item
        
    Returns:
        Dictionary containing the added memory item
    """
    global next_memory_id, memory_items, structured_memory
    
    if metadata is None:
        metadata = {}
    
    # Create memory item
    memory_item = {
        'id': next_memory_id,
        'item': item,
        'category': category,
        'added_at': turn_count,
        'priority': metadata.get('priority', 0),
        'confidence': metadata.get('confidence', 1.0),
        'context': metadata.get('context', {}),
        'version': 1
    }
    
    # Increment memory ID counter
    next_memory_id += 1
    
    # Add to flat memory list
    memory_items.append(memory_item)
    
    # Add to structured memory if category is specified
    if category and category in structured_memory:
        structured_memory[category].append(memory_item)
    
    logging.info(f"Added memory item: {item} (category: {category}, id: {memory_item['id']})")
    
    return memory_item

def search_memory(query, category=None, min_priority=0, min_confidence=0.0):
    """
    Search memory items.
    
    Args:
        query: Text to search for in memory items
        category: Optional category to search within
        min_priority: Minimum priority level (0-10)
        min_confidence: Minimum confidence level (0.0-1.0)
        
    Returns:
        List of matching memory items
    """
    results = []
    source = structured_memory[category] if category else memory_items
    
    for item in source:
        # Apply filters
        if item['priority'] < min_priority or item['confidence'] < min_confidence:
            continue
            
        # Check if query is in item
        if query.lower() in item['item'].lower():
            results.append(item)
    
    return results

def get_system_prompt():
    """
    Generate a system prompt for Claude.
    
    Returns:
        String containing the system prompt
    """
    button_rules = """
Input Button Notation:
- A: Press the A button (action, confirm)
- B: Press the B button (cancel, back)
- Start: Press the Start button (menu)
- Select: Press the Select button
- Up: Press the Up direction
- Down: Press the Down direction
- Left: Press the Left direction
- Right: Press the Right direction

When giving multiple inputs, separate them with spaces, e.g., "Up A Down B".
"""
    
    return f"""You are an AI agent designed to play Pokemon games. You will be given screenshots from a Pokemon game and must use the provided tools to interact with the game. You are also given tools to give yourself a long term memory, as you can only keep a few messages in your short term memory. Your ultimate objective is to defeat the game by becoming the Pokemon champion.

<notation>
{button_rules}
</notation>

Always use the tools provided to you to interact with the game.
Analyze each screenshot carefully to understand the current game state.
Think strategically about which Pokemon to use, which moves to select, and when to use items.
Keep track of your Pokemon's health, status conditions, and move PP.
Remember type advantages and disadvantages when battling.
"""

def play_turn():
    """Play one turn of the game with Claude making decisions."""
    global turn_count, chat_history, instance
    
    # Increment turn counter
    turn_count += 1
    logging.info(f"===== Turn {turn_count} =====")
    
    # Capture screenshot
    screenshot = capture_screenshot(instance)
    
    # Prepare user content with screenshot
    user_content = [
        {"type": "text", "text": f"Turn #{turn_count}"},
        screenshot
    ]
    
    # Add user message to chat history
    if len(chat_history) == 0:
        user_message = {"role": "user", "content": user_content}
    else:
        # Include memory summary if we have previous messages
        memory_summary = "Current Memory:\n"
        for category, items in structured_memory.items():
            if items:
                memory_summary += f"\n{category.upper()}:\n"
                for item in items:
                    memory_summary += f"- [{item['id']}] {item['item']}\n"
        
        user_message = {"role": "user", "content": [{"type": "text", "text": memory_summary}] + user_content}
    
    chat_history.append(user_message)
    
    # Define the tools for Claude to use
    tools = [
        {
            "name": "send_inputs",
            "description": "Send a sequence of button inputs to the game emulator.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "inputs": {
                        "type": "string",
                        "description": "Sequence of inputs, e.g., 'A B Up Down Left Right'"
                    }
                },
                "required": ["inputs"]
            }
        },
        {
            "name": "add_to_memory",
            "description": "Add a new item to memory with optional category.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Information to remember"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category for organizing memory (e.g., 'items', 'npcs', 'locations', 'pokemons', 'quests', 'game_mechanics', 'stats')"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority level (0-10, higher is more important)",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in the information (0.0-1.0)",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["item"]
            }
        },
        {
            "name": "search_memory",
            "description": "Search memory items by text and optional filters.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for in memory items"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category to search within"
                    },
                    "min_priority": {
                        "type": "integer",
                        "description": "Minimum priority level",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence level",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["query"]
            }
        }
    ]
    
    # Send request to Claude
    try:
        system_prompt = get_system_prompt()
        
        message = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=chat_history,
            tools=tools,
            thinking={"type": "enabled", "budget_tokens": 2000}
        )
        
        # Extract assistant's message content
        assistant_message = {"role": "assistant", "content": message.content}
        chat_history.append(assistant_message)
        
        # Process tool calls
        logging.info("Processing tool calls")
        for tool_use in message.model_dump().get("content", []):
            if tool_use.get("type") == "tool_use":
                tool_name = tool_use.get("name")
                tool_input = tool_use.get("input", {})
                
                logging.info(f"Executing tool: {tool_name}")
                
                if tool_name == "send_inputs":
                    inputs = tool_input.get("inputs", "")
                    send_inputs(instance, inputs)
                    
                    # Capture new screenshot after inputs
                    new_screenshot = capture_screenshot(instance)
                    
                    # Add tool result to chat history
                    chat_history.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Inputs sent: {inputs}"},
                            new_screenshot
                        ]
                    })
                
                elif tool_name == "add_to_memory":
                    item = tool_input.get("item", "")
                    category = tool_input.get("category")
                    priority = tool_input.get("priority", 0)
                    confidence = tool_input.get("confidence", 1.0)
                    
                    memory_item = add_memory_item(
                        item=item,
                        category=category,
                        metadata={
                            "priority": priority,
                            "confidence": confidence
                        }
                    )
                    
                    # Add tool result to chat history
                    chat_history.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Added to memory: {item} (id: {memory_item['id']})"}
                        ]
                    })
                
                elif tool_name == "search_memory":
                    query = tool_input.get("query", "")
                    category = tool_input.get("category")
                    min_priority = tool_input.get("min_priority", 0)
                    min_confidence = tool_input.get("min_confidence", 0.0)
                    
                    results = search_memory(
                        query=query,
                        category=category,
                        min_priority=min_priority,
                        min_confidence=min_confidence
                    )
                    
                    # Format results
                    results_text = f"Search results for '{query}':\n"
                    if results:
                        for item in results:
                            results_text += f"[{item['id']}] {item['item']}\n"
                    else:
                        results_text += "No results found."
                    
                    # Add tool result to chat history
                    chat_history.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": results_text}
                        ]
                    })
        
        # Save conversation history and game state to data directory every 5 turns
        if turn_count % 5 == 0:
            save_game_state()
            
        logging.info("Turn completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error during turn: {e}")
        return False

def save_game_state():
    """Save the conversation history and game state to the data directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save conversation history
    try:
        # Remove image data from chat_history to save space
        stripped_history = []
        for msg in chat_history:
            new_content = []
            if isinstance(msg.get('content', []), list):
                for item in msg['content']:
                    if isinstance(item, dict) and item.get('type') == 'image':
                        # Replace image data with a placeholder
                        new_content.append({
                            'type': 'text',
                            'text': f'[Image from turn {turn_count}]'
                        })
                    else:
                        new_content.append(item)
                stripped_msg = msg.copy()
                stripped_msg['content'] = new_content
                stripped_history.append(stripped_msg)
            else:
                stripped_history.append(msg)
        
        # Save to file
        history_path = f"data/chat_history_{timestamp}.json"
        with open(history_path, 'w') as f:
            json.dump(stripped_history, f, indent=2)
        logging.info(f"Saved chat history to {history_path}")
    except Exception as e:
        logging.error(f"Error saving chat history: {e}")
    
    # Save memory items
    try:
        memory_path = f"data/memory_{timestamp}.json"
        memory_data = {
            'memory_items': memory_items,
            'structured_memory': structured_memory,
            'next_memory_id': next_memory_id,
            'turn_count': turn_count
        }
        with open(memory_path, 'w') as f:
            json.dump(memory_data, f, indent=2)
        logging.info(f"Saved memory data to {memory_path}")
    except Exception as e:
        logging.error(f"Error saving memory data: {e}")

def play_game(instance_obj, max_turns=100):
    """
    Main function to let Claude play the Pokemon game.
    
    Args:
        instance_obj: The Morph Cloud instance running the emulator
        max_turns: Maximum number of game turns to play
    """
    global instance
    instance = instance_obj
    
    try:
        # Give the emulator time to start
        time.sleep(5)
        
        # Main game loop
        for _ in range(max_turns):
            success = play_turn()
            if not success:
                logging.error("Error during turn, stopping game")
                break
            
            # Small delay between turns
            time.sleep(2)
        
        # Create a final snapshot when done
        logging.info("Creating final snapshot")
        final_snapshot = instance.snapshot()
        final_snapshot.set_metadata({
            "type": "claude-pokemon-player-complete",
            "description": f"Claude Pokemon Player with {turn_count} turns played",
            "turn_count": str(turn_count),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        logging.info(f"Final snapshot created: {final_snapshot.id}")
        print(f"Final snapshot created: {final_snapshot.id}")
        
        # Save final game state
        save_game_state()
        
        return final_snapshot.id
        
    except Exception as e:
        logging.error(f"Error running Claude Pokemon Player: {e}")
        raise

if __name__ == "__main__":
    print("This module should be imported by run.py rather than run directly.")
    print("Use 'python run.py --help' for usage information.") 