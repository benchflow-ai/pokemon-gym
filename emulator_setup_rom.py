# /// script
# dependencies = [
# "morphcloud",
# ]
# ///

#!/usr/bin/env python3
"""
Setup script for creating a Morph Cloud VM with a remote desktop emulator environment.
Uses snapshot caching for faster setup and SFTP for ROM uploads.
"""

import os
import sys
import time
import argparse
from morphcloud.api import MorphCloudClient

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Set up a remote desktop emulator environment and upload a ROM file.')
    parser.add_argument('--rom', type=str, help='Path to the ROM file to upload to the emulator')
    return parser.parse_args()

def upload_rom_via_sftp(instance, local_path):
    """Upload a ROM file to the instance using Paramiko SFTP"""
    if not os.path.exists(local_path):
        print(f"Error: ROM file not found at {local_path}")
        return False
    
    filename = os.path.basename(local_path)
    remote_path = f"/root/BizHawk/ROMs/{filename}"
    
    print(f"\n=== 📤 Uploading ROM file: {local_path} ===")
    
    # Connect via SSH and create directory
    print("Ensuring ROM directory exists...")
    instance.exec("mkdir -p /root/BizHawk/ROMs && chmod 777 /root/BizHawk/ROMs")
    
    # Get an SSH client from the instance
    ssh_client = instance.ssh_connect()
    sftp = None
    
    try:
        # Open SFTP session
        sftp = ssh_client.open_sftp()
        
        # Upload the file
        print(f"Uploading {filename} to {remote_path}...")
        sftp.put(local_path, remote_path)
        
        # Set permissions
        sftp.chmod(remote_path, 0o644)
        
        print(f"✅ ROM file uploaded successfully")
        
        # Configure BizHawk to load this ROM at startup
        setup_auto_load_rom(instance, remote_path)
        return True
    except Exception as e:
        print(f"❌ Error uploading ROM file: {e}")
        return False
    finally:
        if sftp:
            sftp.close()
        ssh_client.close()
def setup_auto_load_rom(instance, rom_path):
    """Configure BizHawk to automatically load the ROM at startup"""
    print("\n=== 🎮 Configuring BizHawk to auto-load ROM ===")
    
    # Create the start script one command at a time to avoid escaping issues
    instance.exec("mkdir -p /root/BizHawk")
    
    # Create the startup script file
    script_content = f"""#!/bin/bash
cd /root/BizHawk
./EmuHawkMono.sh "{rom_path}" --fullscreen
"""
    
    # Write the script content to a file on the instance
    result = instance.exec(f"cat > /root/BizHawk/start-with-rom.sh << 'EOFSCRIPT'\n{script_content}EOFSCRIPT")
    if result.exit_code != 0:
        print(f"❌ Error creating startup script: {result.stderr}")
        return False
    
    # Make the script executable
    result = instance.exec("chmod +x /root/BizHawk/start-with-rom.sh")
    if result.exit_code != 0:
        print(f"❌ Error making script executable: {result.stderr}")
        return False
    
    # Create a new service file rather than modifying existing one
    service_content = """[Unit]
Description=BizHawk Emulator with ROM
After=xfce-session.service
Requires=xfce-session.service

[Service]
Type=simple
User=root
Environment=DISPLAY=:1
ExecStart=/root/BizHawk/start-with-rom.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    # Write the service file
    result = instance.exec(f"cat > /etc/systemd/system/bizhawk-rom.service << 'EOFSERVICE'\n{service_content}EOFSERVICE")
    if result.exit_code != 0:
        print(f"❌ Error creating service file: {result.stderr}")
        return False
    
    # Stop existing BizHawk service if running
    instance.exec("systemctl stop bizhawk || true")
    
    # Enable and start the new service
    result = instance.exec("systemctl daemon-reload && systemctl enable bizhawk-rom && systemctl restart bizhawk-rom")
    if result.exit_code != 0:
        print(f"❌ Error starting service: {result.stderr}")
        return False
    
    print("✅ ROM auto-load configured successfully")
    return True

def automate_initial_interactions(instance):
    """Automate initial mouse movements and clicks to help with setup"""
    print("\n=== 🖱 Automating initial interactions ===")
    
    # Give services time to fully start up
    print("Waiting for desktop to initialize...")
    instance.exec("sleep 5")
    
    # Execute just the first two mouse commands
    print("Performing initial mouse clicks...")
    mouse_commands = [
        "DISPLAY=:1 xdotool mousemove 755 473 click 1",
        "DISPLAY=:1 xdotool mousemove 644 442 click 1"
    ]
    
    for cmd in mouse_commands:
        result = instance.exec(cmd)
        if result.exit_code != 0:
            print(f"⚠️ Mouse command failed: {cmd}")
            print(f"Error: {result.stderr}")
        else:
            print(f"✅ Executed: {cmd}")
        
        # Add a short delay between commands
        instance.exec("sleep 1")
    
    print("✅ Initial interactions completed")

def main():
    args = parse_arguments()
    
    # Create client (will use MORPH_API_KEY from environment)
    client = MorphCloudClient()
    
    print("\n=== 🚀 Starting emulator setup ===")
    
    # Create or get a base snapshot with reasonable specs
    print("\n=== 🔍 Finding or creating base snapshot ===")
    snapshots = client.snapshots.list(
        digest="emulator-base-snapshot",
        metadata={"purpose": "emulator-environment"}
    )
    
    if snapshots:
        base_snapshot = snapshots[0]
        print(f"✅ Using existing base snapshot: {base_snapshot.id}")
    else:
        print("⏳ Creating new base snapshot...")
        base_snapshot = client.snapshots.create(
            vcpus=4,
            memory=4096,
            disk_size=8192,
            digest="emulator-base-snapshot",
            metadata={"purpose": "emulator-environment"}
        )
        print(f"✅ Created new base snapshot: {base_snapshot.id}")
    
    # Install desktop environment packages - this uses caching!
    print("\n=== 🔧 Setting up desktop environment (cached) ===")
    desktop_setup_script = """
