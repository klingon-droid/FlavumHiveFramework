#!/usr/bin/env python3
"""
Dependency installation script for the platform integration.
This script reads the config.json to determine which platforms are enabled
and installs the necessary dependencies.
"""

import json
import subprocess
import sys
from pathlib import Path

def read_config():
    """Read the configuration file."""
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config.json: {e}")
        return None

def install_requirements(requirements_file):
    """Install requirements from a requirements file."""
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', requirements_file
        ])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing {requirements_file}: {e}")
        return False

def main():
    """Main installation process."""
    # Always install core requirements
    print("Installing core requirements...")
    if not install_requirements('requirements.txt'):
        sys.exit(1)

    # Read config to check which platforms are enabled
    config = read_config()
    if not config:
        sys.exit(1)

    # Check if Eliza platforms are enabled
    platforms = config.get('platforms', {})
    if any([
        platforms.get('discord', False),
        platforms.get('twitter', False),
        platforms.get('telegram', False),
        platforms.get('instagram', False),
        platforms.get('slack', False)
    ]):
        print("Installing Eliza platform requirements...")
        if not install_requirements('requirements-eliza.txt'):
            sys.exit(1)

    print("All dependencies installed successfully!")

if __name__ == '__main__':
    main() 