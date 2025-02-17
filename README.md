# FlavumHive

FlavumHive is an innovative social media orchestration system that creates engaging, multi-personality discussions and interactions on Reddit. It simulates natural conversations between distinct Key Opinion Leaders (KOLs) in the cryptocurrency, DeFi, and technology space, each with their own expertise, viewpoints, and communication styles.

## Current Personalities

The system features five distinct KOL personalities:

1. **shawmakesmagic** - OS development and systems architecture
   - Creator of ElizaOS
   - Systems programmer focused on Rust and modern OS design
   - Advocate for rethinking traditional OS patterns

2. **fxnction** - DeFi and trading expertise
   - Seasoned crypto trader and DeFi expert
   - Technical analyst focused on market psychology
   - Community educator on complex DeFi concepts

3. **infinity_gainz** - Market analysis and technical trading
   - Crypto KOL focused on high-conviction trades
   - On-chain data specialist
   - DeFi protocol reviewer and power user

4. **defi_skeptic** - Traditional finance perspective
   - Experienced traditional finance professional
   - Risk analyst focused on protocol vulnerabilities
   - Critical analyst of DeFi claims and systems

5. **crypto_researcher** - Academic analysis
   - Blockchain economics researcher
   - Data-driven protocol analyst
   - Specialist in tokenomics and governance systems

## Core Features

- **KOL-Driven Interactions**: Each personality maintains their unique voice, expertise, and perspective
- **Natural Conversation Flow**: Generates contextual, flowing discussions without mechanical structures
- **Clear Attribution**: Each post and comment clearly identifies the speaking personality
- **Dynamic Flair Management**: Automatically selects appropriate post flairs based on content
- **Intelligent Rate Limiting**: Maintains natural posting patterns while respecting Reddit's guidelines
- **Multi-Perspective Discussions**: Creates rich interactions between different viewpoints

## Development Roadmap 🚀

### Phase 1: Foundation (Completed ✅)
- ✅ Multi-KOL System Implementation
- ✅ Natural Language Processing Integration
- ✅ Basic Personality Framework
- ✅ Reddit API Integration
- ✅ Rate Limiting System
- ✅ Docker Containerization

### Phase 2: Enhanced Intelligence (Q2 2024)
- 🔄 Advanced Conversation Branching
- 🔄 Personality Memory System
- 🔄 Sentiment Analysis Integration
- 🔄 Cross-Platform Support (Twitter/X)
- 🔄 Enhanced Market Analysis Tools
- 🔄 Community Feedback Integration

### Phase 3: Advanced Features (Q3 2024)
- 📊 Analytics Dashboard
- 🔗 Web3 Integration
- 🤖 Custom LLM Fine-tuning
- 📈 Trading Signal Generation
- 🔒 Enhanced Security Features
- 🌐 Multi-Language Support

### Phase 4: Enterprise Features (Q4 2024)
- 💼 Team Management Console
- 📱 Mobile Management App
- 🔄 Auto-Scaling Infrastructure
- 📊 Advanced Analytics & Reporting
- 🤝 API for Third-Party Integration
- 🎯 Custom Deployment Solutions

### Phase 5: Future Vision (2025)
- 🧠 Advanced AI Personality Creation
- 🌐 Decentralized Infrastructure
- 🤝 DAO Integration
- 📊 Predictive Analytics
- 🔗 Cross-Chain Support
- 🚀 Custom AI Model Training

## Configuration

### Personality Files
Located in `/personalities/` directory:
- `shawmakesmagic.json`
- `fxnction.json`
- `infinity_gainz.json`
- `defi_skeptic.json`
- `crypto_researcher.json`

Each personality file contains:
- Detailed bio and background
- Knowledge areas and expertise
- Communication style preferences
- Example messages and posts
- Characteristic adjectives

### Central Configuration
`config.json` manages:
- Target subreddits
- Rate limits
- Interaction settings
- Conversation depth
- Post frequency

## Prerequisites

- Python 3.8 or higher
- Reddit account with API access
- OpenAI API key (GPT-4 access)
- SQLite (included with Python)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/flavumhive.git
cd flavumhive
```

2. Create and activate Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your `.env` file with API credentials:
```env
# OpenAI Configuration
OPENAI_API_KEY="your_openai_api_key"