# Update and install essential packages
DEBIAN_FRONTEND=noninteractive apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
    xfce4 xfce4-goodies tigervnc-standalone-server tigervnc-common \
    python3 python3-pip python3-websockify git net-tools nginx \
    dbus dbus-x11 xfonts-base mono-complete libsdl2-2.0-0 \
    libopenal1 libgtk2.0-0 xdotool imagemagick

# Clone noVNC repository
rm -rf /opt/noVNC || true
git clone https://github.com/novnc/noVNC.git /opt/noVNC

# Clean any existing VNC processes
pkill Xvnc || true
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 || true

# Create config directories
mkdir -p /root/.config/xfce4 /root/.config/xfce4-session /root/.config/autostart /root/.config/systemd
"""
    
    start_time = time.time()
    desktop_snapshot = base_snapshot.setup(desktop_setup_script)
    end_time = time.time()
    print(f"⏱️ Desktop environment setup time: {end_time - start_time:.2f} seconds")
    
    # Set up services - this also uses caching!
    print("\n=== 🔧 Setting up services (cached) ===")
    services_setup_script = """
# Create VNC service
cat > /etc/systemd/system/vncserver.service << 'EOF'
[Unit]
Description=VNC Server for X11
After=syslog.target network.target

[Service]
Type=simple
User=root
Environment=HOME=/root
Environment=DISPLAY=:1
ExecStartPre=-/bin/rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
ExecStart=/usr/bin/Xvnc :1 -geometry 1280x800 -depth 24 -SecurityTypes None -localhost no
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create XFCE session startup script
cat > /usr/local/bin/start-xfce-session << 'EOF'
#!/bin/bash
export DISPLAY=:1
export HOME=/root
export XDG_CONFIG_HOME=/root/.config
export XDG_CACHE_HOME=/root/.cache
export XDG_DATA_HOME=/root/.local/share
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

# Start dbus if not running
if [ -z "$DBUS_SESSION_BUS_PID" ]; then
  eval $(dbus-launch --sh-syntax)
fi

# Ensure xfconfd is running
/usr/lib/x86_64-linux-gnu/xfce4/xfconf/xfconfd &

# Wait for xfconfd to start
sleep 2

# Start XFCE session
exec startxfce4
EOF

chmod +x /usr/local/bin/start-xfce-session

# Create XFCE service
cat > /etc/systemd/system/xfce-session.service << 'EOF'
[Unit]
Description=XFCE Session
After=vncserver.service dbus.service
Requires=vncserver.service dbus.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/start-xfce-session
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create noVNC service
cat > /etc/systemd/system/novnc.service << 'EOF'
[Unit]
Description=noVNC service
After=vncserver.service
Requires=vncserver.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/websockify --web=/opt/noVNC 6080 localhost:5901
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Configure nginx
cat > /etc/nginx/sites-available/novnc << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:6080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

ln -sf /etc/nginx/sites-available/novnc /etc/nginx/sites-enabled/novnc
rm -f /etc/nginx/sites-enabled/default

