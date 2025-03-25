#!/usr/bin/env python3
"""
Claude Player for Pokemon - Uses Claude AI to play Pokemon games through the emulator.
It captures screenshots from the emulator, sends them to Claude for analysis,
and then executes the recommended actions.
"""

import os
import time
import base64
import argparse
import json
import sys
import requests
from io import BytesIO
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
    raise ValueError("""
    ANTHROPIC_API_KEY must be set in .env file with a valid API key.
    
    Please update your .env file with your actual Anthropic API key:
    ANTHROPIC_API_KEY=your_actual_key_here
    
    You can get an API key from: https://console.anthropic.com/
    """)

# Get Morph Cloud API key
MORPH_API_KEY = os.getenv('MORPH_API_KEY')

# Get Claude model from environment or use default
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-7-sonnet-20250219')

# Import anthropic (required)
try:
    import anthropic
    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
except ImportError:
    print("ERROR: Anthropic library is not installed.")
    print("Install it with: pip install anthropic")
    sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Use Claude AI to play Pokemon')
    parser.add_argument('--emulator_url', type=str, 
                      help='URL of the remote emulator (required for Morph Cloud)')
    parser.add_argument('--instance_id', type=str,
                      help='Morph Cloud instance ID (for sending keypresses)')
    parser.add_argument('--interval', type=float, default=10.0,
                      help='Interval between screenshot captures in seconds')
    parser.add_argument('--max_tokens', type=int, default=1000,
                      help='Maximum number of tokens in Claude response')
    parser.add_argument('--resize', type=int, default=800,
                      help='Resize screenshot width in pixels (height will scale proportionally)')
    parser.add_argument('--save_screenshots', action='store_true',
                      help='Save screenshots to disk for debugging')
    parser.add_argument('--use_browser', action='store_true',
                      help='Use local browser for emulator access instead of API')
    return parser.parse_args()

def process_screenshot_data(screenshot_data, resize_width=800, save_to_disk=False):
    """Process raw screenshot data into a format suitable for Claude"""
    try:
        from PIL import Image
        screenshot = Image.open(BytesIO(screenshot_data))
        
        # Resize the image to stay under Claude's 5MB limit
        width, height = screenshot.size
        new_width = resize_width
        new_height = int(height * (new_width / width))
        screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
        
        # For PNG format, RGBA is okay
        # For JPEG format, convert RGBA to RGB
        buffer = BytesIO()
        
        if screenshot.mode == 'RGBA':
            # Try to save as PNG first (supports alpha channel)
            try:
                screenshot.save(buffer, format="PNG")
                format_used = "PNG"
            except Exception as e:
                print(f"Error saving as PNG: {e}. Converting to RGB for JPEG...")
                # Create a white background
                background = Image.new('RGB', screenshot.size, (255, 255, 255))
                # Paste the screenshot on the background using alpha as mask
                background.paste(screenshot, mask=screenshot.split()[3])
                screenshot = background
                screenshot.save(buffer, format="JPEG", quality=85)
                format_used = "JPEG"
        else:
            # RGB format, save as JPEG
            screenshot.save(buffer, format="JPEG", quality=85)
            format_used = "JPEG"
        
        # Save to disk if requested
        if save_to_disk:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            os.makedirs("screenshots", exist_ok=True)
            screenshot.save(f"screenshots/screen_{timestamp}.{format_used.lower()}")
            
        print(f"Screenshot processed as {format_used}, size: {len(buffer.getvalue()) / (1024 * 1024):.2f} MB")
        
        return buffer.getvalue()
    except Exception as e:
        print(f"Error processing screenshot: {e}")
        return None

