import json
import time
import threading
import os
import sys
import argparse
from datetime import datetime
import logging
from typing import Dict, List
from dotenv import load_dotenv, find_dotenv

from utils.db_init import init_database
from utils.post import generate_posts
from utils.comment import generate_comments
from utils.personality_manager import PersonalityManager
from platforms.reddit.handler import RedditHandler
from platforms.eliza.handler import ElizaHandler

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
logger.info("Loading environment variables...")
env_path = find_dotenv()
logger.info(f"Found .env file at: {env_path}")
load_dotenv(env_path)

# Log all relevant environment variables (without sensitive data)
logger.info("Environment variable presence check:")
for var in ['DB_PATH', 'REDDIT_CLIENT_ID', 'REDDIT_USERNAME', 'OPENAI_API_KEY']:
    logger.info(f"{var} present: {bool(os.getenv(var))}")

# Set up database path
DB_PATH = os.getenv("DB_PATH", "bot.db")
logger.info(f"Using database path: {DB_PATH}")
logger.info(f"Database file exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    logger.info(f"Database file permissions: {oct(os.stat(DB_PATH).st_mode)[-3:]}")

class MultiPlatformBot:
    def __init__(self, config_path: str = "config.json"):
        logger.info("Initializing MultiPlatformBot")
        
        # Initialize database
        logger.info("Initializing database")
        init_database(db_path=DB_PATH, force_recreate=True)
        
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise
        
        # Initialize components
        try:
            self.personality_manager = PersonalityManager()
            logger.info("Personality manager initialized")
            
            self.platform_handlers = {}
            self.initialize_platforms()
            logger.info(f"Initialized platforms: {list(self.platform_handlers.keys())}")
            
            # Flag to control the bot's running state
            self.running = True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            raise

    def initialize_platforms(self):
        """Initialize enabled platform handlers"""
        if self.config['platforms'].get('reddit', {}).get('enabled', False):
            try:
                self.platform_handlers['reddit'] = RedditHandler(self.personality_manager)
                logger.info("Reddit platform initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit platform: {str(e)}")
                raise

        if self.config['platforms'].get('eliza', {}).get('enabled', False):
            try:
                self.platform_handlers['eliza'] = ElizaHandler()
                logger.info("Eliza platform initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Eliza platform: {str(e)}")
                raise

    def run_platform(self, platform_name: str):
        """Run a specific platform's main loop"""
        handler = self.platform_handlers.get(platform_name)
        if not handler:
            logger.error(f"Platform {platform_name} not initialized")
            return

        logger.info(f"Starting {platform_name} platform loop")
        
        while self.running:
            try:
                if platform_name == 'reddit':
                    # Get Reddit-specific config
                    reddit_config = self.config['platforms']['reddit']
                    commenters_config = reddit_config.get('commenters', {})
                    
                    # Process subreddits with commenter configuration
                    handler.process_subreddits(commenters_config)
                elif platform_name == 'eliza':
                    handler.cleanup_inactive_sessions()
                
                # Get platform-specific rate limits
                rate_limits = self.config['platforms'][platform_name].get('rate_limits', {})
                delay = rate_limits.get('min_delay_between_actions', 30)
                
                # Sleep for the configured delay
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error in {platform_name} platform loop: {str(e)}")
                if self.running:  # Only sleep if we're still meant to be running
                    time.sleep(60)  # Wait a minute before retrying

    def start(self):
        """Start all enabled platforms in separate threads"""
        threads = []
        
        for platform_name in self.platform_handlers.keys():
            thread = threading.Thread(
                target=self.run_platform,
                args=(platform_name,),
                name=f"{platform_name}_thread"
            )
            thread.daemon = True  # Make thread daemon so it exits when main thread exits
            thread.start()
            threads.append(thread)
            logger.info(f"Started {platform_name} platform thread")

        try:
            # Keep the main thread alive and handle keyboard interrupt
            while True:
                # Check if all threads are alive
                for thread in threads:
                    if not thread.is_alive():
                        logger.error(f"Thread {thread.name} died unexpectedly")
                        # Restart the thread if it died
                        if self.running:
                            new_thread = threading.Thread(
                                target=self.run_platform,
                                args=(thread.name.replace('_thread', ''),),
                                name=thread.name
                            )
                            new_thread.daemon = True
                            new_thread.start()
                            threads.remove(thread)
                            threads.append(new_thread)
                            logger.info(f"Restarted {thread.name}")
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.running = False  # Signal threads to stop
            logger.info("Waiting for threads to finish...")
            # Wait for threads to finish their current iteration
            for thread in threads:
                thread.join(timeout=10)
            logger.info("Bot shutdown complete")

    def stop(self):
        """Stop the bot gracefully"""
        self.running = False

def main():
    parser = argparse.ArgumentParser(description='FlavumHive Social Media Bot')
    parser.add_argument('--platform', type=str, required=True, choices=['reddit', 'twitter'],
                      help='Platform to run the bot on')
    args = parser.parse_args()

    try:
        bot = MultiPlatformBot()
        if args.platform == 'reddit':
            logger.info("Starting Reddit bot...")
            bot.start()  # This will run until interrupted
        else:
            logger.error(f"Platform {args.platform} not yet implemented")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