# Enable services
systemctl daemon-reload
systemctl enable vncserver xfce-session novnc nginx
"""
    
    start_time = time.time()
    services_snapshot = desktop_snapshot.setup(services_setup_script)
    end_time = time.time()
    print(f"⏱️ Services setup time: {end_time - start_time:.2f} seconds")
    
    # Install BizHawk - this uses caching!
    print("\n=== 🔧 Setting up BizHawk emulator (cached) ===")
    bizhawk_setup_script = """
# Download and extract BizHawk
rm -rf /root/BizHawk || true
wget -q https://github.com/TASEmulators/BizHawk/releases/download/2.10/BizHawk-2.10-linux-x64.tar.gz
mkdir -p /root/BizHawk
tar -xzf BizHawk-2.10-linux-x64.tar.gz -C /root/BizHawk
chmod +x /root/BizHawk/EmuHawkMono.sh
mkdir -p /root/BizHawk/ROMs
chmod 777 /root/BizHawk/ROMs

# Create BizHawk startup script
cat > /usr/local/bin/start-bizhawk << 'EOF'
#!/bin/bash
export DISPLAY=:1
export HOME=/root
export XDG_CONFIG_HOME=/root/.config
export XDG_CACHE_HOME=/root/.cache
export XDG_DATA_HOME=/root/.local/share
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

cd /root/BizHawk
./EmuHawkMono.sh --fullscreen
EOF

chmod +x /usr/local/bin/start-bizhawk

# Create BizHawk service
cat > /etc/systemd/system/bizhawk.service << 'EOF'
[Unit]
Description=BizHawk Emulator
After=xfce-session.service
Requires=xfce-session.service

[Service]
Type=simple
User=root
Environment=DISPLAY=:1
ExecStart=/usr/local/bin/start-bizhawk
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable BizHawk service
systemctl daemon-reload
systemctl enable bizhawk
rm -f BizHawk-2.10-linux-x64.tar.gz
"""
    
    start_time = time.time()
    bizhawk_snapshot = services_snapshot.setup(bizhawk_setup_script)
    end_time = time.time()
    print(f"⏱️ BizHawk setup time: {end_time - start_time:.2f} seconds")
    
    # Start an instance from the final snapshot
    print("\n=== 🚀 Starting instance from final snapshot ===")
    print(f"Snapshot ID: {bizhawk_snapshot.id}")
    instance = client.instances.start(bizhawk_snapshot.id)
    
    try:
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
        if result.exit_code == 0:
            print("✅ All services started successfully")
        else:
            print(f"⚠️ Some services may not have started correctly: {result.stderr}")
        
        # Upload ROM if specified and perform interactions after ROM is loaded
        if args.rom:
            if upload_rom_via_sftp(instance, args.rom):
                # Give the ROM loading service time to start
                print("\n=== ⌛ Waiting for ROM to load ===")
                instance.exec("sleep 5")
                # Now perform the interactions
                automate_initial_interactions(instance)
        else:
            # If no ROM, wait for BizHawk to start normally before interactions
            print("\n=== ⌛ Waiting for emulator to start ===")
            instance.exec("sleep 5")
            automate_initial_interactions(instance)
        
        # Print access information
        print("\n=== 🎮 EMULATOR READY! ===")
        print(f"Instance ID: {instance.id}")
        print(f"Access your remote desktop at: {url}/vnc_lite.html")
        print(f"Alternative URL: https://desktop-{instance.id.replace('_', '-')}.http.cloud.morph.so/vnc_lite.html")
        
        # Create a final snapshot with the ROM and setup included
        print("\n=== 💾 Creating final snapshot ===")
        final_snapshot = instance.snapshot()
        
        # Add metadata about the ROM
        metadata = {
            "type": "emulator-complete",
            "description": "Remote desktop environment with XFCE, noVNC, and BizHawk",
            "has_rom": "true" if args.rom else "false"
        }
        if args.rom:
            metadata["rom_file"] = os.path.basename(args.rom)
        
        final_snapshot.set_metadata(metadata)
        print(f"✅ Final snapshot created: {final_snapshot.id}")
        print(f"To start a new instance from this exact state, run:")
        print(f"morphcloud instance start {final_snapshot.id}")
        
        print("\nThe instance will remain running. To stop it when you're done, run:")
        print(f"morphcloud instance stop {instance.id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("For troubleshooting, try SSH:")
        print(f"morphcloud instance ssh {instance.id}")
        raise

if __name__ == "__main__":
    main()
