import os
import json
import time
import logging
from datetime import datetime

from main import MultiPlatformBot
from utils.db_init import initialize_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_test_environment():
    """Set up the test environment with required configurations"""
    logger.info("Setting up test environment")
    
    # Create test config if it doesn't exist
    if not os.path.exists("config.json"):
        test_config = {
            "target_subreddits": ["TestSubreddit"],
            "platforms": {
                "reddit": True,
                "eliza": True
            },
            "platform_rate_limits": {
                "reddit": {
                    "posts_per_day": 5,
                    "comments_per_day": 10,
                    "min_delay_between_actions": 30
                },
                "eliza": {
                    "messages_per_minute": 10,
                    "session_timeout": 300
                }
            },
            "eliza_settings": {
                "personality_mapping": {
                    "default": "therapist",
                    "therapist": {
                        "initial_message": "Hello, I'm here to help. How are you feeling today?",
                        "style": "empathetic"
                    }
                }
            }
        }
        
        with open("config.json", "w") as f:
            json.dump(test_config, f, indent=4)
        logger.info("Created test configuration file")

def verify_platform_status(bot):
    """Verify the status of all platforms"""
    logger.info("Verifying platform status")
    
    all_platforms_ok = True
    
    # Check Reddit platform
    try:
        reddit_stats = bot.platform_handlers["reddit"].get_platform_stats()
        logger.info(f"Reddit platform stats: {reddit_stats}")
    except Exception as e:
        logger.error(f"Reddit platform error: {str(e)}")
        all_platforms_ok = False
    
    # Check Eliza platform
    try:
        eliza_stats = bot.platform_handlers["eliza"].get_platform_stats()
        logger.info(f"Eliza platform stats: {eliza_stats}")
    except Exception as e:
        logger.error(f"Eliza platform error: {str(e)}")
        all_platforms_ok = False
    
    return all_platforms_ok

def test_platform_interactions(bot):
    """Test basic interactions on each platform"""
    logger.info("Testing platform interactions")
    
    # Test Reddit interactions
    try:
        reddit_handler = bot.platform_handlers["reddit"]
        reddit_handler.process_subreddits()
        logger.info("Reddit interaction test completed")
    except Exception as e:
        logger.error(f"Reddit interaction test failed: {str(e)}")
        return False
    
    # Test Eliza interactions
    try:
        eliza_handler = bot.platform_handlers["eliza"]
        session_id = eliza_handler.create_session("test_user")
        success, response = eliza_handler.process_message(session_id, "Hello")
        if success:
            logger.info(f"Eliza response: {response}")
        else:
            logger.error("Eliza message processing failed")
            return False
        eliza_handler.end_session(session_id)
        logger.info("Eliza interaction test completed")
    except Exception as e:
        logger.error(f"Eliza interaction test failed: {str(e)}")
        return False
    
    return True

def main():
    try:
        # Set up test environment
        setup_test_environment()
        
        # Initialize database
        if not initialize_db():
            logger.error("Database initialization failed")
            return
        
        # Create bot instance
        logger.info("Creating bot instance")
        bot = MultiPlatformBot()
        
        # Verify platform status
        if not verify_platform_status(bot):
            logger.error("Platform status verification failed")
            return
        
        # Test platform interactions
        if not test_platform_interactions(bot):
            logger.error("Platform interaction tests failed")
            return
        
        logger.info("All integration tests passed successfully")
        
        # Start the bot
        logger.info("Starting bot")
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Integration test stopped by user")
    except Exception as e:
        logger.error(f"Integration test failed: {str(e)}")

if __name__ == "__main__":
    main() 