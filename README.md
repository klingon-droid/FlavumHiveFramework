# FlavumHive

FlavumHive is an advanced social media orchestration framework that enables intelligent, personality-driven interactions across multiple platforms. It creates engaging, authentic conversations through distinct AI personalities, each maintaining consistent character traits and expertise across different social media platforms.

## 🚀 Quick Start

1. **Clone & Setup**:
   ```bash
   git clone https://github.com/yourusername/flavumhive.git
   cd flavumhive
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - Twitter credentials (username, password, email)
   # - Reddit API credentials
   # - OpenAI API key
   ```

3. **Start the Bots**:
   ```bash
   # Start Twitter Bot
   python continuous_twitter_bot.py
   
   # Start Reddit Bot
   python main.py --platform reddit
   
   # Monitor Logs
   tail -f twitter_bot.log  # Twitter logs
   tail -f bot.log         # General logs
   ```

## 🎯 Core Functionalities

### 1. Multi-Platform Integration
- **Twitter/X**: 
  - Automated posting with personality-driven content
  - Thread creation and management
  - Real-time engagement monitoring
  - Rate-limited interactions (5 tweets/hour default)

- **Reddit**:
  - Subreddit monitoring and engagement
  - Automated post creation and responses
  - Community-specific personality adaptation
  - Rate-limited interactions (2 posts/hour, 5 comments/hour default)

### 2. AI Personality System
- **Available Personalities**:
  - `crypto_researcher`: Academic analysis and research
  - `defi_skeptic`: Critical analysis and risk assessment
  - `infinity_gainz`: Market analysis and trading
  - Each personality maintains:
    - Consistent voice and style
    - Platform-specific behavior patterns
    - Configurable response types

### 3. Configuration System
- **Platform Settings** (`config.json`):
  ```json
  {
    "platforms": {
      "twitter": {
        "enabled": true,
        "rate_limits": {
          "tweets_per_hour": 5,
          "min_delay_between_actions": 30
        }
      }
    }
  }
  ```

- **Personality Settings** (`personalities/*.json`):
  ```json
  {
    "name": "crypto_researcher",
    "platform_settings": {
      "twitter": {
        "tweet_style": "informative",
        "interaction_style": "academic_analytical"
      }
    }
  }
  ```

## 🛠 Developer Guide

### Project Structure
```
FlavumHive/
├── platforms/           # Platform-specific implementations
│   ├── twitter/        # Twitter automation
│   └── reddit/         # Reddit API integration
├── personalities/      # AI personality configurations
├── utils/             # Shared utilities
├── continuous_twitter_bot.py  # Twitter bot entry
├── main.py            # Multi-platform entry
└── config.json        # Global configuration
```

### Key Components

1. **Platform Handlers**
   - `TwitterHandler`: Browser automation using Selenium
   - `RedditHandler`: PRAW-based Reddit API integration
   - Each handler implements:
     - Authentication
     - Content generation
     - Rate limiting
     - Error recovery

2. **Personality Manager**
   - Loads personality configurations
   - Manages personality switching
   - Provides context for AI responses

3. **Database Integration**
   - SQLite-based storage
   - Tracks:
     - Post history
     - Interaction states
     - Rate limit compliance

### Common Operations

1. **Managing Bots**:
   ```bash
   # Start Twitter bot in background
   nohup python continuous_twitter_bot.py &
   
   # Check bot status
   python manage_bot.py status
   
   # Stop running bots
   python manage_bot.py stop
   ```

2. **Monitoring**:
   - Log files: `twitter_bot.log`, `bot.log`
   - Debug screenshots: `debug_twitter/`
   - Status file: `bot_status.json`

3. **Testing**:
   ```bash
   # Run integration tests
   python run_integrated_test.py
   
   # Test specific platform
   python test_twitter_integration.py
   python test_reddit_integration.py
   ```

## 🔧 Customization

### Adding New Personalities
1. Create new personality file in `personalities/`
2. Define platform-specific behaviors
3. Update `config.json` to enable

### Modifying Rate Limits
```json
{
  "platforms": {
    "twitter": {
      "rate_limits": {
        "tweets_per_hour": 10,  // Increase tweet frequency
        "min_delay_between_actions": 45  // Increase delay
      }
    }
  }
}
```

### Custom Content Generation
- Modify `generate_tweet_content()` in platform handlers
- Adjust personality prompts in personality JSON files
- Configure OpenAI parameters in handlers

## 📊 Monitoring & Maintenance

### Health Checks
- Monitor `bot_status.json` for current state
- Check log files for errors
- Review debug screenshots for UI issues

### Common Issues
1. **Rate Limiting**: Adjust in `config.json`
2. **Authentication**: Check `.env` credentials
3. **Browser Issues**: Clear `debug_twitter/` and restart

### Best Practices
1. Regular log rotation
2. Backup database files
3. Monitor API usage
4. Test changes in dry-run mode

## 🔐 Security Considerations

1. **Credential Management**
   - Use environment variables
   - Regular key rotation
   - Secure storage practices

2. **Rate Limiting**
   - Platform-specific limits
   - Gradual ramp-up
   - Anti-spam measures

3. **Error Handling**
   - Graceful degradation
   - Automatic recovery
   - Alert systems

## 📚 Additional Resources

- [Detailed Documentation](../flavumhive-documentation)
- [API Reference](../flavumhive-documentation/docs/api)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

MIT License - See [LICENSE](LICENSE) file
