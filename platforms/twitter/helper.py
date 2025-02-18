"""Twitter Helper utilities"""

import logging
import pyotp
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .tweet import Tweet

logger = logging.getLogger(__name__)

class TwitterHelper:
    """Helper class for Twitter operations"""
    
    def handle_2fa(self, driver: webdriver.Chrome, twofa_secret: str):
        """Handle two-factor authentication"""
        try:
            # Wait for 2FA input field
            twofa_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            
            # Generate 2FA code
            totp = pyotp.TOTP(twofa_secret)
            code = totp.now()
            
            # Enter 2FA code
            twofa_input.send_keys(code)
            twofa_input.send_keys(Keys.RETURN)
            
            # Wait for successful 2FA
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ARIA_LABEL, "Home timeline"))
            )
            
        except TimeoutException:
            raise Exception("2FA verification failed")
        except Exception as e:
            raise Exception(f"Error during 2FA: {str(e)}")

    def send_tweet(self, driver: webdriver.Chrome, tweet: Tweet) -> Optional[str]:
        """Send a new tweet"""
        try:
            # Click tweet button
            tweet_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[@href='/compose/tweet']"))
            )
            tweet_button.click()
            
            # Wait for tweet input
            tweet_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )
            
            # Enter tweet content
            tweet_input.send_keys(tweet.content)
            
            # Handle media attachments if any
            if tweet.media_urls:
                self._attach_media(driver, tweet.media_urls)
            
            # Click post button
            post_button = driver.find_element(By.XPATH, "//span[text()='Post']")
            post_button.click()
            
            # Wait for tweet to be posted and get its ID
            try:
                tweet_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweet']"))
                )
                return tweet_element.get_attribute('data-tweet-id')
            except TimeoutException:
                logger.error("Failed to get tweet ID after posting")
                return None
            
        except Exception as e:
            logger.error(f"Error sending tweet: {str(e)}")
            return None

    def _attach_media(self, driver: webdriver.Chrome, media_urls: List[str]):
        """Attach media to tweet"""
        try:
            # Find media upload input
            media_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            
            # Upload each media file
            for url in media_urls:
                media_input.send_keys(url)
                
                # Wait for upload to complete
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='mediaPreview']"))
                )
        except Exception as e:
            logger.error(f"Error attaching media: {str(e)}")
            raise

    def get_timeline(self, driver: webdriver.Chrome, limit: int = 10) -> List[Dict]:
        """Get recent tweets from timeline"""
        tweets = []
        try:
            # Navigate to home timeline
            driver.get('https://twitter.com/home')
            
            # Wait for tweets to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweet']"))
            )
            
            # Scroll to load more tweets if needed
            last_height = driver.execute_script("return document.body.scrollHeight")
            while len(tweets) < limit:
                # Get tweet elements
                tweet_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='tweet']")
                
                for element in tweet_elements:
                    if len(tweets) >= limit:
                        break
                        
                    try:
                        tweet_data = self._extract_tweet_data(element)
                        if tweet_data:
                            tweets.append(tweet_data)
                    except Exception as e:
                        logger.error(f"Error extracting tweet data: {str(e)}")
                        continue
                
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content
                try:
                    WebDriverWait(driver, 5).until(lambda driver: 
                        driver.execute_script("return document.body.scrollHeight") > last_height
                    )
                    last_height = driver.execute_script("return document.body.scrollHeight")
                except TimeoutException:
                    break
            
            return tweets[:limit]
            
        except Exception as e:
            logger.error(f"Error getting timeline: {str(e)}")
            return []

    def _extract_tweet_data(self, tweet_element) -> Optional[Dict]:
        """Extract data from a tweet element"""
        try:
            tweet_id = tweet_element.get_attribute('data-tweet-id')
            username = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']").text
            content = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']").text
            
            # Get media if present
            media_urls = []
            try:
                media_elements = tweet_element.find_elements(By.CSS_SELECTOR, "img[alt='Image']")
                media_urls = [img.get_attribute('src') for img in media_elements]
            except NoSuchElementException:
                pass
            
            return {
                'tweet_id': tweet_id,
                'username': username,
                'content': content,
                'media_urls': media_urls
            }
        except Exception as e:
            logger.error(f"Error extracting tweet data: {str(e)}")
            return None

    def reply_to_tweet(self, driver: webdriver.Chrome, tweet_id: str, content: str) -> Optional[str]:
        """Reply to a specific tweet"""
        try:
            # Navigate to tweet
            driver.get(f'https://twitter.com/i/status/{tweet_id}')
            
            # Wait for reply button
            reply_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reply']"))
            )
            reply_button.click()
            
            # Wait for reply input
            reply_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )
            
            # Enter reply content
            reply_input.send_keys(content)
            
            # Click reply button
            reply_button = driver.find_element(By.XPATH, "//span[text()='Reply']")
            reply_button.click()
            
            # Wait for reply to be posted and get its ID
            try:
                reply_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweet']"))
                )
                return reply_element.get_attribute('data-tweet-id')
            except TimeoutException:
                logger.error("Failed to get reply ID after posting")
                return None
            
        except Exception as e:
            logger.error(f"Error replying to tweet: {str(e)}")
            return None 