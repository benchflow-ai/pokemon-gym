# Pokemon Emulator Setup

This repository contains a script to set up a cloud-based Pokemon emulator environment using Morph Cloud. The script creates a virtual machine with a remote desktop environment, installs BizHawk emulator, and configures it to run your Pokemon ROM.

## Prerequisites

- Python 3.6+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- A valid Morph Cloud API key
- Pokemon ROM file (e.g., Pokemon Red.gb)

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/pokemon-gym.git
   cd pokemon-gym
   ```

2. Install dependencies with uv:
   ```bash
   uv pip install morphcloud
   ```

## Usage

To run the emulator setup with your Pokemon ROM:

```bash
uv run emulator_setup_rom.py --rom ~/Downloads/Pokemon\ Red.gb
```

The script will:

1. Create or use a cached snapshot with a desktop environment
2. Set up BizHawk emulator
3. Upload your ROM file
4. Configure the emulator to auto-load your ROM
5. Provide you with a URL to access the remote desktop environment

## Project Structure

```
pokemon-gym/
├── .gitignore          # Git ignore rules
├── README.md          # This file
├── emulator_setup_rom.py # Main setup script
└── requirements.txt   # Python dependencies
```

## Features

- Remote desktop environment with XFCE
- BizHawk emulator pre-installed
- Automatic ROM loading
- Cached snapshots for faster setup
- Secure SFTP for ROM uploads
- noVNC for browser-based access

## Troubleshooting

If you encounter any issues, check the console output for error messages. You can SSH into the instance for troubleshooting using:

```bash
morphcloud instance ssh <instance_id>
```

Where `<instance_id>` is the instance ID displayed in the script output.

Common issues:

1. **ROM Not Found**: Ensure the ROM file path is correct and the file exists
2. **Permission Issues**: Check if you have the necessary permissions to access the ROM file
3. **Connection Issues**: Verify your internet connection and Morph Cloud API key

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
