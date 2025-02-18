import json
import time
import threading
import os
from datetime import datetime
import logging
from typing import Dict, List
from dotenv import load_dotenv

from utils.db_init import initialize_db
from utils.post import generate_posts
from utils.comment import generate_comments
from utils.personality_manager import PersonalityManager
from platforms.reddit.handler import RedditHandler
from platforms.eliza.handler import ElizaHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MultiPlatformBot:
    def __init__(self, config_path: str = "config.json"):
        logger.info("Initializing MultiPlatformBot")
        
        # Load environment variables
        if os.path.exists(".env"):
            logger.info("Loading environment variables from .env")
            load_dotenv()
        else:
            logger.warning("No .env file found")
        
        # Initialize database
        logger.info("Initializing database")
        if not initialize_db():
            raise RuntimeError("Failed to initialize database")
        
        # Load configuration
        try:
            self.config = self._load_config(config_path)
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
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            raise

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return json.load(f)

    def initialize_platforms(self):
        """Initialize enabled platform handlers"""
        if self.config['platforms'].get('reddit', False):
            try:
                self.platform_handlers['reddit'] = RedditHandler(self.personality_manager)
                logger.info("Reddit platform initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit platform: {str(e)}")
                raise

        if self.config['platforms'].get('eliza', False):
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
        
        while True:
            try:
                if platform_name == 'reddit':
                    handler.process_subreddits()
                elif platform_name == 'eliza':
                    handler.cleanup_inactive_sessions()
                
                # Get platform-specific rate limits
                rate_limits = self.config['platform_rate_limits'].get(platform_name, {})
                delay = rate_limits.get('min_delay_between_actions', 30)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error in {platform_name} platform loop: {str(e)}")
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
            thread.daemon = True
            thread.start()
            threads.append(thread)
            logger.info(f"Started {platform_name} platform thread")

        try:
            # Keep the main thread alive
            while True:
                # Check if all threads are alive
                for thread in threads:
                    if not thread.is_alive():
                        logger.error(f"Thread {thread.name} died unexpectedly")
                        # You might want to restart the thread here
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            # Implement graceful shutdown logic here if needed

def main():
    try:
        bot = MultiPlatformBot()
        bot.start()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
