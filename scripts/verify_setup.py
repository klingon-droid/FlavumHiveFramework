#!/usr/bin/env python3
"""
Verification script for project structure and dependencies.
Tests that both the project structure and dependencies are correctly set up.
"""

import importlib
import os
import sys
from pathlib import Path
import pkg_resources

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

def check_directory_structure():
    """Verify that the project structure is correct."""
    required_dirs = [
        'platforms',
        'platforms/reddit',
        'platforms/eliza',
    ]
    
    required_files = [
        'platforms/__init__.py',
        'platforms/reddit/__init__.py',
        'platforms/reddit/post.py',
        'platforms/reddit/comment.py',
        'platforms/reddit/helper.py',
        'platforms/eliza/__init__.py',
    ]
    
    errors = []
    
    # Check directories
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            errors.append(f"Missing directory: {dir_path}")
    
    # Check files
    for file_path in required_files:
        if not os.path.isfile(file_path):
            errors.append(f"Missing file: {file_path}")
    
    return errors

def check_core_dependencies():
    """Verify that core dependencies are installed."""
    required_packages = {
        'praw': 'praw',
        'openai': 'openai',
        'flask': 'flask',
        'python-dotenv': 'dotenv',
        'aiohttp': 'aiohttp',
        'sqlalchemy': 'sqlalchemy',
        'alembic': 'alembic',
        'pytest': 'pytest',
        'pytest-asyncio': 'pytest_asyncio'
    }
    
    missing = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name} installed")
        except ImportError:
            missing.append(package_name)
            print(f"❌ {package_name} not found")
    
    return missing

def check_platform_imports():
    """Verify that platform-specific imports work."""
    import_errors = []
    
    try:
        from platforms import SocialPlatform
        print("✅ Base platform interface imported successfully")
    except ImportError as e:
        import_errors.append(f"Failed to import base platform interface: {e}")
    
    try:
        from platforms.reddit import RedditPlatform
        print("✅ Reddit platform imported successfully")
    except ImportError as e:
        import_errors.append(f"Failed to import Reddit platform: {e}")
    
    return import_errors

def check_eliza_dependencies():
    """Check if Eliza-specific dependencies are installed (if enabled)."""
    config_path = Path(__file__).parent.parent / 'config.json'
    if not config_path.exists():
        return ["config.json not found"]
    
    import json
    with open(config_path) as f:
        config = json.load(f)
    
    platforms = config.get('platforms', {})
    errors = []
    
    if platforms.get('discord'):
        try:
            import discord
            print("✅ Discord.py installed")
        except ImportError:
            errors.append("Discord.py not installed")
    
    if platforms.get('twitter'):
        try:
            import tweepy
            print("✅ Tweepy installed")
        except ImportError:
            errors.append("Tweepy not installed")
    
    if platforms.get('telegram'):
        try:
            import telegram
            print("✅ Python-telegram-bot installed")
        except ImportError:
            errors.append("Python-telegram-bot not installed")
    
    return errors

def main():
    """Run all verification checks."""
    print("\n=== Checking Project Structure ===")
    structure_errors = check_directory_structure()
    if structure_errors:
        print("❌ Project structure issues found:")
        for error in structure_errors:
            print(f"  - {error}")
    else:
        print("✅ Project structure is correct")
    
    print("\n=== Checking Core Dependencies ===")
    missing_deps = check_core_dependencies()
    if missing_deps:
        print("❌ Missing core dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
    else:
        print("✅ All core dependencies are installed")
    
    print("\n=== Checking Platform Imports ===")
    import_errors = check_platform_imports()
    if import_errors:
        print("❌ Import issues found:")
        for error in import_errors:
            print(f"  - {error}")
    else:
        print("✅ All platform imports working")
    
    print("\n=== Checking Eliza Dependencies ===")
    eliza_errors = check_eliza_dependencies()
    if eliza_errors:
        print("❌ Eliza dependency issues found:")
        for error in eliza_errors:
            print(f"  - {error}")
    else:
        print("✅ All required Eliza dependencies are installed")
    
    # Overall status
    if any([structure_errors, missing_deps, import_errors, eliza_errors]):
        print("\n❌ Setup verification failed. Please fix the issues above.")
        sys.exit(1)
    else:
        print("\n✅ All checks passed! Setup is correct.")
        sys.exit(0)

if __name__ == '__main__':
    main() 