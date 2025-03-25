#!/usr/bin/env python3
"""
Adapter for the emulator_setup_rom.py module.
Provides a cleaner interface to the emulator setup functionality without modifying the original code.
"""

import os
import sys
import time
from morphcloud.api import MorphCloudClient

# Import from original emulator setup module
import emulator_setup_rom

def setup_emulator(rom_path=None, snapshot_id=None):
    """
    Set up the emulator environment in Morph Cloud.
    
    Args:
        rom_path: Path to the ROM file to upload.
        snapshot_id: Optional ID of an existing snapshot to use.
        
    Returns:
        tuple: (instance, url) - The Morph Cloud instance and URL to access the emulator.
    """
    # Expand the ROM path if it contains a tilde
    if rom_path and '~' in rom_path:
        rom_path = os.path.expanduser(rom_path)
        
    # Remove any escape characters in the path
    if rom_path:
        rom_path = rom_path.replace('\\', '')
    
    # If snapshot_id is provided, start from that snapshot
    if snapshot_id:
        client = MorphCloudClient()
        print(f"\n=== 🔍 Using existing snapshot: {snapshot_id} ===")
        instance = client.instances.start(snapshot_id)
        print(f"✅ Instance started from snapshot: {instance.id}")
        
        # Wait for instance to be ready
        print("⏳ Waiting for instance to be ready...")
        instance.wait_until_ready(timeout=300)
        print(f"✅ Instance {instance.id} is ready")
        
        # Expose HTTP service for desktop
        print("\n=== 🌐 Exposing desktop service ===")
        url = instance.expose_http_service("desktop", 80)
        print(f"✅ Desktop service exposed at {url}")
        
        # Start the services
        print("\n=== 🔄 Starting services ===")
        result = instance.exec("systemctl daemon-reload && systemctl restart vncserver xfce-session novnc nginx bizhawk")
        
        # If ROM was provided, upload it
        if rom_path:
            emulator_setup_rom.upload_rom_via_sftp(instance, rom_path)
            print("\n=== ⌛ Waiting for ROM to load ===")
            instance.exec("sleep 5")
            emulator_setup_rom.automate_initial_interactions(instance)
        
        # Print access information
        print("\n=== 🎮 EMULATOR READY! ===")
        print(f"Instance ID: {instance.id}")
        print(f"Access your remote desktop at: {url}/vnc_lite.html")
        print(f"Alternative URL: https://desktop-{instance.id.replace('_', '-')}.http.cloud.morph.so/vnc_lite.html")
        
        return instance, url
    
    # If no snapshot_id, use the original emulator setup approach
    else:
        # Create a simplified args object for the original script
        class Args:
            pass
        
        args = Args()
        args.rom = rom_path
        
        # Store the original sys.argv
        original_argv = sys.argv
        
        try:
            # Temporarily modify sys.argv to match what emulator_setup_rom.py expects
            if rom_path:
                sys.argv = [sys.argv[0], '--rom', rom_path]
            else:
                sys.argv = [sys.argv[0]]
            
            # Run the main function from emulator_setup_rom.py
            # But capture its output to return the instance and URL
            import io
            from contextlib import redirect_stdout
            
            original_stdout = sys.stdout
            str_output = io.StringIO()
            
            instance = None
            url = None
            
            try:
                with redirect_stdout(str_output):
                    # Call the original script
                    result = emulator_setup_rom.main()
                    
                    # We need to extract the instance and URL from the output
                    output = str_output.getvalue()
                    
                    # Find instance ID in the output
                    import re
                    instance_match = re.search(r"Instance\s+([a-zA-Z0-9_]+)\s+is ready", output)
                    if instance_match:
                        instance_id = instance_match.group(1)
                        
                        # Get the client
                        client = MorphCloudClient()
                        
                        # Get the instance
                        instance = client.instances.get(instance_id)
                        
                        # Find URL in the output
                        url_match = re.search(r"Desktop service exposed at\s+(https?://[^\s]+)", output)
                        if url_match:
                            url = url_match.group(1)
            finally:
                sys.stdout = original_stdout
            
            # If we couldn't extract the instance and URL, run it again normally
            if not instance or not url:
                # Run the original main function directly
                emulator_setup_rom.main()
                
                # Inform the user we had trouble extracting the instance and URL
                print("\nNote: Unable to automatically return instance and URL.")
                print("Please manually copy the instance ID and URL from above.")
                
                # Ask the user for the instance ID
                instance_id = input("Please enter the instance ID from above: ")
                
                # Get the client and instance
                client = MorphCloudClient()
                instance = client.instances.get(instance_id)
                
                # Get URL
                services = instance.list_http_services()
                for service in services:
                    if service.name == "desktop":
                        url = service.url
                        break
                
                if not url:
                    url = f"https://desktop-{instance.id.replace('_', '-')}.http.cloud.morph.so"
            
            return instance, url
        
        finally:
            # Restore the original sys.argv
            sys.argv = original_argv 