def capture_via_morphcloud_api(instance_id, resize_width=800, save_to_disk=False):
    """Capture a screenshot using the Morph Cloud API"""
    if not MORPH_API_KEY:
        print("ERROR: MORPH_API_KEY environment variable not set.")
        return None
        
    if not instance_id:
        print("ERROR: instance_id required for Morph Cloud API screenshot.")
        return None
        
    try:
        headers = {
            "Authorization": f"Bearer {MORPH_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Command to capture screenshot - we need to make sure ImageMagick is installed
        screenshot_command = """
        if ! command -v import &> /dev/null; then
            apt-get update -qq && apt-get install -y -qq imagemagick
        fi
        DISPLAY=:1 import -window root /tmp/screenshot.png
        cat /tmp/screenshot.png | base64
        """
        
        api_url = "https://api.cloud.morph.so/v1/instances/exec"
        data = {
            "instance_id": instance_id,
            "command": screenshot_command
        }
        
        print("Capturing screenshot via Morph Cloud API...")
        response = requests.post(api_url, json=data, headers=headers)
        
        if response.status_code == 200:
            try:
                result = response.json()
                stdout = result.get('stdout', '')
                
                # Decode the base64 image
                screenshot_data = base64.b64decode(stdout)
                print("Successfully captured screenshot via Morph Cloud API")
                
                # Process the image
                return process_screenshot_data(screenshot_data, resize_width, save_to_disk)
            except Exception as e:
                print(f"Error processing screenshot from API: {e}")
                return None
        else:
            print(f"API screenshot failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error with Morph Cloud API: {e}")
        return None

def capture_via_vnc_api(url, resize_width=800, save_to_disk=False):
    """Try to capture screenshot via various VNC API endpoints"""
    try:
        # Make sure URL points to the VNC client
        if not url.endswith('/vnc_lite.html'):
            if url.endswith('/'):
                url = url + 'vnc_lite.html'
            else:
                url = url + '/vnc_lite.html'
                
        print(f"Accessing remote emulator at: {url}")
        
        # Extract the base URL for alternative API approaches
        base_url = url.replace('/vnc_lite.html', '')
        
        # Try different screenshot API endpoints that might work with noVNC
        # These are common endpoints or approaches that might work with noVNC
        screenshot_urls = [
            f"{base_url}/screenshot.png",
            f"{base_url}/api/screenshot",
            f"{base_url}/api/capture",
            f"{base_url}/screenshots/screenshot.png",
        ]
        
        screenshot_data = None
        for screenshot_url in screenshot_urls:
            try:
                print(f"Trying screenshot URL: {screenshot_url}")
                response = requests.get(screenshot_url, timeout=5)
                if response.status_code == 200 and response.content:
                    screenshot_data = response.content
                    print(f"Successfully captured screenshot from: {screenshot_url}")
                    break
            except requests.RequestException as e:
                print(f"Failed with {screenshot_url}: {e}")
                continue
        
        if not screenshot_data:
            print("All VNC API endpoints failed.")
            return None
            
        # Process the screenshot data
        return process_screenshot_data(screenshot_data, resize_width, save_to_disk)
    except Exception as e:
        print(f"Error in VNC API screenshot capture: {e}")
        return None

def capture_via_browser(url, resize_width=800, save_to_disk=False):
    """Open the emulator in a browser and capture a local screenshot"""
    try:
        # Check if we should open the browser (first time)
        if not hasattr(capture_via_browser, "browser_opened"):
            # Import webbrowser here to avoid dependency issues
            import webbrowser
            print(f"Opening emulator in browser: {url}")
            webbrowser.open(url)
            # Set flag to avoid opening multiple browser windows
            capture_via_browser.browser_opened = True
            # Give time for the browser to open
            print("Waiting 10 seconds for browser to open...")
            time.sleep(10)
            
        print("Taking screenshot of browser window...")
        return capture_local_screenshot(resize_width, save_to_disk)
    except Exception as e:
        print(f"Error with browser-based capture: {e}")
        return None

def capture_local_screenshot(resize_width=800, save_to_disk=False):
    """Capture a screenshot from the local screen"""
    try:
        from PIL import Image, ImageGrab
        # Capture local screenshot
        screenshot = ImageGrab.grab()
        
        # Process the screenshot data
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        return process_screenshot_data(buffer.getvalue(), resize_width, save_to_disk)
    except ImportError:
        print("ERROR: Pillow library is not installed. Cannot capture screenshots.")
        print("Install it with: pip install pillow")
        sys.exit(1)
    except Exception as e:
        print(f"Error capturing local screenshot: {e}")
        return None

def capture_screenshot(emulator_url=None, instance_id=None, resize_width=800, save_to_disk=False, use_browser=False):
    """Capture a screenshot, trying multiple methods in order of preference"""
    
    # Method 1: Morph Cloud API (if we have instance_id and API key)
    if instance_id and MORPH_API_KEY:
        print("Trying Morph Cloud API screenshot...")
        screenshot = capture_via_morphcloud_api(instance_id, resize_width, save_to_disk)
        if screenshot:
            return screenshot
    
    # Method 2: VNC API endpoints (if we have URL)
    if emulator_url:
        print("Trying VNC API endpoints...")
        screenshot = capture_via_vnc_api(emulator_url, resize_width, save_to_disk)
        if screenshot:
            return screenshot
    
    # Method 3: Browser-based capture (if requested and we have URL)
    if use_browser and emulator_url:
        print("Trying browser-based capture...")
        screenshot = capture_via_browser(emulator_url, resize_width, save_to_disk)
        if screenshot:
            return screenshot
    
    # Method 4: Local screenshot as last resort
    print("Trying local screenshot...")
    return capture_local_screenshot(resize_width, save_to_disk)

def encode_image_base64(image_bytes):
    """Encode image bytes to base64 string"""
    return base64.b64encode(image_bytes).decode('utf-8')

def analyze_game_state(image_bytes):
    """Send screenshot to Claude for analysis and recommendations"""
    base64_image = encode_image_base64(image_bytes)
    
    # Determine media type based on header bytes
    media_type = "image/jpeg"  # Default
    if image_bytes.startswith(b'\x89PNG'):
        media_type = "image/png"
    
    # Prepare the message for Claude
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=args.max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """You are an AI that plays Pokemon games.
                        
Look at this screenshot of a Pokemon game and:
1. Describe what you see on the screen (current location, Pokemon visible, NPCs, UI elements)
2. Identify the current game state (battle, overworld, menu, etc.)
3. Recommend the BEST SINGLE action to take next 
   (e.g., "Move UP", "Press A", "Select FIGHT", etc.)
4. Explain your reasoning for the recommended action
5. Format your response in valid JSON with these keys:
   - "description": brief description of the screen
   - "game_state": the current state
   - "action": the recommended action (UP, DOWN, LEFT, RIGHT, A, B, START, SELECT)
   - "reasoning": why this action is recommended

Only respond with valid JSON that can be parsed."""
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    )
    
    # Extract the response content
    response_text = message.content[0].text
    
    # Try to extract JSON from the response
    try:
        # Find JSON in the response (in case Claude adds extra text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            return result
        else:
            print("Error: No JSON found in response")
            print(f"Response: {response_text}")
            return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response: {response_text}")
        return None

