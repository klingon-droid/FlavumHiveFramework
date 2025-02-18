#!/usr/bin/env python3
import os
import json
import argparse
import subprocess
import psutil
import time
from datetime import datetime

def get_bot_pid():
    """Get the PID of the running bot process"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'continuous_twitter_bot.py' in ' '.join(proc.info['cmdline']):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def get_bot_status():
    """Get current bot status"""
    status_file = 'bot_status.json'
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                status = json.load(f)
            return status
        except:
            return None
    return None

def get_config():
    """Get Twitter configuration"""
    config_file = 'config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config['platforms']['twitter']
        except:
            return None
    return None

def start_bot():
    """Start the Twitter bot"""
    pid = get_bot_pid()
    if pid:
        print("Bot is already running!")
        return

    try:
        # Start the bot in the background
        subprocess.Popen(
            ['python', 'continuous_twitter_bot.py'],
            stdout=open('bot_output.log', 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        print("Bot started successfully! Monitor bot_output.log for details.")
    except Exception as e:
        print(f"Failed to start bot: {str(e)}")

def stop_bot():
    """Stop the Twitter bot"""
    pid = get_bot_pid()
    if not pid:
        print("Bot is not running!")
        return

    try:
        os.kill(pid, 15)  # Send SIGTERM
        time.sleep(2)
        if psutil.pid_exists(pid):
            os.kill(pid, 9)  # Send SIGKILL if still running
        print("Bot stopped successfully!")
    except Exception as e:
        print(f"Failed to stop bot: {str(e)}")

def show_status():
    """Show bot status and statistics"""
    pid = get_bot_pid()
    status = get_bot_status()
    config = get_config()
    
    print("\n=== Twitter Bot Status ===")
    print(f"Running: {'Yes' if pid else 'No'}")
    if pid:
        print(f"Process ID: {pid}")
    
    if config:
        print("\nConfiguration:")
        print(f"Tweets per hour: {config['rate_limits']['tweets_per_hour']}")
        print(f"Minimum delay between actions: {config['rate_limits']['min_delay_between_actions']}s")
        print(f"Active personality: {config['personality']['active']}")
        print(f"Auto-reply enabled: {config['personality']['settings']['auto_reply']}")
        print(f"Reply probability: {config['personality']['settings']['reply_probability']}")
    
    if status:
        print("\nCurrent Status:")
        if status.get('last_tweet_time'):
            last_tweet = datetime.fromisoformat(status['last_tweet_time'])
            print(f"Last Tweet: {last_tweet.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if status.get('total_tweets'):
            print(f"\nActivity:")
            print(f"Total Tweets: {status['total_tweets']}")
            print(f"Total Replies: {status.get('total_replies', 0)}")
    
    print("\nLog file: bot_output.log")

def main():
    parser = argparse.ArgumentParser(description='Manage the Twitter Bot')
    parser.add_argument('action', choices=['start', 'stop', 'status'],
                      help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        start_bot()
    elif args.action == 'stop':
        stop_bot()
    elif args.action == 'status':
        show_status()

if __name__ == '__main__':
    main() 