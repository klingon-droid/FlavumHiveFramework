import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from platforms.reddit.handler import RedditHandler
from utils.personality_manager import PersonalityManager

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_live_reddit_interaction():
    try:
        # Initialize handlers
        personality_manager = PersonalityManager()
        reddit_handler = RedditHandler(personality_manager)
        
        logger.info("Starting live Reddit interaction test...")
        
        # 1. Create a meaningful post about FlavumHiveAI
        test_subreddit = "FlavumHiveAI"
        test_title = "Flavumhive AI: Latest Development Updates and Community Discussion"
        test_content = """
Hello Flavumhive community! 👋

I wanted to start a discussion about the latest developments in our AI ecosystem. Here are some key points I'd love to get your thoughts on:

1. AI-Driven Market Analysis
2. Community Engagement Features
3. Cross-Platform Integration

What aspects of Flavumhive's AI capabilities are you most excited about? What features would you like to see implemented in the near future?

Looking forward to engaging with everyone in the comments! 🤖✨
        """.strip()
        
        try:
            # Create the post
            subreddit = reddit_handler.reddit.subreddit(test_subreddit)
            test_post = subreddit.submit(title=test_title, selftext=test_content)
            post_url = f"https://reddit.com{test_post.permalink}"
            logger.info(f"Created discussion post: {post_url}")
            
            # Wait for post to be available
            time.sleep(5)
            
            # 2. Generate and add an AI response using the personality system
            logger.info("Generating AI response using personality system...")
            
            # Get the active personality
            personality = reddit_handler.active_personality
            logger.info(f"Using personality: {personality['name']}")
            
            # Generate response using the personality
            ai_response = reddit_handler.generate_comment_content(
                personality=personality,
                title=test_title,
                content=test_content
            )
            
            if ai_response:
                # Post the AI-generated comment
                comment = test_post.reply(ai_response)
                logger.info(f"Posted AI response with ID: {comment.id}")
                
                # Wait briefly to simulate natural timing
                time.sleep(3)
                
                # 3. Add a follow-up interaction
                follow_up = "Thank you for sharing these insights! Could you elaborate more on the AI-driven market analysis capabilities?"
                reply_to_ai = comment.reply(follow_up)
                logger.info("Added follow-up question to simulate user interaction")
                
                # Display interaction statistics
                logger.info("\nInteraction Summary:")
                logger.info(f"Post URL: {post_url}")
                logger.info(f"Total Comments: {test_post.num_comments}")
                logger.info(f"Post Score: {test_post.score}")
                
                # Check rate limits
                logger.info("\nRate Limit Status:")
                logger.info(f"Requests Used: {reddit_handler.reddit.auth.limits['used']}")
                logger.info(f"Requests Remaining: {reddit_handler.reddit.auth.limits['remaining']}")
                
                # Keep the post for review (don't delete)
                return True, f"Live interaction test completed successfully! View the post at: {post_url}"
            else:
                return False, "Failed to generate AI response"
            
        except Exception as e:
            error_msg = f"Error during live Reddit interaction: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Failed to initialize Reddit handler: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

if __name__ == "__main__":
    success, message = test_live_reddit_interaction()
    print(f"\nTest Result: {'✅ PASSED' if success else '❌ FAILED'}")
    print(f"Message: {message}") 