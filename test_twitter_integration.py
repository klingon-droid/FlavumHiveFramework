"""Test Twitter Integration"""

import os
import time
import logging
from datetime import datetime
from platforms.twitter.handler import TwitterHandler
from utils.personality_manager import PersonalityManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_integration_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_live_twitter_interaction():
    try:
        # Initialize handlers
        personality_manager = PersonalityManager()
        twitter_handler = TwitterHandler(personality_manager)
        
        logger.info("Starting live Twitter interaction test...")
        
        try:
            # 1. Generate and post an initial tweet about FlavumHiveAI
            logger.info("Generating tweet using personality system...")
            
            # Get the active personality
            personality = twitter_handler.active_personality
            logger.info(f"Using personality: {personality['name']}")
            
            # Context for the AI to generate relevant content
            context = """
            Flavumhive AI Updates:
            - Enhanced AI-driven market analysis
            - New community engagement features
            - Cross-platform integration improvements
            - Focus on user experience and accessibility
            """
            
            # Generate tweet content using the personality
            tweet_content = twitter_handler.generate_tweet_content(
                personality=personality,
                context=context
            )
            
            if tweet_content:
                # Post the tweet
                tweet_id = twitter_handler.post_tweet(tweet_content, personality)
                logger.info(f"Posted tweet with ID: {tweet_id}")
                
                # Wait briefly to simulate natural timing
                time.sleep(3)
                
                # 2. Generate and post a follow-up tweet
                follow_up_context = "Expanding on the AI-driven market analysis capabilities..."
                follow_up_content = twitter_handler.generate_tweet_content(
                    personality=personality,
                    context=follow_up_context
                )
                
                if follow_up_content:
                    reply_id = twitter_handler.reply_to_tweet(tweet_id, follow_up_content, personality)
                    logger.info(f"Posted follow-up tweet with ID: {reply_id}")
                
                # 3. Get timeline and verify posts
                timeline = twitter_handler.get_timeline(limit=5)
                logger.info("\nRecent Timeline:")
                for tweet in timeline:
                    logger.info(f"Tweet: {tweet['content'][:100]}...")
                
                # Get statistics
                stats = twitter_handler.get_stats()
                logger.info("\nTwitter Stats:")
                logger.info(f"Total Tweets: {stats['total_tweets']}")
                logger.info(f"Total Replies: {stats['total_replies']}")
                logger.info(f"Last Activity: {stats['last_activity']}")
                
                return True, "Live Twitter interaction test completed successfully!"
            else:
                return False, "Failed to generate tweet content"
            
        except Exception as e:
            error_msg = f"Error during live Twitter interaction: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Failed to initialize Twitter handler: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    finally:
        # Ensure browser is closed
        if 'twitter_handler' in locals():
            del twitter_handler

if __name__ == "__main__":
    success, message = test_live_twitter_interaction()
    print(f"\nTest Result: {'✅ PASSED' if success else '❌ FAILED'}")
    print(f"Message: {message}") 