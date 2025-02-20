import os
import random
import logging
from datetime import datetime
import praw
from dotenv import load_dotenv
from utils.helper import get_reddit_instance, get_openai_response, is_valid_subreddit, handle_rate_limit
from utils.personality_manager import PersonalityManager

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

personality_manager = PersonalityManager()

def get_random_post(reddit: praw.Reddit, subreddit_name: str):
    """Get a random post from the subreddit"""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = list(subreddit.hot(limit=20))  # Get hot posts
        if not posts:
            logger.error(f"No posts found in subreddit {subreddit_name}")
            return None
        return random.choice(posts)
    except praw.exceptions.RedditAPIException as e:
        logger.error(f"Reddit API Error getting posts: {str(e)}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error getting random post: {str(e)}", exc_info=True)
        return None

def generate_comment_content(personality, post_content):
    """Generate comment content based on personality and post"""
    try:
        base_prompt = personality_manager.get_personality_prompt(personality, is_reply=True)
        enhanced_prompt = f"""
{base_prompt}

As {personality['name']}, engage thoughtfully with this post from your unique perspective.
You are {personality['bio'][0]} participating in an intellectual discussion with peers.
Respond naturally and conversationally, while drawing from your expertise to add value to the discussion.

The post you're responding to:
{post_content}

Remember to:
- Engage directly with the key points
- Share your unique insights based on your experience
- Maintain a natural, flowing conversation
- Draw from your specific expertise in {', '.join(personality['knowledge'][:3])}
- Keep your characteristic style: {', '.join(personality['style']['chat'])}
"""
        content = get_openai_response(enhanced_prompt)
        
        # Add personality signature at the top
        signature = f"*Perspective from **{personality['name']}** - {personality['bio'][0]}*\n\n"
        return signature + content
    except Exception as e:
        logger.error(f"Error generating comment content: {str(e)}", exc_info=True)
        return None

@handle_rate_limit
def submit_comment(post, content):
    """Submit comment with rate limit handling"""
    return post.reply(content)

def generate_comments():
    """Generate and submit comments using different personalities"""
    try:
        reddit = get_reddit_instance()
        if not reddit:
            logger.error("Failed to get Reddit instance")
            return False
            
        personality = personality_manager.get_random_personality()
        logger.info(f"Selected Personality for Comment: {personality['name']}")
        
        # Randomly select a subreddit from the personality's list
        subreddit_name = random.choice(personality['settings']['subreddits'])
        
        if not is_valid_subreddit(reddit, subreddit_name):
            logger.error(f"Subreddit {subreddit_name} is not accessible")
            return False
            
        # Get a random post to comment on
        post = get_random_post(reddit, subreddit_name)
        if not post:
            return False
            
        try:
            # Generate and submit comment
            comment_content = generate_comment_content(personality, post.selftext or post.title)
            if not comment_content:
                logger.error("Failed to generate comment content")
                return False

            comment = submit_comment(post, comment_content)
            if not comment:
                logger.error("Failed to submit comment (rate limited)")
                return False
                
            logger.info(f"Comment created by {personality['name']} on post {post.id}")
            
            # Chance for another personality to reply to this comment
            if personality_manager.should_interact(personality['name']):
                try:
                    contrasting_personality = personality_manager.get_contrasting_personality(personality['name'])
                    reply_prompt = f"""As {contrasting_personality['name']}, you're continuing this intellectual discussion.
You are {contrasting_personality['bio'][0]} engaging with a thought-provoking comment.
Respond naturally and thoughtfully, building on the conversation while offering your unique perspective.

The comment you're responding to:
{comment_content}

Remember to:
- Build on the discussion naturally
- Share your contrasting viewpoint respectfully
- Maintain the flow of conversation
- Draw from your expertise in {', '.join(contrasting_personality['knowledge'][:3])}
- Keep your characteristic style: {', '.join(contrasting_personality['style']['chat'])}"""

                    reply_content = get_openai_response(reply_prompt)
                    if reply_content:
                        # Add personality signature at the top
                        reply_content = f"*Insights from **{contrasting_personality['name']}** - {contrasting_personality['bio'][0]}*\n\n{reply_content}"
                        reply = submit_comment(comment, reply_content)
                        if reply:
                            logger.info(f"Added reply from {contrasting_personality['name']}")
                except Exception as e:
                    logger.error(f"Error creating contrasting reply: {str(e)}", exc_info=True)
            
            return True
            
        except praw.exceptions.RedditAPIException as e:
            logger.error(f"Reddit API Error posting comment: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Error in generate_comments: {str(e)}", exc_info=True)
        return False