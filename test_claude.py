#!/usr/bin/env python3
"""
Simple test script for Claude API connectivity
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if Anthropic is installed
try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package is not installed.")
    print("Install it with: pip install anthropic")
    sys.exit(1)

# Get API key from environment
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
    print("""
ERROR: ANTHROPIC_API_KEY must be set in .env file with a valid API key.
    
Please update your .env file with your actual Anthropic API key:
ANTHROPIC_API_KEY=your_actual_key_here
    
You can get an API key from: https://console.anthropic.com/
    """)
    sys.exit(1)

# Get Claude model from environment or use default
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-7-sonnet-20250219')

print("Testing Claude API connection...")
print(f"Using model: {CLAUDE_MODEL}")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

try:
    # Send a simple message to Claude
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Hello Claude! Respond with a single emoji that represents a Pokémon."
            }
        ]
    )
    
    # Print the response
    print("\nClaude's response:")
    print(message.content[0].text)
    print("\nAPI test successful! You're ready to play Pokemon with Claude.")
    
except Exception as e:
    print(f"\nERROR: Failed to connect to Claude API: {e}")
    sys.exit(1) 