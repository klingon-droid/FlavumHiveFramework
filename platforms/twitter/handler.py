"""Twitter Platform Handler"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import random

from utils.db_utils import init_db_connection
from utils.personality_manager import PersonalityManager
from utils.openai_utils import get_openai_response
from .tweet import Tweet

logger = logging.getLogger(__name__)

# Add diagnostic logging for imports
def _check_dependency(module_name: str):
    try:
        __import__(module_name)
        logger.info(f"Successfully imported {module_name}")
        return True
    except ImportError as e:
        logger.error(f"Failed to import {module_name}: {str(e)}")
        return False

class TwitterHandler:
    """Handler for Twitter platform interactions"""
    
    def __init__(self, personality_manager: PersonalityManager, config_path: str = "config.json"):
        """Initialize Twitter handler"""
        logger.info("Initializing Twitter handler")
        
        # Check dependencies before proceeding
        logger.info("Checking critical dependencies...")
        dependencies = [
            'selenium',
            'webdriver_manager',
            'psutil',
            'openai'
        ]
        missing_deps = [dep for dep in dependencies if not _check_dependency(dep)]
        if missing_deps:
            raise ImportError(f"Missing required dependencies: {', '.join(missing_deps)}")
        
        # Log Python version and environment
        import sys
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Operating system: {sys.platform}")
        
        # Log environment variables (safely)
        logger.info("Environment variable check:")
        env_vars = ['TWITTER_USERNAME', 'TWITTER_PASSWORD', 'TWITTER_EMAIL', 'TWITTER_DRY_RUN']
        for var in env_vars:
            logger.info(f"{var} is {'set' if os.getenv(var) else 'not set'}")
        
        # Log current working directory and permissions
        logger.info(f"Current working directory: {os.getcwd()}")
        try:
            logger.info(f"Current directory permissions: {oct(os.stat('.').st_mode)[-3:]}")
        except Exception as e:
            logger.error(f"Failed to get directory permissions: {str(e)}")
        
        try:
            self.config = self._load_config(config_path)
            if not self.config['platforms']['twitter']['enabled']:
                raise ValueError("Twitter platform is not enabled in config")
            logger.info("Config loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise

        self.personality_manager = personality_manager
        self.db_path = os.getenv("DB_PATH", self.config['global_settings']['database']['path'])
        self.last_tweet_time = None
        self.last_reply_time = None
        self.dry_run = os.getenv('TWITTER_DRY_RUN', str(self.config['global_settings']['dry_run'])).lower() == 'true'
        
        # Load active personality
        self.active_personality = None
        self._load_active_personality()
        
        if self.dry_run:
            logger.info("Running in DRY RUN mode - no actual tweets will be posted")
        
        # Initialize database tables
        self._init_db()
        
        try:
            # Log environment variables (without sensitive data)
            env_vars = {
                'TWITTER_USERNAME': bool(os.getenv('TWITTER_USERNAME')),
                'TWITTER_PASSWORD': bool(os.getenv('TWITTER_PASSWORD')),
                'TWITTER_EMAIL': bool(os.getenv('TWITTER_EMAIL'))
            }
            logger.info(f"Environment variables present: {env_vars}")
            
            # Check for existing Chrome processes
            import psutil
            chrome_processes = [p for p in psutil.process_iter(['name']) if 'chrome' in p.info['name'].lower()]
            logger.info(f"Existing Chrome processes: {len(chrome_processes)}")
            
            # Initialize browser session
            logger.info("Starting browser initialization...")
            self.driver = self._init_browser()
            
            # Verify driver session
            if self.driver.session_id:
                logger.info(f"Driver session created successfully: {self.driver.session_id}")
            else:
                logger.error("Driver session creation failed")
                raise Exception("Failed to create driver session")
            
            self._login()
            logger.info("Twitter authentication successful")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            if hasattr(self, 'driver'):
                try:
                    # Get any available browser logs
                    logs = self.driver.get_log('browser')
                    logger.error(f"Browser logs before quit:\n{logs}")
                except:
                    pass
                self.driver.quit()
            raise

    def _load_active_personality(self):
        """Load the active personality from config"""
        try:
            personality_name = self.config['platforms']['twitter']['personality']['active']
            if not personality_name:
                logger.warning("No active personality configured in config.json")
                return
                
            self.active_personality = self.personality_manager.get_personality(personality_name)
            if self.active_personality:
                logger.info(f"Loaded active personality: {personality_name}")
            else:
                logger.error(f"Failed to load configured personality: {personality_name}")
        except Exception as e:
            logger.error(f"Error loading active personality: {str(e)}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        logger.debug(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)

    def _init_browser(self) -> webdriver.Chrome:
        """Initialize Chrome browser with enhanced anti-detection measures"""
        try:
            # Get Chrome version first
            chrome_version = None
            try:
                import subprocess
                chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                chrome_version = subprocess.check_output([chrome_path, '--version']).decode('utf-8').strip()
                chrome_version = chrome_version.split()[-1]  # Get just the version number
                logger.info(f"Chrome version: {chrome_version}")
            except Exception as e:
                logger.error(f"Failed to get Chrome version: {str(e)}")

            # Initialize ChromeDriver with specific version
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                chromedriver_path = ChromeDriverManager().install()
                logger.info(f"ChromeDriver path: {chromedriver_path}")
            except Exception as e:
                logger.error(f"Failed to get ChromeDriver: {str(e)}")
                raise

            # Log system resources
            import psutil
            process = psutil.Process()
            logger.info(f"Current process memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            logger.info(f"Current process CPU usage: {process.cpu_percent()}%")
            logger.info(f"System memory available: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")

            # Clean up existing Chrome processes
            try:
                for proc in psutil.process_iter(['name']):
                    if 'chrome' in proc.info['name'].lower():
                        try:
                            proc.terminate()
                            logger.info(f"Terminated existing Chrome process: {proc.pid}")
                        except:
                            pass
                time.sleep(2)  # Wait for processes to clean up
            except Exception as e:
                logger.error(f"Failed to clean up Chrome processes: {str(e)}")

            chrome_options = Options()
            
            # Essential Chrome flags for stability
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # Enhanced stealth settings
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Session stability improvements
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # Connection stability
            chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            chrome_options.add_argument('--disable-site-isolation-trials')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--disable-web-security')
            
            # Performance improvements
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            
            # Mimic real browser behavior
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            
            # Add realistic user agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
            
            # Add language and locale
            chrome_options.add_argument('--lang=en-US')
            chrome_options.add_argument('--accept-lang=en-US')
            
            # Log all Chrome flags being used
            logger.info("Chrome flags being used:")
            for arg in chrome_options.arguments:
                logger.info(f"  {arg}")
            
            # Create service with specific executable path
            service = Service(executable_path=chromedriver_path)
            
            # Initialize driver with keep alive and extended timeout
            chrome_options.add_experimental_option("detach", True)  # Keep browser open
            chrome_options.add_experimental_option('w3c', True)  # Enable W3C mode
            
            # Add performance logging
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set connection and page load timeouts
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            # Set window size
            driver.set_window_size(1920, 1080)
            
            # Execute stealth scripts
            self._apply_stealth_scripts(driver)
            
            # Verify driver is responsive
            try:
                driver.current_url
                logger.info("Driver is responsive")
                
                # Additional session verification
                session_id = driver.session_id
                logger.info(f"Session ID: {session_id}")
                
                # Test basic interaction
                driver.execute_script("return navigator.userAgent;")
                logger.info("JavaScript execution test passed")
                
            except Exception as e:
                logger.error(f"Driver is not responsive: {str(e)}")
                raise
            
            logger.info("Chrome browser initialized with enhanced stealth measures")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome browser: {str(e)}")
            import traceback
            logger.error(f"Full error traceback:\n{traceback.format_exc()}")
            raise

    def _apply_stealth_scripts(self, driver: webdriver.Chrome):
        """Apply various stealth scripts to make automation harder to detect"""
        try:
            # Override navigator properties
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                "platform": "MacIntel",
                "acceptLanguage": "en-US,en;q=0.9"
            })
            
            # Execute stealth scripts
            stealth_scripts = [
                # Remove webdriver property
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });",
                
                # Add language props
                "Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });",
                
                # Add chrome props
                """
                window.chrome = {
                    app: {
                        isInstalled: false,
                        InstallState: {
                            DISABLED: 'disabled',
                            INSTALLED: 'installed',
                            NOT_INSTALLED: 'not_installed'
                        },
                        RunningState: {
                            CANNOT_RUN: 'cannot_run',
                            READY_TO_RUN: 'ready_to_run',
                            RUNNING: 'running'
                        }
                    },
                    runtime: {
                        OnInstalledReason: {
                            CHROME_UPDATE: 'chrome_update',
                            INSTALL: 'install',
                            SHARED_MODULE_UPDATE: 'shared_module_update',
                            UPDATE: 'update'
                        },
                        OnRestartRequiredReason: {
                            APP_UPDATE: 'app_update',
                            OS_UPDATE: 'os_update',
                            PERIODIC: 'periodic'
                        },
                        PlatformArch: {
                            ARM: 'arm',
                            ARM64: 'arm64',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformNaclArch: {
                            ARM: 'arm',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformOs: {
                            ANDROID: 'android',
                            CROS: 'cros',
                            LINUX: 'linux',
                            MAC: 'mac',
                            OPENBSD: 'openbsd',
                            WIN: 'win'
                        },
                        RequestUpdateCheckStatus: {
                            NO_UPDATE: 'no_update',
                            THROTTLED: 'throttled',
                            UPDATE_AVAILABLE: 'update_available'
                        }
                    }
                };
                """,
                
                # Add permissions API
                """
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                """
            ]
            
            for script in stealth_scripts:
                driver.execute_script(script)
                
        except Exception as e:
            logger.error(f"Failed to apply stealth scripts: {str(e)}")

    def _add_random_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add a random delay to simulate human behavior"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def _init_db(self):
        """Initialize database tables for Twitter"""
        conn = init_db_connection(self.db_path)
        try:
            c = conn.cursor()
            
            # Create tweets table
            c.execute('''CREATE TABLE IF NOT EXISTS tweets
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         tweet_id TEXT UNIQUE,
                         content TEXT,
                         username TEXT,
                         personality_id TEXT,
                         personality_context TEXT,  -- JSON string of personality context
                         timestamp DATETIME)''')
            
            # Create interactions table
            c.execute('''CREATE TABLE IF NOT EXISTS tweet_interactions
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         tweet_id TEXT,
                         interaction_type TEXT,
                         username TEXT,
                         personality_id TEXT,
                         personality_context TEXT,  -- JSON string of personality context
                         timestamp DATETIME,
                         FOREIGN KEY(tweet_id) REFERENCES tweets(tweet_id))''')
            
            # Create personality stats table
            c.execute('''CREATE TABLE IF NOT EXISTS personality_stats
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         personality_id TEXT UNIQUE,
                         total_tweets INTEGER DEFAULT 0,
                         total_replies INTEGER DEFAULT 0,
                         last_tweet_time DATETIME,
                         last_reply_time DATETIME)''')
            
            conn.commit()
        finally:
            conn.close()

    def _login(self):
        """Login to Twitter using credentials"""
        username = os.getenv('TWITTER_USERNAME')
        password = os.getenv('TWITTER_PASSWORD')
        email = os.getenv('TWITTER_EMAIL')

        if not all([username, password, email]):
            raise ValueError("Missing required Twitter credentials")

        try:
            if self.dry_run:
                logger.info("DRY RUN: Would have logged in with credentials")
                return

            # Navigate to Twitter login
            self.driver.get('https://twitter.com/i/flow/login')
            logger.info("Navigated to Twitter login page")
            
            # Wait for login form
            time.sleep(5)  # Give page time to fully load
            
            # Enter username
            username_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            username_input.send_keys(username)
            logger.info("Entered username")
            
            # Click next
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
            )
            next_button.click()
            time.sleep(3)
            
            # Handle possible email verification
            try:
                email_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='email']"))
                )
                email_input.send_keys(email)
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
                )
                next_button.click()
                time.sleep(3)
            except TimeoutException:
                logger.info("No email verification required")
            
            # Enter password
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_input.send_keys(password)
            
            # Click login
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Log in']"))
            )
            login_button.click()
            
            # Wait for home timeline to verify login
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
            )
            
            logger.info("Successfully logged in to Twitter")
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            if hasattr(self, 'driver'):
                self.driver.save_screenshot('twitter_login_error.png')
                logger.info("Saved error screenshot to twitter_login_error.png")
            raise

    def _check_rate_limit(self, action_type: str) -> bool:
        """Check if action is within rate limits"""
        rate_limits = self.config['platforms']['twitter']['rate_limits']
        
        if action_type == 'tweet':
            if (self.last_tweet_time and 
                datetime.now() - self.last_tweet_time < timedelta(seconds=rate_limits['min_delay_between_actions'])):
                return False
        elif action_type == 'reply':
            if (self.last_reply_time and 
                datetime.now() - self.last_reply_time < timedelta(seconds=rate_limits['min_delay_between_actions'])):
                return False
        
        return True

    def _save_debug_info(self, stage: str):
        """Save debug information at various stages"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_dir = "debug_twitter"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Save screenshot
            screenshot_path = f"{debug_dir}/{stage}_{timestamp}.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Saved screenshot to {screenshot_path}")
            
            # Save page source
            source_path = f"{debug_dir}/{stage}_{timestamp}.html"
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Saved page source to {source_path}")
            
            # Save current URL
            logger.info(f"Current URL: {self.driver.current_url}")
            
        except Exception as e:
            logger.error(f"Failed to save debug info: {str(e)}")

    def post_tweet(self, content: str, personality: Optional[Dict] = None) -> Optional[str]:
        """Post a new tweet with human-like behavior"""
        if not self._check_rate_limit('tweet'):
            logger.warning("Rate limit exceeded for tweets")
            return None

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Add initial random delay
                self._add_random_delay(1.0, 3.0)
                
                # Log browser state
                logger.info(f"Current URL before posting: {self.driver.current_url}")
                self._save_debug_info("before_post")
                
                # Check if we're still logged in
                if "login" in self.driver.current_url.lower():
                    logger.error("Session appears to have expired, detected login page")
                    self._save_debug_info("login_expired")
                    return None

                # Navigate to home first (more natural)
                logger.info("Navigating to home page first...")
                
                # Try both twitter.com and x.com
                try:
                    self.driver.get('https://twitter.com/home')
                    self._add_random_delay(2.0, 4.0)
                    if "x.com" in self.driver.current_url:
                        logger.info("Redirected to x.com, adjusting selectors...")
                        self.base_url = "https://x.com"
                    else:
                        self.base_url = "https://twitter.com"
                    self._save_debug_info("home_page")
                except:
                    logger.info("Falling back to x.com...")
                    self.driver.get('https://x.com/home')
                    self._add_random_delay(2.0, 4.0)
                    self.base_url = "https://x.com"
                    self._save_debug_info("x_home_page")

                # Verify page loaded correctly
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda x: "home" in x.current_url.lower()
                    )
                except:
                    logger.error("Failed to load home page")
                    self._save_debug_info("home_page_failed")
                    retry_count += 1
                    continue

                # Try multiple compose button selectors
                compose_selectors = [
                    (By.CSS_SELECTOR, "a[href='/compose/tweet']"),
                    (By.CSS_SELECTOR, "a[href='/compose/post']"),
                    (By.CSS_SELECTOR, "div[aria-label='Post']"),
                    (By.CSS_SELECTOR, "div[aria-label='Tweet']"),
                    (By.XPATH, "//span[text()='Post']"),
                    (By.XPATH, "//span[text()='Tweet']"),
                    # Additional selectors for the blue compose button
                    (By.CSS_SELECTOR, "div[data-testid='SideNav_NewTweet_Button']"),
                    (By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button']"),
                    (By.CSS_SELECTOR, "div[aria-label='New post']"),
                    (By.CSS_SELECTOR, "div[aria-label='New tweet']")
                ]
                
                compose_button = None
                for selector_type, selector in compose_selectors:
                    try:
                        compose_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        logger.info(f"Found compose button using selector: {selector}")
                        break
                    except:
                        continue
                
                if compose_button:
                    # Try different click methods
                    click_success = False
                    for click_method in ['action_chains', 'javascript', 'direct']:
                        try:
                            if click_method == 'action_chains':
                                action = webdriver.ActionChains(self.driver)
                                action.move_to_element(compose_button)
                                action.pause(random.uniform(0.1, 0.3))
                                action.click()
                                action.perform()
                            elif click_method == 'javascript':
                                self.driver.execute_script("arguments[0].click();", compose_button)
                            else:
                                compose_button.click()
                            click_success = True
                            break
                        except:
                            continue
                    
                    if not click_success:
                        logger.error("Failed to click compose button")
                        self._save_debug_info("compose_click_failed")
                        retry_count += 1
                        continue
                    
                    self._add_random_delay()
                    self._save_debug_info("after_compose_click")
                else:
                    # Fallback to direct navigation
                    logger.info("Falling back to direct compose navigation...")
                    self.driver.get(f'{self.base_url}/compose/tweet')
                    self._add_random_delay(2.0, 4.0)
                    self._save_debug_info("direct_compose")
                
                # Check for automation detection
                if any(x in self.driver.current_url.lower() for x in ["challenge", "unusual_activity", "verify"]):
                    logger.error("Detected security challenge page")
                    self._save_debug_info("security_challenge")
                    return None

                # Wait for compose page to be ready
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda x: "compose" in x.current_url.lower()
                    )
                except:
                    logger.error("Failed to load compose page")
                    self._save_debug_info("compose_page_failed")
                    retry_count += 1
                    continue

                try:
                    # Try multiple input selectors
                    input_selectors = [
                        (By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']"),
                        (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"),
                        (By.CSS_SELECTOR, "div[aria-label='Post text']"),
                        (By.CSS_SELECTOR, "div[aria-label='Tweet text']"),
                        # Additional backup selectors
                        (By.CSS_SELECTOR, "div.public-DraftEditor-content[contenteditable='true']"),
                        (By.CSS_SELECTOR, "div[data-contents='true']")
                    ]
                    
                    tweet_input = None
                    for selector_type, selector in input_selectors:
                        try:
                            tweet_input = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((selector_type, selector))
                            )
                            logger.info(f"Found tweet input using selector: {selector}")
                            break
                        except:
                            continue
                    
                    if not tweet_input:
                        logger.error("Could not find tweet input element")
                        self._save_debug_info("no_input_found")
                        retry_count += 1
                        continue
                    
                    # Clear any existing text naturally
                    tweet_input.click()
                    self._add_random_delay()
                    tweet_input.clear()
                    self._add_random_delay()
                    
                    # Try different methods to input text
                    input_success = False
                    for input_method in ['char_by_char', 'javascript', 'direct']:
                        try:
                            if input_method == 'char_by_char':
                                for char in content:
                                    tweet_input.send_keys(char)
                                    self._add_random_delay(0.01, 0.05)
                            elif input_method == 'javascript':
                                self.driver.execute_script(
                                    "arguments[0].innerHTML = arguments[1];",
                                    tweet_input,
                                    content
                                )
                                # Trigger input event
                                self.driver.execute_script(
                                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                                    tweet_input
                                )
                            else:
                                tweet_input.send_keys(content)
                            input_success = True
                            break
                        except:
                            continue
                    
                    if not input_success:
                        logger.error("Failed to input content")
                        self._save_debug_info("input_failed")
                        retry_count += 1
                        continue
                    
                    self._add_random_delay()
                    self._save_debug_info("after_input")
                    
                    # Verify content was entered
                    actual_content = tweet_input.text or tweet_input.get_attribute('innerHTML')
                    if not actual_content:
                        logger.error("Failed to input content")
                        self._save_debug_info("input_failed")
                        retry_count += 1
                        continue
                    
                    # Try multiple post button selectors
                    post_selectors = [
                        (By.CSS_SELECTOR, "div[data-testid='tweetButtonInline']"),
                        (By.CSS_SELECTOR, "div[data-testid='postButtonInline']"),
                        (By.XPATH, "//span[text()='Post']"),
                        (By.XPATH, "//span[text()='Tweet']"),
                        # Additional backup selectors
                        (By.CSS_SELECTOR, "div[data-testid='tweetButton']"),
                        (By.CSS_SELECTOR, "div[data-testid='postButton']"),
                        (By.CSS_SELECTOR, "div[role='button'][data-testid*='tweet']"),
                        (By.CSS_SELECTOR, "div[role='button'][data-testid*='post']")
                    ]
                    
                    post_button = None
                    for selector_type, selector in post_selectors:
                        try:
                            post_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((selector_type, selector))
                            )
                            logger.info(f"Found post button using selector: {selector}")
                            break
                        except:
                            continue
                    
                    if not post_button:
                        logger.error("Could not find post button")
                        self._save_debug_info("no_post_button")
                        retry_count += 1
                        continue
                    
                    # Try different click methods
                    click_success = False
                    for click_method in ['action_chains', 'javascript', 'direct']:
                        try:
                            if click_method == 'action_chains':
                                action = webdriver.ActionChains(self.driver)
                                action.move_to_element(post_button)
                                action.pause(random.uniform(0.1, 0.3))
                                action.click()
                                action.perform()
                            elif click_method == 'javascript':
                                self.driver.execute_script("arguments[0].click();", post_button)
                            else:
                                post_button.click()
                            click_success = True
                            break
                        except:
                            continue
                    
                    if not click_success:
                        logger.error("Failed to click post button")
                        self._save_debug_info("post_click_failed")
                        retry_count += 1
                        continue
                    
                    # Wait for post to complete
                    self._add_random_delay(3.0, 5.0)
                    self._save_debug_info("after_post")
                    
                    # Try to get tweet ID
                    tweet_id = self._extract_tweet_id()
                    if tweet_id:
                        return tweet_id
                    
                    logger.error("Failed to get tweet ID")
                    self._save_debug_info("tweet_id_failed")
                    retry_count += 1
                    continue
                    
                except TimeoutException as e:
                    logger.error(f"Timeout while waiting for element: {str(e)}")
                    self._save_debug_info("timeout_error")
                    retry_count += 1
                    continue
                except Exception as e:
                    logger.error(f"Error during tweet posting: {str(e)}")
                    self._save_debug_info("posting_error")
                    retry_count += 1
                    continue

            except Exception as e:
                logger.error(f"Failed to post tweet: {str(e)}")
                if hasattr(self, 'driver'):
                    self._save_debug_info("fatal_error")
                retry_count += 1
                continue
        
        logger.error(f"Failed to post tweet after {max_retries} attempts")
        return None

    def _extract_tweet_id(self) -> Optional[str]:
        """Extract tweet ID after posting"""
        try:
            logger.info("Attempting to extract tweet ID...")
            
            # Try multiple methods to find the tweet ID
            methods = [
                (By.CSS_SELECTOR, "a[href*='/status/']"),
                (By.CSS_SELECTOR, "a[href*='/posts/']"),
                (By.CSS_SELECTOR, "div[data-testid='tweet']"),
                (By.CSS_SELECTOR, "article[data-testid='tweet']"),
                (By.CSS_SELECTOR, "div[data-testid='post']"),
                (By.CSS_SELECTOR, "article[data-testid='post']")
            ]
            
            for selector_type, selector in methods:
                try:
                    logger.info(f"Trying selector: {selector}")
                    element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    
                    if selector_type == By.CSS_SELECTOR and ("status" in selector or "posts" in selector):
                        href = element.get_attribute('href')
                        tweet_id = href.split('/')[-1]
                        logger.info(f"Found tweet ID from href: {tweet_id}")
                        return tweet_id
                    else:
                        for attr in ['data-tweet-id', 'data-post-id', 'id']:
                            tweet_id = element.get_attribute(attr)
                            if tweet_id:
                                logger.info(f"Found tweet ID from attribute {attr}: {tweet_id}")
                                return tweet_id
                except:
                    continue
            
            # If we still don't have an ID, try to get it from the URL
            try:
                current_url = self.driver.current_url
                if '/status/' in current_url or '/posts/' in current_url:
                    tweet_id = current_url.split('/')[-1]
                    logger.info(f"Found tweet ID from URL: {tweet_id}")
                    return tweet_id
            except:
                pass
            
            logger.error("Could not find tweet ID using any method")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting tweet ID: {str(e)}")
            return None

    def get_timeline(self, limit: int = 10) -> List[Dict]:
        """Get recent tweets from timeline"""
        try:
            if self.dry_run:
                return [{'id': f'dry_run_{i}', 'content': f'Test tweet {i}'} for i in range(limit)]

            # Navigate to profile page to see our tweets
            username = os.getenv('TWITTER_USERNAME')
            self.driver.get(f'https://twitter.com/{username}')
            time.sleep(5)  # Wait for page to load

            tweets = []
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while len(tweets) < limit:
                # Find all tweet elements
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                
                for element in tweet_elements:
                    try:
                        # Get tweet text
                        text_element = element.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                        content = text_element.text
                        
                        # Get tweet ID from the article's aria-labelledby attribute
                        tweet_id = element.get_attribute('aria-labelledby').split()[0]
                        
                        tweets.append({
                            'tweet_id': tweet_id,
                            'content': content,
                            'username': username
                        })
                        
                        if len(tweets) >= limit:
                            break
                            
                    except NoSuchElementException:
                        continue
                
                if len(tweets) >= limit:
                    break
                    
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            return tweets[:limit]

        except Exception as e:
            logger.error(f"Error getting timeline: {str(e)}")
            return []

    def reply_to_tweet(self, tweet_id: str, content: str, personality: Optional[Dict] = None) -> Optional[str]:
        """Reply to a specific tweet"""
        if not self._check_rate_limit('reply'):
            logger.warning("Rate limit exceeded for replies")
            return None

        try:
            # Create Tweet object with personality context
            tweet = Tweet(content=content)
            if personality:
                tweet.personality_id = personality['name']
                tweet.personality_context = {
                    'name': personality['name'],
                    'bio': personality['bio'][0],
                    'style': personality['style']['chat']  # Use chat style for replies
                }
                tweet.add_personality_signature(personality)

            if self.dry_run:
                logger.info(f"DRY RUN: Would have replied to tweet {tweet_id} with: {tweet.content}")
                dry_run_id = f"dry_run_reply_{datetime.now().timestamp()}"
                
                # Store in database for testing
                conn = init_db_connection(self.db_path)
                try:
                    c = conn.cursor()
                    c.execute('''INSERT INTO tweet_interactions 
                                (tweet_id, interaction_type, username, personality_id, personality_context, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?)''',
                             (tweet_id, 'reply', os.getenv('TWITTER_USERNAME'),
                              tweet.personality_id,
                              json.dumps(tweet.personality_context) if tweet.personality_context else None,
                              datetime.now()))
                    
                    if tweet.personality_id:
                        # Update personality stats
                        c.execute('''INSERT INTO personality_stats 
                                    (personality_id, total_replies, last_reply_time)
                                    VALUES (?, 1, ?)
                                    ON CONFLICT(personality_id) 
                                    DO UPDATE SET 
                                        total_replies = total_replies + 1,
                                        last_reply_time = ?''',
                                 (tweet.personality_id, datetime.now(), datetime.now()))
                    
                    conn.commit()
                finally:
                    conn.close()
                
                self.last_reply_time = datetime.now()
                return dry_run_id

            # Navigate to tweet
            self.driver.get(f'https://twitter.com/i/status/{tweet_id}')
            
            # Wait for reply button
            reply_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reply']"))
            )
            reply_button.click()
            
            # Wait for reply input
            reply_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']"))
            )
            
            # Enter reply content
            reply_input.send_keys(tweet.content)
            
            # Click reply button
            reply_button = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='tweetButton']")
            reply_button.click()
            
            # Wait for reply to be posted and get its ID
            try:
                reply_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweet']"))
                )
                reply_id = reply_element.get_attribute('data-tweet-id')
                
                if reply_id:
                    # Store in database
                    conn = init_db_connection(self.db_path)
                    try:
                        c = conn.cursor()
                        c.execute('''INSERT INTO tweet_interactions 
                                    (tweet_id, interaction_type, username, personality_id, personality_context, timestamp)
                                    VALUES (?, ?, ?, ?, ?, ?)''',
                                 (tweet_id, 'reply', os.getenv('TWITTER_USERNAME'),
                                  tweet.personality_id,
                                  json.dumps(tweet.personality_context) if tweet.personality_context else None,
                                  datetime.now()))
                        
                        if tweet.personality_id:
                            # Update personality stats
                            c.execute('''INSERT INTO personality_stats 
                                        (personality_id, total_replies, last_reply_time)
                                        VALUES (?, 1, ?)
                                        ON CONFLICT(personality_id) 
                                        DO UPDATE SET 
                                            total_replies = total_replies + 1,
                                            last_reply_time = ?''',
                                     (tweet.personality_id, datetime.now(), datetime.now()))
                        
                        conn.commit()
                    finally:
                        conn.close()
                    
                    self.last_reply_time = datetime.now()
                    logger.info(f"Successfully replied to tweet {tweet_id}")
                    return reply_id
            except TimeoutException:
                logger.error("Failed to get reply ID after posting")
                return None
            
        except Exception as e:
            logger.error(f"Failed to reply to tweet: {str(e)}")
            return None

    def get_stats(self) -> Dict:
        """Get Twitter statistics"""
        conn = init_db_connection(self.db_path)
        try:
            c = conn.cursor()
            
            # Get overall stats
            c.execute('SELECT COUNT(*) FROM tweets')
            total_tweets = c.fetchone()[0]
            
            c.execute('SELECT COUNT(*) FROM tweet_interactions WHERE interaction_type = "reply"')
            total_replies = c.fetchone()[0]
            
            c.execute('SELECT MAX(timestamp) FROM tweets')
            last_activity = c.fetchone()[0]
            
            return {
                'total_tweets': total_tweets,
                'total_replies': total_replies,
                'last_activity': last_activity
            }
        finally:
            conn.close()

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def generate_tweet_content(self, personality: Dict, context: Optional[str] = None) -> Optional[str]:
        """Generate tweet content based on personality"""
        try:
            base_prompt = self.personality_manager.get_personality_prompt(personality, 'twitter', is_reply=False)
            enhanced_prompt = f"""
{base_prompt}

Write a concise, engaging tweet that reflects your unique perspective and expertise.
Focus on one clear idea and express it naturally within Twitter's 280 character limit.
Write conversationally while maintaining your professional voice.

Remember:
- You are {personality['name']}, {personality['bio'][0]}
- Draw from your specific knowledge in: {', '.join(personality['knowledge'][:3])}
- Maintain your characteristic style: {', '.join(personality['style']['post'])}
- Keep it under 280 characters
"""
            if context:
                enhanced_prompt += f"\nContext to respond to:\n{context}"

            content = get_openai_response(enhanced_prompt)
            return content[:280] if content else None
        except Exception as e:
            logger.error(f"Error generating tweet content: {str(e)}")
            return None

    def generate_reply_content(self, personality: Dict, tweet_content: str) -> Optional[str]:
        """Generate reply content based on personality"""
        try:
            base_prompt = self.personality_manager.get_personality_prompt(personality, 'twitter', is_reply=True)
            enhanced_prompt = f"""
{base_prompt}

As {personality['name']}, engage thoughtfully with this tweet from your unique perspective.
Write a concise, natural reply that adds value to the discussion while staying within Twitter's 280 character limit.

The tweet you're responding to:
{tweet_content}

Remember:
- You are {personality['name']}, {personality['bio'][0]}
- Draw from your specific knowledge in: {', '.join(personality['knowledge'][:3])}
- Maintain your characteristic style: {', '.join(personality['style']['chat'])}
- Keep it under 280 characters
"""
            content = get_openai_response(enhanced_prompt)
            return content[:280] if content else None
        except Exception as e:
            logger.error(f"Error generating reply content: {str(e)}")
            return None 