# Reddit Configuration
REDDIT_USERNAME="your_username"
REDDIT_PASSWORD="your_password"
REDDIT_CLIENT_ID="your_client_id"
REDDIT_CLIENT_SECRET="your_client_secret"
REDDIT_USER_AGENT="script:flavumhive:v1.0 (by u/your_username)"
```

## Usage

1. Start the system:
```bash
python main.py
```

The system will:
- Load all five KOL personalities
- Connect to target subreddits
- Generate natural posts and comments
- Maintain conversation threads
- Create multi-perspective discussions

## Current Rate Limits

Default settings in `config.json`:
- 10 posts per day
- 50 comments per day
- 2 posts per hour
- 5 comments per hour
- 20-40 seconds between actions

## Interaction Flow

1. **Post Creation**:
   - Random KOL selection
   - Natural title generation
   - Content creation with personality signature
   - Automatic flair selection

2. **Comment Generation**:
   - Contextual response generation
   - Personality-appropriate insights
   - Natural conversation flow
   - Clear KOL attribution

3. **Discussion Dynamics**:
   - Technical discussions between system experts
   - Market analysis debates
   - Critical perspective integration
   - Academic insights and research views

## Best Practices

1. Monitor interactions for quality and authenticity
2. Regularly review personality configurations
3. Adjust rate limits based on community response
4. Keep conversation flows natural and engaging
5. Respect subreddit-specific guidelines

## Development Status

Current focus areas:
- [x] Multi-KOL system implementation
- [x] Natural conversation flow
- [x] Personality-specific content generation
- [x] Dynamic flair management
- [x] Rate limiting and timing controls
- [x] Clear personality attribution
- [ ] Advanced conversation branching
- [ ] Personality memory system
- [ ] Analytics dashboard

## Troubleshooting

Common issues and solutions:
1. Rate limit errors: Check `config.json` timing settings
2. Authentication failures: Verify Reddit API credentials
3. Database errors: Ensure proper SQLite setup
4. Content generation issues: Check OpenAI API key and quota

## Security Note

Never commit sensitive credentials to the repository. Always use environment variables for API keys and authentication details. The `.env` file is automatically ignored by git to prevent accidental exposure of credentials.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Reddit API and PRAW documentation
- OpenAI GPT-4 API
- Community contributors and testers
- SQLite project

## Deployment

### Local Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Digital Ocean Deployment

1. Create a Digital Ocean account and generate an access token

2. Set up GitHub Secrets:
   - `DIGITALOCEAN_ACCESS_TOKEN`: Your DO access token
   - `DIGITALOCEAN_REGISTRY`: Your DO registry name
   - `DROPLET_HOST`: Your droplet's IP address
   - `DROPLET_USERNAME`: Your droplet's SSH username
   - `DROPLET_SSH_KEY`: Your SSH private key for the droplet

3. Create a Digital Ocean droplet:
   ```bash
   # Create a new droplet with Docker pre-installed
   doctl compute droplet create flavumhive \
     --image docker-20-04 \
     --size s-1vcpu-1gb \
     --region nyc1 \
     --ssh-keys your-ssh-key-id
   ```

4. Initial server setup:
   ```bash
   # SSH into your droplet
   ssh root@your-droplet-ip

   # Create application directory
   mkdir -p /opt/flavumhive
   cd /opt/flavumhive

   # Copy your .env file
   nano .env  # Paste your environment variables
   ```

5. Push to GitHub:
   - The GitHub Actions workflow will automatically:
     - Build the Docker image
     - Push to Digital Ocean Container Registry
     - Deploy to your droplet
     - Restart the service

### Continuous Deployment

The system is configured for continuous deployment:
1. Push changes to main/master branch
2. GitHub Actions automatically builds and deploys
3. New version runs on Digital Ocean
4. Database persists between deployments

### Monitoring

1. View logs:
   ```bash
   # SSH into droplet
   ssh root@your-droplet-ip
   
   # View logs
   cd /opt/flavumhive
   docker-compose logs -f
   ```

2. Check status:
   ```bash
   docker-compose ps
   ```
