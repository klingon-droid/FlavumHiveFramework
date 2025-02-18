"""OpenAI utilities for content generation"""

import os
import logging
from openai import OpenAI
from typing import Optional

logger = logging.getLogger(__name__)

def get_openai_response(prompt: str) -> Optional[str]:
    """Get a response from OpenAI"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not client.api_key:
            logger.error("OpenAI API key not found")
            return None

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,  # Limit response length
            temperature=0.7,  # Balance between creativity and consistency
            n=1,  # Get one response
            stop=None  # No specific stop sequence
        )

        if response.choices and response.choices[0].message:
            return response.choices[0].message.content.strip()
        return None

    except Exception as e:
        logger.error(f"Error getting OpenAI response: {str(e)}")
        return None 