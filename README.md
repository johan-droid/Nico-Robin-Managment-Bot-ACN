# 🌸 Nico Robin Bot - Anime Crew Network

<div align="center">

![Nico Robin](https://img.shields.io/badge/Nico%20Robin-ACN%20Bot-purple?style=for-the-badge&logo=one-piece)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Telegram](https://img.shields.io/badge/Telegram%20Bot-2CA5E0?style=for-the-badge&logo=telegram)
![Database](https://img.shields.io/badge/Database-PostgreSQL-336791?style=for-the-badge&logo=postgresql)

**A sophisticated Telegram bot for the Anime Crew Network with advanced features, point system, and character interactions.**

[![GitHub stars](https://img.shields.io/github/stars/johan-droid/Nico-Robin-Bot-.svg?style=social&label=Star)](https://github.com/johan-droid/Nico-Robin-Bot-/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/johan-droid/Nico-Robin-Bot-.svg?style=social&label=Fork)](https://github.com/johan-droid/Nico-Robin-Bot-/forks)

</div>

## 📖 Table of Contents

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📋 Requirements](#-requirements)
- [⚙️ Installation](#️-installation)
- [🔧 Configuration](#-configuration)
- [🗄️ Database Setup](#️-database-setup)
- [📝 Commands](#-commands)
- [🎯 Point System](#-point-system)
- [🤝 Bot Friendship](#-bot-friendship)
- [🌸 ACN Loyalty](#-acn-loyalty)
- [🐳 Docker Deployment](#-docker-deployment)
- [📊 API](#-api)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## ✨ Features

### 🎮 **Interactive Systems**
- **💫 Point System** - Earn points, collect apploids, level up
- **💕 Bot Friendship** - Bond with Yamato ACN bot with sweet interactions
- **🌸 Flirting System** - Advanced romantic interactions with Nico Robin
- **🎭 Custom Apploids** - Collect unique Nico Robin themed avatars

### 🛡️ **Moderation & Management**
- **🔧 Feature Toggles** - Enable/disable bot features per group
- **👥 ACN Loyalty** - Rank system with rewards and privileges
- **📊 Member Profiles** - Track user activity and engagement
- **🔒 Security Controls** - Role-based access and permissions

### 🎯 **Engagement Features**
- **🌊 Nico Moments** - Character interactions and emotions
- **📺 Broadcast System** - Cross-group announcements
- **🎪 Entertainment** - Games, jokes, and fun activities
- **📈 Statistics** - Comprehensive analytics and leaderboards

### 🔧 **Technical Features**
- **⚡ Real-time WebSocket** - Live events and notifications
- **🗄️ PostgreSQL Database** - Scalable data storage
- **🐳 Docker Support** - Easy deployment
- **📡 Webhook Gateway** - Secure bot communication

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Telegram Bot Token
- Docker (optional)

### One-Click Setup with Docker
```bash
# Clone the repository
git clone https://github.com/johan-droid/Nico-Robin-Bot-.git
cd Nico-Robin-Bot-

# Copy environment file
cp .env.example .env

# Edit your bot token and database settings
nano .env

# Run with Docker Compose
docker-compose up -d
```

### Manual Setup
```bash
# Clone and setup
git clone https://github.com/johan-droid/Nico-Robin-Bot-.git
cd Nico-Robin-Bot-
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python init_database.py

# Run the bot
python main.py
```

## 📋 Requirements

### System Requirements
- **Python**: 3.11 or higher
- **Database**: PostgreSQL 12+ (recommended)
- **Memory**: Minimum 512MB RAM
- **Storage**: Minimum 1GB disk space

### Python Dependencies
- `python-telegram-bot` - Telegram Bot API
- `sqlalchemy` - Database ORM
- `asyncpg` - PostgreSQL async driver
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `alembic` - Database migrations
- `structlog` - Structured logging

### Optional Dependencies
- `redis` - For caching (recommended)
- `celery` - For background tasks
- `prometheus-client` - For metrics

## ⚙️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/johan-droid/Nico-Robin-Bot-.git
cd Nico-Robin-Bot-
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Setup Database
```bash
# Create PostgreSQL database
createdb nico_robin_bot

# Run migrations and setup
python init_database.py
```

### 6. Start the Bot
```bash
python main.py
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file with the following:

```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
BOT_NAME=Nico Robin

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nico_robin_bot

# ACN Leadership
CAPTAIN_ID=123456789
COMMANDER_IDS=234567890,345678901

# Security
WEBHOOK_SECRET=your_webhook_secret_here
METRICS_API_KEY=your_metrics_key_here

# Optional Features
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### Bot Token Setup
1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the token and add it to `.env`

### Database Setup
```bash
# PostgreSQL setup (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo -u postgres createdb nico_robin_bot
sudo -u postgres createuser --interactive
```

## 🗄️ Database Setup

### Automatic Setup
```bash
# Initialize database with all tables and basic data
python init_database.py

# Validate the setup
python database_migration_validator.py
```

### Manual Setup
```bash
# Run Alembic migrations
alembic upgrade head

# Initialize basic data
python -c "
from database import async_session_factory
from services.acn_service import ACNService
# Add your ACN members here
"
```

### Database Schema
The bot uses 30+ tables including:
- **Users & Groups** - Core user and group management
- **Points System** - Point economy and apploids
- **Bot Friendship** - Companion bot relationships
- **Flirting System** - Romantic interactions
- **ACN Loyalty** - Rank and reward system
- **Feature Management** - Toggle controls
- **Activity Tracking** - User engagement metrics

## 📝 Commands

### 🎯 Point System Commands
```
/points              - Show your point balance and level
/leaderboard [limit] - Show top point earners
/apploids            - View available apploids
/buy_apploid <name> - Purchase an apploid
/equip_apploid <name> - Equip an apploid
/earn_points         - Show ways to earn points
```

### 🤝 Bot Friendship Commands
```
/bond_with_yamato    - Bond with Yamato ACN bot
/yamato_interact <type> - Interact with Yamato
/yamato_status       - Show friendship status
/yamato_memories     - View shared memories
/gift_to_yamato <type> <msg> - Send gift to Yamato
```

### 💕 Flirting Commands
```
/flirt <message>     - Try to flirt with Nico Robin
/flirt_stats         - Show your flirting statistics
/flirt_categories    - View available categories
/flirt_achievements  - Show your achievements
/flirt_example       - Get example flirt lines
```

### 🔧 Feature Management Commands
```
/features            - Show all available features
/enable <feature>   - Enable a feature
/disable <feature>  - Disable a feature
/toggle <feature>   - Toggle a feature on/off
/feature_info <feature> - Show feature details
```

### 🌸 ACN Commands
```
/acn_status          - Check your ACN status and rank
/loyalty_leaderboard - Show ACN leaderboard
/acn_members         - List ACN members in group
/acn_info            - Show group statistics
```

### 👑 Leadership Commands (Captain/Commander Only)
```
/addacn <user> <role> - Add ACN member
/removeacn <user>    - Remove ACN member
/award <user> <points> - Award loyalty points
/addacngroup         - Add group to ACN
```

## 🎯 Point System

### How to Earn Points
- **Messages**: 1 point per message (1 min cooldown)
- **Daily Streak**: 10 points daily bonus
- **Flirting**: 5 points for successful attempts
- **Bot Friendship**: 3 points for interactions
- **Achievements**: 20 points for special accomplishments

### Point Levels & Ranks
```
Level 1 - Novice Scholar (0 pts) - 1.0x multiplier
Level 2 - Apprentice Archaeologist (100 pts) - 1.1x multiplier
Level 3 - Journeyman Historian (250 pts) - 1.2x multiplier
Level 4 - Expert Researcher (500 pts) - 1.3x multiplier
Level 5 - Master Scholar (1,000 pts) - 1.4x multiplier
Level 6 - Senior Archaeologist (2,000 pts) - 1.5x multiplier
Level 7 - Lead Historian (5,000 pts) - 1.6x multiplier
Level 8 - Chief Researcher (10,000 pts) - 1.8x multiplier
Level 9 - Master Archaeologist (25,000 pts) - 2.0x multiplier
Level 10 - Legendary Scholar (50,000 pts) - 2.5x multiplier
```

### Apploids Collection
Collect unique Nico Robin themed apploids:
- **Common**: Robin Classic, Scholar Robin
- **Rare**: Devil Child, Archaeologist Robin
- **Epic**: Blossom Robin, Ocean Robin, Nightingale Robin
- **Legendary**: Golden Robin, Poneglyph Robin, Angel Robin

## 🤝 Bot Friendship

### Yamato ACN Integration
Build a sweet friendship between Nico Robin and Yamato ACN bot (@YamatoAcn_bot).

### Friendship Levels
- **Acquaintance** (0-24 pts) - Just getting to know each other
- **Friend** (25-49 pts) - Good friends who enjoy time together
- **Close Friend** (50-74 pts) - Very close with deep connections
- **Best Friend** (75-100 pts) - Unbreakable bond, soulmates

### Interaction Types
- **waifu** - Compliment Yamato's waifu hunting skills
- **compliment** - Give sweet compliments
- **moment** - Share special moments together
- **tease** - Playful teasing and fun
- **deep** - Deep emotional connections

## 🌸 ACN Loyalty

### Rank System
```
Crew Member (0-49 pts)
Ensign (50-99 pts)
Lieutenant (100-199 pts)
Commander (200-499 pts)
Captain (500-999 pts)
Commodore (1,000-1,999 pts)
Rear Admiral (2,000-4,999 pts)
Vice Admiral (5,000-9,999 pts)
Fleet Admiral (10,000+ pts)
```

### Role Hierarchy
- **Captain** - The leader (Monkey D. Sparrow)
- **Commanders** - Management team
- **Members** - Regular ACN members
- **Allies** - External collaborators

## 🐳 Docker Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: nico_robin_bot
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Docker Commands
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down

# Update bot
docker-compose pull
docker-compose up -d --force-recreate
```

## 📊 API

### Webhook Endpoint
```
POST /webhook
Content-Type: application/json
X-Telegram-Bot-Api-Secret-Token: <secret>
```

### WebSocket Events
Connect to `/socket.io` for real-time events:
- User joins/leaves
- Moderation actions
- Point updates
- Feature changes

### Metrics Endpoint
```
GET /metrics
Authorization: Bearer <api_key>
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Use meaningful commit messages

### Code Style
```python
# Use type hints
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming message."""
    pass

# Use async/await
async def get_user_data(user_id: int) -> Optional[User]:
    """Get user data from database."""
    async with async_session_factory() as session:
        # Database operations
        pass
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **One Piece** - For the amazing character Nico Robin
- **Telegram** - For the excellent Bot API
- **Anime Crew Network** - For the community and support
- ** Contributors** - Everyone who helped make this bot better

## 📞 Support

- **GitHub Issues**: [Report bugs](https://github.com/johan-droid/Nico-Robin-Bot-/issues)
- **Discussions**: [Feature requests](https://github.com/johan-droid/Nico-Robin-Bot-/discussions)
- **Telegram**: [@YourSupportBot] (coming soon)

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=johan-droid/Nico-Robin-Bot-&type=Date)](https://star-history.com/#johan-droid/Nico-Robin-Bot-&Date)

---

<div align="center">

**Made with ❤️ for the Anime Crew Network**

![Nico Robin](https://img.shields.io/badge/Nico%20Robin-ACN%20Bot-purple?style=for-the-badge)

*"Knowledge is power, and friendship is treasure!"* - Nico Robin

</div>