def execute_remote_action(action, instance_id):
    """Execute the recommended action in the remote emulator using Morph API"""
    if not instance_id:
        print("ERROR: Cannot execute remote action without instance_id")
        return False
        
    # Map action to keyboard keys and xdotool commands
    action_map = {
        "UP": "key Up",
        "DOWN": "key Down",
        "LEFT": "key Left",
        "RIGHT": "key Right",
        "A": "key x",  # Common BizHawk mapping
        "B": "key z",  # Common BizHawk mapping
        "START": "key Return",
        "SELECT": "key BackSpace"
    }
    
    key_command = action_map.get(action.upper())
    if not key_command:
        print(f"Unknown action: {action}")
        return False
        
    # Construct the xdotool command
    xdotool_cmd = f"DISPLAY=:1 xdotool {key_command}"
    
    # Try the Morph Cloud API if available
    if MORPH_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {MORPH_API_KEY}",
                "Content-Type": "application/json"
            }
            
            api_url = "https://api.cloud.morph.so/v1/instances/exec"
            data = {
                "instance_id": instance_id,
                "command": xdotool_cmd
            }
            
            print(f"Executing action via Morph Cloud API: {action}")
            response = requests.post(api_url, json=data, headers=headers)
            
            if response.status_code == 200:
                print("Command executed successfully via API")
                return True
            else:
                print(f"Error executing remote action via API: {response.status_code} - {response.text}")
                # Fall through to CLI method
        except Exception as e:
            print(f"Error executing remote action via API: {e}")
            # Fall through to CLI method
    
    # Fallback to CLI method
    try:
        cmd = ["morphcloud", "instance", "exec", instance_id, xdotool_cmd]
        print(f"Executing action via CLI: {action}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Command executed successfully via CLI")
            return True
        else:
            print(f"Error executing remote action via CLI: {result.stderr}")
            return False
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"morphcloud CLI not found or failed: {e}")
        return False

