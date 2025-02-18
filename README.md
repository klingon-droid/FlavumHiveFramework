# FlavumHive

FlavumHive is an advanced social media orchestration framework that enables intelligent, personality-driven interactions across multiple platforms. It creates engaging, authentic conversations through distinct AI personalities, each maintaining consistent character traits and expertise across different social media platforms.

## Supported Platforms

- ✅ **Twitter/X**: Real-time engagement, trending discussions, thread creation
- ✅ **Reddit**: Community discussions, detailed analysis, subreddit engagement
- 🔄 **Discord**: Coming soon - Server management, community interaction
- 🔄 **Telegram**: Coming soon - Group discussions, broadcast channels

## Core Features

- **Multi-Platform Integration**: Seamless operation across different social media platforms
- **Personality-Driven Interactions**: Consistent character voices across all platforms
- **Intelligent Rate Management**: Platform-specific rate limiting and timing controls
- **Advanced Session Handling**: Robust browser automation and API integrations
- **Comprehensive Monitoring**: Unified logging and status tracking
- **Database Integration**: Cross-platform activity tracking and state management

## Active Personalities

The system features expert personalities in crypto, DeFi, and technology:

1. **crypto_researcher** - Academic analysis and research
2. **defi_skeptic** - Critical analysis and risk assessment
3. **infinity_gainz** - Market analysis and trading
4. **fxnction** - DeFi and protocol expertise
5. **shawmakesmagic** - Technical development and architecture

Each personality maintains consistent traits across all platforms while adapting to platform-specific communication styles.

## Technical Architecture

### Platform Handlers
- `platforms/twitter/`: Twitter integration with browser automation
- `platforms/reddit/`: Reddit API integration
- `platforms/discord/`: (Coming soon) Discord bot integration
- `platforms/telegram/`: (Coming soon) Telegram bot integration

### Core Components
- `utils/`: Shared utilities and helpers
- `personalities/`: Personality configurations and traits
- `database/`: Cross-platform data management

## Configuration

### Environment Setup
```bash
# Twitter Credentials
TWITTER_USERNAME="your_username"
TWITTER_PASSWORD="your_password"
TWITTER_EMAIL="your_email"

# Reddit Credentials
REDDIT_USERNAME="your_username"
REDDIT_PASSWORD="your_password"
REDDIT_CLIENT_ID="your_client_id"
REDDIT_CLIENT_SECRET="your_client_secret"

# OpenAI Configuration
OPENAI_API_KEY="your_openai_api_key"
```

### Platform Settings (`config.json`)
```json
{
    "platforms": {
        "twitter": {
            "enabled": true,
            "rate_limits": {
                "tweets_per_hour": 5,
                "min_delay_between_actions": 30
            }
        },
        "reddit": {
            "enabled": true,
            "rate_limits": {
                "posts_per_hour": 2,
                "comments_per_hour": 5
            }
        }
    }
}
```

## Quick Start

1. **Installation**:
   ```bash
   git clone https://github.com/yourusername/flavumhive.git
   cd flavumhive
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Copy `.env.example` to `.env` and add your credentials
   - Adjust `config.json` for platform-specific settings

3. **Platform Management**:
   ```bash
   # Twitter Bot Management
   python manage_bot.py start   # Start Twitter bot
   python manage_bot.py status  # Check status
   python manage_bot.py stop    # Stop bot
   
   # Reddit Bot Management
   python main.py --platform reddit
   ```

## Monitoring and Logs

- **Platform-specific logs**: `{platform}_bot.log`
- **Debug information**: `debug_{platform}/`
- **Database**: `redharmony.db`
- **Status tracking**: `bot_status.json`

## Development Status

### Completed ✅
- Multi-platform framework architecture
- Twitter integration with browser automation
- Reddit API integration
- Personality system implementation
- Rate limiting and monitoring
- Database integration

### In Progress 🔄
- Discord integration
- Telegram integration
- Cross-platform conversation threading
- Advanced analytics dashboard

## Best Practices

1. **Rate Limiting**: Respect platform-specific rate limits
2. **Error Handling**: Implement proper recovery mechanisms
3. **Monitoring**: Regular log review and status checks
4. **Testing**: Thorough testing before deployment
5. **Security**: Secure credential management

## Requirements

- Python 3.13+
- Chrome browser (for Twitter)
- SQLite
- Platform-specific API access
- OpenAI API key (GPT-4)

## License

MIT License - See [LICENSE](LICENSE) file

## Security

- Never commit credentials to the repository
- Use environment variables for sensitive data
- Regularly rotate API keys and passwords
- Monitor for suspicious activity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
