import argparse
import base64
import io
import logging
import os
import time
import csv
import datetime
from typing import Dict, List, Any, Optional
import threading  # For the timeout timer

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

from pokemon_env import PokemonEnvironment
from pokemon_env.action import Action, PressKey, Wait, ActionType
from .evaluate import PokemonEvaluator  # Import the evaluator class

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Global variables
ROM_PATH = "Pokemon_Red.gb"  # Default ROM path
ENV = None
CSV_WRITER = None
CSV_FILE = None
LAST_RESPONSE_TIME = None
EVALUATOR = None  # Add evaluator instance variable
SESSION_START_TIME = None  # Track when the session started
SESSION_TIMER = None  # Timer to track 30 minute limit
MAX_SESSION_DURATION = 4 * 60 * 60  # 30 minutes in seconds

# Output directory structure
OUTPUT_DIR = "gameplay_sessions"  # Base directory for all sessions
current_session_dir = None  # Current session directory
IMAGES_FOLDER = "images"  # Subfolder name for images within the session directory

# Create base output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title="Pokemon Evaluator API",
    description="API for evaluating AI agents on Pokemon Red gameplay",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models for API requests and responses
class InitializeRequest(BaseModel):
    headless: bool = True
    sound: bool = False


class ActionRequest(BaseModel):
    action_type: str  # "press_key" or "wait"
    # For press_key
    keys: Optional[List[str]] = None
    # For wait
    frames: Optional[int] = None


class GameStateResponse(BaseModel):
    player_name: str
    rival_name: str
    money: int
    location: str
    coordinates: List[int]
    badges: List[str]
    valid_moves: List[str]
    inventory: List[Dict[str, Any]]
    dialog: None | str
    pokemons: List[Dict[str, Any]]
    screenshot_base64: str
    collision_map: None | str
    step_number: int
    execution_time: float
    score: float = 0.0  # Add a score field to the response


def setup_session_directory():
    """Create a new directory for the current gameplay session."""
    global current_session_dir
    
    # Generate timestamp for unique directory name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(OUTPUT_DIR, f"session_{timestamp}")
    
    # Create session directory
    os.makedirs(session_dir, exist_ok=True)
    
    # Create images subdirectory
    images_dir = os.path.join(session_dir, IMAGES_FOLDER)
    os.makedirs(images_dir, exist_ok=True)
    
    current_session_dir = session_dir
    logger.info(f"Created session directory: {session_dir}")
    
    return session_dir


