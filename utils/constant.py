import openai
from dotenv import load_dotenv
import os
import random
import re

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_post_content(prompt, subreddit, max_tokens=200):
    content_prompt = f"{prompt} Create an engaging post for r/{subreddit}. The post should be natural, informative, and spark discussion. Write 4-5 sentences in a conversational style."
    content = openAI_generate(content_prompt, max_tokens)
    if content:
        content = content.replace('"', '')
    return content

def generate_post_title(post_content, max_tokens=50):
    title_prompt = f"Create a brief, engaging Reddit post title (max 300 characters) for this content:\n\n{post_content}\n\nTitle:"
    title = openAI_generate(title_prompt, max_tokens)
    if title:
        title = title.replace('"', '').strip()
        # Remove "Title:" if it was included in the response
        title = re.sub(r'^(Title:\s*)', '', title)
    return title

def generate_comment(prompt, post_context, max_tokens=150):
    combined_prompt = f"This is your personality:\n\n{prompt}\n\nRespond to this post:\n\n{post_context}\n\nWrite a natural, engaging comment that fits your personality."
    content = openAI_generate(combined_prompt, max_tokens)
    if content:
        content = content.replace('"', '')
    return content

def openAI_generate(prompt, max_tokens=150):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",  
            messages=[
                {"role": "system", "content": "You are a helpful Reddit community member who creates engaging, natural content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  
            max_tokens=max_tokens  
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating content: {e}")
        return None