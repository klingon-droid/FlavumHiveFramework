import os
import time
import random
import logging
import signal
import sys
import json
from datetime import datetime, timedelta

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_bot.log'),
        logging.StreamHandler()
    ]
)

# Initialize logger
logger = logging.getLogger(__name__)

# Diagnostic Information
logger.info("=== Startup Diagnostics ===")
logger.info("Python Version: %s", sys.version)
logger.info("Python Executable: %s", sys.executable)
logger.info("Python Path: %s", os.pathsep.join(sys.path))
logger.info("Working Directory: %s", os.getcwd())
logger.info("Script Location: %s", os.path.abspath(__file__))

# Virtual Environment Check
venv_path = os.environ.get('VIRTUAL_ENV')
logger.info("Virtual Environment: %s", venv_path if venv_path else "Not activated")

# Directory Structure Check
expected_dirs = ['platforms', 'utils']
for dir_name in expected_dirs:
    dir_path = os.path.join(os.path.dirname(__file__), dir_name)
    logger.info("Directory '%s' exists: %s", dir_name, os.path.exists(dir_path))

# Test env file loading
try:
    from dotenv import load_dotenv
    logger.info("Attempting to load .env file...")
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    logger.info(".env file exists: %s", os.path.exists(env_path))
    load_dotenv()
    logger.info("Environment after load_dotenv:")
    logger.info("TWITTER_USERNAME present: %s", bool(os.getenv('TWITTER_USERNAME')))
    logger.info("TWITTER_PASSWORD present: %s", bool(os.getenv('TWITTER_PASSWORD')))
    logger.info("TWITTER_EMAIL present: %s", bool(os.getenv('TWITTER_EMAIL')))
except Exception as e:
    logger.error("Error loading .env: %s", str(e))

# Test dependency availability and versions
try:
    logger.info("=== Dependency Check ===")
    packages_to_check = ['selenium', 'webdriver_manager', 'psutil', 'openai', 'python-dotenv']
    for package in packages_to_check:
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'unknown')
            logger.info(f"✓ {package} is available (version: {version})")
        except ImportError as e:
            logger.error(f"✗ {package} is missing: {str(e)}")
except Exception as e:
    logger.error("Error checking packages: %s", str(e))

logger.info("=== End Startup Diagnostics ===")

# Continue with the rest of the original imports
try:
    from platforms.twitter.handler import TwitterHandler
    from utils.personality_manager import PersonalityManager
except Exception as e:
    logger.error("Error importing project modules: %s", str(e))