def save_screenshot(screenshot_base64: str, step_number: int, action_type: str) -> None:
    """
    Save a screenshot to the images folder
    
    Args:
        screenshot_base64: Base64 encoded screenshot
        step_number: Current step number
        action_type: Type of action taken
    """
    try:
        # Create filename with step number and action type
        images_dir = os.path.join(current_session_dir, IMAGES_FOLDER)
        filename = os.path.join(images_dir, f"{step_number}_{action_type}.png")
        
        # Decode base64 image
        image_data = base64.b64decode(screenshot_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Save the image
        image.save(filename)
        logger.info(f"Screenshot saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving screenshot: {e}")


def initialize_csv_logger(custom_filename=None):
    """Initialize the CSV logger within the session directory."""
    global CSV_WRITER, CSV_FILE
    
    try:
        if custom_filename:
            # If a custom filename is provided, use it but place in the session directory
            filename = os.path.join(current_session_dir, os.path.basename(custom_filename))
        else:
            # Otherwise use a default name
            filename = os.path.join(current_session_dir, "gameplay_data.csv")
        
        CSV_FILE = open(filename, 'w', newline='')
        fieldnames = ['timestamp', 'step_number', 'action_type', 'action_details', 'badges', 
                      'inventory', 'location', 'money', 'coordinates', 'pokemons', 'dialog', 
                      'execution_time', 'score']  # Add score to fieldnames
        CSV_WRITER = csv.DictWriter(CSV_FILE, fieldnames=fieldnames)
        CSV_WRITER.writeheader()
        logger.info(f"Response data will be logged to {filename}")
    except Exception as e:
        logger.error(f"Error initializing CSV logger: {e}")
        CSV_WRITER = None
        if CSV_FILE:
            CSV_FILE.close()
            CSV_FILE = None


def log_response(response: GameStateResponse, action_type: str, action_details: Any):
    """Log a response to the CSV file."""
    global CSV_WRITER, EVALUATOR
    
    if CSV_WRITER is None:
        return
    try:
        row = {
            'timestamp': datetime.datetime.now().isoformat(),
            'step_number': response.step_number,
            'action_type': action_type,
            'action_details': str(action_details),
            'badges': str(response.badges),
            'inventory': str(response.inventory),
            'location': response.location,
            'money': response.money,
            'coordinates': str(response.coordinates),
            'pokemons': str(response.pokemons),  # Convert pokemons to string representation
            'dialog': response.dialog,
            'execution_time': response.execution_time,
            'score': response.score  # Add score to CSV
        }
        CSV_WRITER.writerow(row)
        CSV_FILE.flush()  # Ensure data is written immediately
        logger.info(f"Response data for step {response.step_number} logged to CSV")
        
        # Update the evaluator with the latest state
        if EVALUATOR:
            EVALUATOR.evaluate_row(row)
        
        # Save screenshot with step number and action type
        action_name = action_type
        if action_type == "press_key" and isinstance(action_details, dict) and "keys" in action_details:
            action_name = f"press_{'-'.join(action_details['keys'])}"
        elif action_type == "wait" and isinstance(action_details, dict) and "frames" in action_details:
            action_name = f"wait_{action_details['frames']}"
        
        save_screenshot(response.screenshot_base64, response.step_number, action_name)
        
    except Exception as e:
        logger.error(f"Error logging to CSV: {e}")


def force_stop_session():
    """Force stop the current session after timeout."""
    global ENV, CSV_FILE, CSV_WRITER, EVALUATOR, SESSION_START_TIME, SESSION_TIMER
    
    logger.warning(f"Session timeout reached ({MAX_SESSION_DURATION/60} minutes). Forcing session to stop.")
    
    try:
        if ENV:
            ENV.stop()
            ENV = None
        
        # Close CSV file if open
        if CSV_FILE:
            logger.info("Closing CSV log file")
            CSV_FILE.close()
            CSV_FILE = None
            CSV_WRITER = None
        
        EVALUATOR = None  # Reset evaluator
        SESSION_START_TIME = None
        
        if SESSION_TIMER:
            SESSION_TIMER.cancel()
            SESSION_TIMER = None
            
        logger.info("Session has been forcibly stopped due to timeout")
    except Exception as e:
        logger.error(f"Error during forced session stop: {e}")


# API Endpoints
@app.post("/initialize", response_model=GameStateResponse)
async def initialize(request: InitializeRequest):
    """
    Initialize the Pokemon environment and return the initial state.
    
    Args:
        request: Initialization parameters
    
    Returns:
        The initial game state
    """
    global ENV, LAST_RESPONSE_TIME, EVALUATOR, SESSION_START_TIME, SESSION_TIMER
    
    # Cancel any existing timer
    if SESSION_TIMER:
        SESSION_TIMER.cancel()
        SESSION_TIMER = None
    
    # First, ensure any existing session is stopped
    if ENV:
        try:
            ENV.stop()
        except Exception as e:
            logger.error(f"Error stopping existing environment: {e}")
        ENV = None
    
    # Set up a new session directory
    setup_session_directory()
    
    # Initialize CSV logger in the new session directory
    initialize_csv_logger()
    
    # Initialize the evaluator
    EVALUATOR = PokemonEvaluator()
    
    # Reset the last response time
    LAST_RESPONSE_TIME = time.time()
    SESSION_START_TIME = time.time()
    
    # Check if ROM file exists
    if not os.path.exists(ROM_PATH):
        raise HTTPException(
            status_code=500, 
            detail=f"ROM file not found: {ROM_PATH}"
        )
    
    # Initialize environment
    try:
        logger.info(f"Initializing environment with ROM: {ROM_PATH}")
        ENV = PokemonEnvironment(
            rom_path=ROM_PATH,
            headless=request.headless,
            sound=request.sound
        )
        logger.info("env initialized")
        
        # Get initial state
        state = ENV.state
        logger.info("state initialized")
        collision_map = ENV.get_collision_map()
        
        # Prepare response
        response = GameStateResponse(
            player_name=state.player_name,
            rival_name=state.rival_name,
            money=state.money,
            location=state.location,
            coordinates=list(state.coordinates),  # Convert tuple to list
            badges=state.badges,
            valid_moves=state.valid_moves,
            inventory=state.inventory,
            dialog=state.dialog,
            pokemons=state.pokemons,
            screenshot_base64=state.screenshot_base64,
            collision_map=collision_map,
            step_number=0,
            execution_time=0.0,
            score=0.0  # Initial score
        )
        
        # Log initial state
        log_response(response, "initialize", request)
        
        # Update score after evaluating initial state
        if EVALUATOR:
            response.score = EVALUATOR.total_score
        
        # Save initial screenshot explicitly
        save_screenshot(response.screenshot_base64, 0, "initial")
        
        # Set up a timer to automatically stop the session after 30 minutes
        SESSION_TIMER = threading.Timer(MAX_SESSION_DURATION, force_stop_session)
        SESSION_TIMER.daemon = True  # Allow the timer to be terminated when the program exits
        SESSION_TIMER.start()
        logger.info(f"Session will automatically terminate in {MAX_SESSION_DURATION/60} minutes")
        
        return response
    
    except Exception as e:
        logger.error(f"Error initializing environment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize environment: {str(e)}"
        )


@app.post("/action", response_model=GameStateResponse)
async def take_action(request: ActionRequest):
    """
    Take an action in the environment and return the new state.
    
    Args:
        request: Action parameters
    
    Returns:
        The new game state after taking the action
    """
    global ENV, LAST_RESPONSE_TIME, EVALUATOR, SESSION_START_TIME
    
    # Check if session has timed out
    if SESSION_START_TIME is None or time.time() - SESSION_START_TIME > MAX_SESSION_DURATION:
        # Force stop if not already stopped
        if ENV:
            force_stop_session()
        
        return GameStateResponse(
            player_name="",
            rival_name="",
            money=0,
            location="SESSION_TIMEOUT",
            coordinates=[0, 0],
            badges=[],
            valid_moves=[],
            inventory=[],
            dialog="Session has timed out after 30 minutes. Please initialize a new session.",
            pokemons=[],
            screenshot_base64="",
            collision_map=None,
            step_number=0,
            execution_time=0.0,
            score=EVALUATOR.total_score if EVALUATOR else 0.0
        )
    
    # Calculate execution time (time since last response)
    current_time = time.time()
    if LAST_RESPONSE_TIME is None:
        execution_time = 0.0  # First action has no previous time
    else:
        execution_time = current_time - LAST_RESPONSE_TIME
    
    # Check if environment is initialized
    if ENV is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call /initialize first."
        )
    
    logger.info(f"Taking action: {request.action_type}")
    logger.info(f"Keys: {request.keys}")
    logger.info(f"Frames: {request.frames}")
    
    # Create action based on request
    try:
        if request.action_type == "press_key":
            if not request.keys:
                raise HTTPException(
                    status_code=400,
                    detail="Keys parameter is required for press_key action."
                )
            logger.info(f"Creating PressKey action with keys: {request.keys}")
            action = PressKey(keys=request.keys)
            action_details = {"keys": request.keys}
        
        elif request.action_type == "wait":
            if not request.frames:
                raise HTTPException(
                    status_code=400,
                    detail="Frames parameter is required for wait action."
                )
            
            action = Wait(frames=request.frames)
            action_details = {"frames": request.frames}
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action type: {request.action_type}"
            )
        
        # Execute action
        state = ENV.step(action)
        
        # Get collision map and valid moves
        collision_map = ENV.get_collision_map()
        valid_moves = ENV.get_valid_moves()
        
        # Prepare response
        response = GameStateResponse(
            player_name=state.player_name,
            rival_name=state.rival_name,
            money=state.money,
            location=state.location,
            coordinates=list(state.coordinates),  # Convert tuple to list
            badges=state.badges,
            valid_moves=state.valid_moves,
            inventory=state.inventory,
            dialog=state.dialog,
            pokemons=state.pokemons,
            screenshot_base64=state.screenshot_base64,
            collision_map=collision_map,
            step_number=ENV.steps_taken,
            execution_time=execution_time,  # Use the calculated time
            score=EVALUATOR.total_score if EVALUATOR else 0.0  # Add current score
        )
        
        # Log the action and response
        log_response(response, request.action_type, action_details)
        
        # Update the response score after evaluation
        if EVALUATOR:
            response.score = EVALUATOR.total_score
        
        # Update the last response time
        LAST_RESPONSE_TIME = time.time()
        
        # Check remaining time and log it
        remaining_time = MAX_SESSION_DURATION - (time.time() - SESSION_START_TIME)
        logger.info(f"Remaining session time: {remaining_time/60:.1f} minutes")
        
        return response
    
    except Exception as e:
        logger.error(f"Error taking action: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to take action: {str(e)}"
        )


