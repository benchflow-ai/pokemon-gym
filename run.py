#!/usr/bin/env python3
"""
Entry point for the Claude Pokemon Player project.
This script coordinates the emulator setup and Claude gameplay.
"""

import os
import sys
import argparse
import time
from dotenv import load_dotenv

# Import the emulator adapter module
import emulator_adapter

# Import the original emulator setup for some functions
import emulator_setup_rom

# Import the Claude player module
import claude

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Claude Pokemon Player - Let Claude play Pokemon games')
    
    # General arguments
    parser.add_argument('--rom', type=str, help='Path to the Pokemon ROM file (overrides ROM_PATH env variable)')
    parser.add_argument('--snapshot', type=str, help='ID of an existing snapshot to use')
    
    # Gameplay options
    parser.add_argument('--max-turns', type=int, default=100, help='Maximum number of game turns')
    parser.add_argument('--setup-only', action='store_true', help='Set up the emulator but don\'t start Claude')
    
    return parser.parse_args()

def main():
    """Main entry point for the application"""
    # Load environment variables
    load_dotenv()
    
    # Ensure required API keys are present
    if not os.getenv("MORPH_API_KEY"):
        print("Error: MORPH_API_KEY not found in environment.")
        print("Please set this environment variable or add it to a .env file.")
        sys.exit(1)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not found in environment.")
        print("Claude functionality will not work until this is set.")
    
    # Parse arguments
    args = parse_arguments()
    
    # Get ROM path from command line or environment
    rom_path = args.rom if args.rom else os.getenv("ROM_PATH")
    
    # Validate arguments
    if not rom_path and not args.snapshot:
        print("Error: Either --rom, ROM_PATH environment variable, or --snapshot must be specified")
        sys.exit(1)
    
    try:
        # Set up the emulator
        print(f"Setting up emulator with ROM: {rom_path if rom_path else 'None'}")
        print(f"Using snapshot: {args.snapshot if args.snapshot else 'None'}")
        
        instance, url = emulator_adapter.setup_emulator(rom_path, args.snapshot)
        
        print("\n===== EMULATOR READY =====")
        print(f"Access the remote desktop at: {url}/vnc_lite.html")
        print(f"Alternative URL: https://desktop-{instance.id.replace('_', '-')}.http.cloud.morph.so/vnc_lite.html")
        
        # If setup-only flag is set, exit here
        if args.setup_only:
            print("\nEmulator setup complete. Not starting Claude as --setup-only was specified.")
            print(f"Instance ID: {instance.id}")
            print(f"To stop the instance when done, run: morphcloud instance stop {instance.id}")
            return
        
        # Make sure we have the Anthropic API key before proceeding
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("\nError: Cannot start Claude without ANTHROPIC_API_KEY.")
            print("Please set this environment variable and try again.")
            print(f"\nThe emulator is still running. You can access it at {url}/vnc_lite.html")
            print(f"Instance ID: {instance.id}")
            print(f"To stop the instance when done, run: morphcloud instance stop {instance.id}")
            sys.exit(1)
        
        # Give the emulator time to fully initialize before starting Claude
        print("\nWaiting for emulator to fully initialize before starting Claude...")
        time.sleep(10)
        
        # Automate initial interactions if needed
        emulator_setup_rom.automate_initial_interactions(instance)
        
        # Start Claude
        print("\n===== STARTING CLAUDE =====")
        print(f"Claude will play for a maximum of {args.max_turns} turns")
        
        # Run the Claude gameplay loop
        final_snapshot_id = claude.play_game(instance, args.max_turns)
        
        print("\n===== CLAUDE FINISHED PLAYING =====")
        print(f"Final snapshot ID: {final_snapshot_id}")
        print(f"Instance ID: {instance.id}")
        print(f"To stop the instance when done, run: morphcloud instance stop {instance.id}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 