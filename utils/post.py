import os
import json
import random
import logging
from datetime import datetime
import praw
from dotenv import load_dotenv
from utils.helper import get_reddit_instance, get_openai_response, handle_rate_limit, get_flairs
from utils.personality_manager import PersonalityManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

personality_manager = PersonalityManager()

def generate_post_content(personality):
    """Generate post content based on personality"""
    try:
        # Enhanced prompt to encourage more natural, flowing content
        base_prompt = personality_manager.get_personality_prompt(personality)
        enhanced_prompt = f"""
{base_prompt}

You are engaging in a thoughtful discussion about crypto and DeFi. Write a natural, insightful post that reflects your unique perspective and expertise. 
Focus on one clear topic or idea, and develop it with depth and nuance. Write as you would speak - naturally and engagingly.
Avoid listing points or numbered sections. Instead, present your thoughts in a flowing, conversational manner while maintaining your professional expertise.

Remember:
- You are {personality['name']}, {personality['bio'][0]}
- Draw from your specific knowledge in: {', '.join(personality['knowledge'])}
- Maintain your characteristic style: {', '.join(personality['style']['post'])}
- Write as if you're sharing valuable insights with peers in your field
"""
        content = get_openai_response(enhanced_prompt)
        
        # Add personality signature at the top
        signature = f"*Thoughts from **{personality['name']}** - {personality['bio'][0]}*\n\n"
        return signature + content
    except Exception as e:
        logger.error(f"Error generating post content: {str(e)}", exc_info=True)
        return None

@handle_rate_limit
def submit_post(subreddit, title, content, flair_id=None):
    """Submit post with rate limit handling"""
    return subreddit.submit(
        title=title,
        selftext=content,
        flair_id=flair_id
    )

def get_appropriate_flair(reddit, subreddit_name):
    """Get an appropriate flair for the subreddit"""
    flairs = get_flairs(reddit, subreddit_name)
    if not flairs:
        return None
        
    # Priority flairs to use (in order of preference)
    preferred_flairs = ['discussion', 'general', 'strategy', 'analysis', 'opinion']
    
    # Try to find a preferred flair
    for preferred in preferred_flairs:
        for flair in flairs:
            if preferred.lower() in flair['flair_text'].lower():
                logger.info(f"Using flair: {flair['flair_text']}")
                return flair['flair_id']
    
    # If no preferred flair found, use the first available one
    logger.info(f"Using default flair: {flairs[0]['flair_text']}")
    return flairs[0]['flair_id']

def generate_title(content, personality):
    """Generate a natural title without [Discussion] prefix"""
    try:
        prompt = f"""As {personality['name']}, create a brief, engaging title for this post. 
The title should naturally reflect your expertise as {personality['bio'][0]}.
Make it conversational and intriguing, avoiding mechanical formats.

The post content is:
{content}"""
        title = get_openai_response(prompt)
        return title[:300]  # Reddit title length limit
    except Exception as e:
        logger.error(f"Error generating title: {str(e)}", exc_info=True)
        return content[:100] + "..."

def generate_posts():
    """Generate and submit posts using different personalities"""
    try:
        reddit = get_reddit_instance()
        if not reddit:
            logger.error("Failed to get Reddit instance")
            return None
            
        personality = personality_manager.get_random_personality()
        
        # Log which personality is posting
        logger.info(f"Selected Personality: {personality['name']}")
        
        # Randomly select a subreddit from the personality's list
        subreddit_name = random.choice(personality['settings']['subreddits'])
        subreddit = reddit.subreddit(subreddit_name)
        
        logger.info(f"Posting in: r/{subreddit_name}")
        
        # Generate and submit post
        post_content = generate_post_content(personality)
        if not post_content:
            logger.error("Failed to generate post content")
            return None

        try:
            # Generate a natural title
            title = generate_title(post_content, personality)
            
            # Get appropriate flair for the subreddit
            flair_id = get_appropriate_flair(reddit, subreddit_name)
            
            # Submit post with flair if available
            submission = submit_post(subreddit, title, post_content, flair_id)
            
            if not submission:
                logger.error("Failed to submit post (rate limited)")
                return None
                
            logger.info(f"Post created by {personality['name']}: {submission.id}")
            
            # If we should create an interaction, generate a comment from another personality
            if personality_manager.should_interact(personality['name']):
                try:
                    contrasting_personality = personality_manager.get_contrasting_personality(personality['name'])
                    comment_prompt = f"""As {contrasting_personality['name']}, engage thoughtfully with this post from your unique perspective.
You are {contrasting_personality['bio'][0]}, and you're having an intellectual discussion with a peer.
Respond naturally and conversationally, while drawing from your expertise to add value to the discussion.

The post you're responding to:
{post_content}

Remember to:
- Engage directly with the key points
- Share your unique insights
- Maintain a natural, flowing conversation
- Draw from your specific expertise in {', '.join(contrasting_personality['knowledge'][:3])}"""

                    comment_content = get_openai_response(comment_prompt)
                    if comment_content:
                        # Add personality signature at the top
                        comment_content = f"*Response from **{contrasting_personality['name']}** - {contrasting_personality['bio'][0]}*\n\n{comment_content}"
                        submission.reply(comment_content)
                        logger.info(f"Added comment from {contrasting_personality['name']}")
                except Exception as e:
                    logger.error(f"Error creating contrasting comment: {str(e)}", exc_info=True)
            
            return submission
            
        except praw.exceptions.RedditAPIException as e:
            logger.error(f"Reddit API Error: {str(e)}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error submitting post: {str(e)}", exc_info=True)
            return None
            
    except Exception as e:
        logger.error(f"Error in generate_posts: {str(e)}", exc_info=True)
        return None