class ContinuousTwitterBot:
    def __init__(self):
        self.running = True
        self.personality_manager = PersonalityManager()
        self.twitter_handler = None
        self.last_tweet_time = None
        self.status_file = 'bot_status.json'
        
        # Load config
        self.config = self._load_config()
        
        # Set rate limits from config
        self.tweets_per_hour = self.config['platforms']['twitter']['rate_limits']['tweets_per_hour']
        self.min_delay = self.config['platforms']['twitter']['rate_limits']['min_delay_between_actions']
        
        # Calculate intervals based on rate limits
        self.min_interval = max(3600 // self.tweets_per_hour, self.min_delay)  # Ensure we don't exceed tweets_per_hour
        self.max_interval = self.min_interval * 2  # Double the min interval for max
        
        # Load or create status file
        self.load_status()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def _load_config(self, config_path: str = "config.json") -> dict:
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info("Successfully loaded config")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise

    def load_status(self):
        """Load bot status from file"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    last_tweet = status.get('last_tweet_time')
                    if last_tweet:
                        self.last_tweet_time = datetime.fromisoformat(last_tweet)
        except Exception as e:
            logger.error(f"Error loading status: {str(e)}")

    def save_status(self):
        """Save bot status to file"""
        try:
            status = {
                'last_tweet_time': self.last_tweet_time.isoformat() if self.last_tweet_time else None,
                'is_running': self.running,
                'tweets_per_hour': self.tweets_per_hour,
                'min_delay': self.min_delay,
                'current_min_interval': self.min_interval,
                'current_max_interval': self.max_interval
            }
            with open(self.status_file, 'w') as f:
                json.dump(status, f)
        except Exception as e:
            logger.error(f"Error saving status: {str(e)}")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal. Cleaning up...")
        self.running = False
        self.save_status()
        if self.twitter_handler:
            logger.info("Closing Twitter handler...")
            del self.twitter_handler
        logger.info("Shutdown complete")
        sys.exit(0)

    def initialize_twitter_handler(self):
        """Initialize or reinitialize the Twitter handler with error handling"""
        try:
            if self.twitter_handler:
                del self.twitter_handler
            
            logger.info("Initializing Twitter handler...")
            self.twitter_handler = TwitterHandler(self.personality_manager)
            logger.info("Twitter handler initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Twitter handler: {str(e)}")
            return False

    def get_next_tweet_delay(self):
        """Calculate delay until next tweet with some randomness"""
        base_delay = random.randint(self.min_interval, self.max_interval)
        jitter = random.uniform(-self.min_delay/2, self.min_delay/2)  # Add jitter within min_delay bounds
        return max(self.min_interval, base_delay + jitter)

    def should_post_tweet(self):
        """Determine if it's time to post a new tweet"""
        if not self.last_tweet_time:
            return True
        
        elapsed = (datetime.now() - self.last_tweet_time).total_seconds()
        return elapsed >= self.get_next_tweet_delay()

    def get_stats(self):
        """Get bot statistics"""
        stats = {
            'running': self.running,
            'last_tweet_time': self.last_tweet_time.isoformat() if self.last_tweet_time else None,
            'tweets_per_hour': self.tweets_per_hour,
            'min_delay_seconds': self.min_delay,
            'current_min_interval': self.min_interval,
            'current_max_interval': self.max_interval
        }
        if self.twitter_handler:
            twitter_stats = self.twitter_handler.get_stats()
            stats.update(twitter_stats)
        return stats

    def run(self):
        """Main loop for continuous operation"""
        retry_delay = 300  # 5 minutes between retries on failure
        max_retries = 3
        
        logger.info("Starting continuous Twitter bot...")
        logger.info(f"Rate limits: {self.tweets_per_hour} tweets/hour, {self.min_delay}s min delay")
        logger.info(f"Posting interval: {self.min_interval/3600:.1f}-{self.max_interval/3600:.1f} hours")
        
        while self.running:
            try:
                # Initialize handler if needed
                if not self.twitter_handler:
                    if not self.initialize_twitter_handler():
                        logger.error("Failed to initialize Twitter handler. Retrying in 5 minutes...")
                        time.sleep(retry_delay)
                        continue

                # Check if it's time to post
                if self.should_post_tweet():
                    retries = 0
                    success = False
                    
                    while retries < max_retries and not success and self.running:
                        try:
                            # Get active personality
                            personality = self.twitter_handler.active_personality
                            logger.info(f"Using personality: {personality['name']}")
                            
                            # Generate and post tweet
                            tweet_content = self.twitter_handler.generate_tweet_content(
                                personality=personality,
                                context="Latest developments in AI, DeFi, and blockchain technology"
                            )
                            
                            if tweet_content:
                                tweet_id = self.twitter_handler.post_tweet(tweet_content, personality)
                                if tweet_id:
                                    logger.info(f"Successfully posted tweet with ID: {tweet_id}")
                                    self.last_tweet_time = datetime.now()
                                    self.save_status()
                                    success = True
                                    
                                    # Wait briefly before potential follow-up
                                    time.sleep(random.uniform(self.min_delay, self.min_delay * 2))
                                    
                                    # Check reply probability from config
                                    reply_prob = self.config['platforms']['twitter']['personality']['settings']['reply_probability']
                                    if random.random() < reply_prob and self.running:
                                        follow_up = self.twitter_handler.generate_reply_content(
                                            personality=personality,
                                            tweet_content=tweet_content
                                        )
                                        if follow_up:
                                            reply_id = self.twitter_handler.reply_to_tweet(
                                                tweet_id=tweet_id,
                                                content=follow_up,
                                                personality=personality
                                            )
                                            if reply_id:
                                                logger.info(f"Posted follow-up tweet with ID: {reply_id}")
                            
                            if not success:
                                retries += 1
                                if retries < max_retries:
                                    logger.warning(f"Retry {retries}/{max_retries} after {self.min_delay} seconds...")
                                    time.sleep(self.min_delay)
                        except Exception as e:
                            logger.error(f"Error during tweet posting: {str(e)}")
                            retries += 1
                            if retries < max_retries:
                                logger.warning(f"Retry {retries}/{max_retries} after {self.min_delay} seconds...")
                                time.sleep(self.min_delay)
                            else:
                                logger.error("Max retries reached. Reinitializing Twitter handler...")
                                self.twitter_handler = None
                
                # Sleep before next check
                sleep_time = min(300, self.min_delay)  # Check at least every 5 minutes or min_delay
                logger.debug(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {str(e)}")
                logger.info(f"Sleeping for {retry_delay} seconds before retry...")
                time.sleep(retry_delay)

if __name__ == "__main__":
    bot = ContinuousTwitterBot()
    bot.run() 