def execute_local_action(action):
    """Execute the recommended action using local keyboard input"""
    try:
        import pyautogui
        # Map action to keyboard keys
        action_map = {
            "UP": "up",
            "DOWN": "down",
            "LEFT": "left",
            "RIGHT": "right",
            "A": "x",  # Common BizHawk mapping
            "B": "z",  # Common BizHawk mapping
            "START": "return",
            "SELECT": "backspace"
        }
        
        key = action_map.get(action.upper())
        if key:
            print(f"Executing action: {action} (key: {key})")
            pyautogui.press(key)
            return True
        else:
            print(f"Unknown action: {action}")
            return False
    except ImportError:
        print("WARNING: PyAutoGUI library is not installed. Cannot execute keyboard actions.")
        print("Install it with: pip install pyautogui")
        print(f"Recommended action was: {action}")
        return False

def execute_action(action, instance_id=None):
    """Execute the recommended action using the best available method"""
    if instance_id:
        return execute_remote_action(action, instance_id)
    else:
        return execute_local_action(action)

def save_game_history(action_data):
    """Save the game actions history to a JSON file"""
    history_file = "pokemon_game_history.json"
    
    # Initialize or load existing history
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
    else:
        history = []
    
    # Add timestamp to action data
    action_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Append new action data
    history.append(action_data)
    
    # Save updated history
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)

def main():
    print(f"=== Claude Pokemon Player ===")
    print(f"Using model: {CLAUDE_MODEL}")
    if args.emulator_url:
        print(f"Remote emulator: {args.emulator_url}")
    if args.instance_id:
        print(f"Morph instance ID: {args.instance_id}")
    if MORPH_API_KEY:
        print(f"Morph Cloud API: Available")
    else:
        print(f"Morph Cloud API: Not available (set MORPH_API_KEY in .env)")
    print(f"Screenshot interval: {args.interval} seconds")
    print(f"Screenshot resize width: {args.resize} pixels")
    print(f"Save screenshots: {args.save_screenshots}")
    print(f"Use browser: {args.use_browser}")
    print(f"Press Ctrl+C to exit")
    print("===========================")
    
    try:
        retry_count = 0
        max_retries = 5
        
        while True:
            try:
                # Capture screenshot
                print("Capturing screenshot...")
                screenshot = capture_screenshot(
                    args.emulator_url, 
                    args.instance_id, 
                    args.resize, 
                    args.save_screenshots,
                    args.use_browser
                )
                
                if not screenshot:
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"Failed to capture screenshot after {max_retries} attempts. Exiting.")
                        break
                    
                    print(f"Failed to capture screenshot. Retry {retry_count}/{max_retries} in 5 seconds...")
                    time.sleep(5)
                    continue
                    
                # Reset retry count on success
                retry_count = 0
                    
                # Analyze game state
                print("Analyzing game state with Claude...")
                result = analyze_game_state(screenshot)
                
                if result:
                    print("\n=== Analysis Result ===")
                    print(f"Description: {result.get('description', 'N/A')}")
                    print(f"Game State: {result.get('game_state', 'N/A')}")
                    print(f"Recommended Action: {result.get('action', 'N/A')}")
                    print(f"Reasoning: {result.get('reasoning', 'N/A')}")
                    
                    # Execute the recommended action
                    action = result.get('action')
                    if action:
                        execute_action(action, args.instance_id)
                    
                    # Save game history
                    save_game_history(result)
                
                # Wait for the specified interval
                print(f"\nWaiting {args.interval} seconds before next action...")
                time.sleep(args.interval)
                
            except KeyboardInterrupt:
                print("\nExiting Claude Pokemon Player")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                retry_count += 1
                if retry_count > max_retries:
                    print(f"Too many errors ({retry_count}). Exiting.")
                    break
                    
                print(f"Error occurred. Retry {retry_count}/{max_retries} in 5 seconds...")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\nExiting Claude Pokemon Player")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Claude Pokemon Player has exited.")

if __name__ == "__main__":
    args = parse_arguments()
    main() 