@app.get("/status")
async def get_status():
    """Get the current status of the environment."""
    global EVALUATOR, SESSION_START_TIME
    
    if ENV is None:
        return {"status": "not_initialized"}
    
    score_info = {}
    if EVALUATOR:
        score_info = {
            "score": EVALUATOR.total_score,
            "pokemon_count": len(EVALUATOR.pokemon_seen),
            "badges_count": len(EVALUATOR.badges_earned),
            "locations_count": len(EVALUATOR.locations_visited)
        }
    
    # Calculate remaining time
    remaining_time = 0
    if SESSION_START_TIME:
        elapsed = time.time() - SESSION_START_TIME
        remaining_time = max(0, MAX_SESSION_DURATION - elapsed)
    
    return {
        "status": "running", 
        "steps_taken": ENV.steps_taken, 
        "session_dir": current_session_dir,
        "remaining_time_seconds": remaining_time,
        "remaining_time_minutes": remaining_time / 60,
        **score_info  # Include score information
    }


@app.post("/stop")
async def stop_environment():
    """Stop the environment."""
    global ENV, CSV_FILE, CSV_WRITER, current_session_dir, EVALUATOR, SESSION_TIMER, SESSION_START_TIME
    
    # Cancel the session timer if it exists
    if SESSION_TIMER:
        SESSION_TIMER.cancel()
        SESSION_TIMER = None
    
    if ENV is None:
        return {"status": "not_initialized"}
    
    session_path = current_session_dir
    score_summary = {}
    
    # Get final score information
    if EVALUATOR:
        score_summary = {
            "final_score": EVALUATOR.total_score,
            "pokemon_collected": list(EVALUATOR.pokemon_seen),
            "badges_earned": list(EVALUATOR.badges_earned),
            "locations_visited": list(EVALUATOR.locations_visited),
            "pokemon_count": len(EVALUATOR.pokemon_seen),
            "badges_count": len(EVALUATOR.badges_earned),
            "locations_count": len(EVALUATOR.locations_visited)
        }
        
        # Generate a summary file
        try:
            summary_path = os.path.join(current_session_dir, "evaluation_summary.txt")
            with open(summary_path, 'w') as f:
                f.write("=== Pokemon Gameplay Evaluation Summary ===\n\n")
                f.write(f"Final Score: {EVALUATOR.total_score:.2f}\n")
                f.write(f"Pokemon Collected: {len(EVALUATOR.pokemon_seen)}\n")
                f.write(f"Badges Earned: {len(EVALUATOR.badges_earned)}\n")
                f.write(f"Locations Visited: {len(EVALUATOR.locations_visited)}\n\n")
                
                f.write("--- Pokemon Details ---\n")
                for pokemon in sorted(EVALUATOR.pokemon_seen):
                    f.write(f"- {pokemon}\n")
                
                f.write("\n--- Badge Details ---\n")
                for badge in sorted(EVALUATOR.badges_earned):
                    f.write(f"- {badge}\n")
                
                f.write("\n--- Location Details ---\n")
                for location in sorted(EVALUATOR.locations_visited):
                    f.write(f"- {location}\n")
        except Exception as e:
            logger.error(f"Error writing evaluation summary: {e}")
    
    try:
        ENV.stop()
        ENV = None
        
        # Close CSV file if open
        if CSV_FILE:
            logger.info("Closing CSV log file")
            CSV_FILE.close()
            CSV_FILE = None
            CSV_WRITER = None
        
        EVALUATOR = None  # Reset evaluator
            
        logger.info(f"Session data saved to {session_path}")
        return {
            "status": "stopped", 
            "session_dir": session_path,
            **score_summary  # Include score summary in response
        }
    
    except Exception as e:
        logger.error(f"Error stopping environment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop environment: {str(e)}"
        )


# Add a new endpoint to get the current evaluation
@app.get("/evaluate")
async def get_evaluation():
    """Get the current evaluation summary."""
    global EVALUATOR
    
    if EVALUATOR is None:
        raise HTTPException(
            status_code=400,
            detail="Evaluator not initialized. Call /initialize first."
        )
    
    # Return a detailed evaluation summary
    return {
        "score": EVALUATOR.total_score,
        "pokemon": {
            "count": len(EVALUATOR.pokemon_seen),
            "items": list(EVALUATOR.pokemon_seen)
        },
        "badges": {
            "count": len(EVALUATOR.badges_earned),
            "items": list(EVALUATOR.badges_earned)
        },
        "locations": {
            "count": len(EVALUATOR.locations_visited),
            "items": list(EVALUATOR.locations_visited)
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pokemon Evaluator API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the server on")
    parser.add_argument("--rom", type=str, default="Pokemon_Red.gb", help="Path to the Pokemon ROM file")
    parser.add_argument("--log-file", type=str, help="Custom CSV filename (optional)")
    
    args = parser.parse_args()
    
    # Set ROM path
    ROM_PATH = args.rom
    
    # Run the server
    uvicorn.run(app, host=args.host, port=args.port) 