# 🚀 Labyrinth Temporal Hunt - Deployment Guide

## 🎯 Overview

This guide covers deployment options for the Labyrinth Temporal Hunt game, a sophisticated turn-based AI game engine with LangGraph integration, temporal mechanics, and modern web UI.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │────│  LangGraph      │────│ GameStateManager│
│   (Frontend)    │    │  Turn Loop      │    │   (Engine)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│   AI Agents     │──────────────┘
                        │ Mistral/Gemini  │
                        └─────────────────┘
```

## 🐳 Docker Deployment (Recommended)

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone https://github.com/GTuritto/labyrinth-temporal-hunt.git
   cd labyrinth-temporal-hunt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (optional for basic gameplay)
   ```

3. **Build and Run**
   ```bash
   docker-compose up --build
   ```

4. **Access the Game**
   - Open browser to: http://localhost:8501
   - Start playing immediately!

### Production Deployment

```bash
# Build production image
docker-compose -f docker-compose.yml build

# Run in production mode
docker-compose up -d

# View logs
docker-compose logs -f app

# Scale (if needed)
docker-compose up -d --scale app=3
```

### With Redis (Optional)
```bash
# Enable Redis for session storage
docker-compose --profile redis up -d
```

## 🖥️ Local Development

### Prerequisites
- Python 3.11+
- pip or poetry

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export PYTHONPATH=$(pwd)/src

# Run tests
pytest tests/ -v

# Start development server
streamlit run src/ui/app.py --server.port=8501
```

## ☁️ Cloud Deployment

### Streamlit Cloud
1. Fork the repository
2. Connect to Streamlit Cloud
3. Deploy from `src/ui/app.py`
4. Set environment variables in Streamlit Cloud dashboard

### Heroku
```bash
# Create Heroku app
heroku create labyrinth-temporal-hunt

# Set buildpack
heroku buildpacks:set heroku/python

# Deploy
git push heroku main
```

### AWS/GCP/Azure
- Use the provided Dockerfile
- Deploy to container services (ECS, Cloud Run, Container Instances)
- Configure load balancer for multiple instances

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_MODE` | Application mode | `development` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `RANDOM_SEED` | Game randomization seed | `42` | No |
| `MISTRAL_API_KEY` | Mistral AI API key | - | No* |
| `GEMINI_API_KEY` | Google Gemini API key | - | No* |

*AI agents are optional - game works without API keys

### Game Configuration

The game engine is highly configurable through `src/gsm/physics.py`:

```python
# Physics constants
GRID_SIZE = 50
STAMINA_DRAIN_RATE = 0.1
SIGHT_RADIUS = 8.0
MINOTAUR_JUMP_COOLDOWN = 600.0
```

## 🎮 Game Features

### Core Gameplay
- **Turn-based mechanics** with user and minotaur phases
- **3D labyrinth navigation** with realistic physics
- **Temporal mechanics** (minotaur vanishing, lantern paralysis)
- **Inventory system** with stone collection objectives
- **Stamina management** affecting movement speed

### AI Integration
- **LangGraph workflow** orchestrating game turns
- **Natural language parsing** ("move north 5" → game commands)
- **AI agents** providing strategic advice
- **Deterministic engine** ensuring fair gameplay

### Technical Features
- **100% test coverage** with comprehensive test suite
- **Type-safe** with Pydantic v2 validation
- **JSON logging** for game analysis and debugging
- **Real-time UI** with live state updates

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_turn_loop.py -v      # LangGraph tests
pytest tests/test_engine_response.py -v # Game engine tests
pytest tests/test_temporal_logic.py -v  # Temporal mechanics tests

# Test coverage
pytest tests/ --cov=src --cov-report=html
```

## 📊 Monitoring

### Health Checks
- **Application**: `http://localhost:8501/_stcore/health`
- **Docker**: Built-in healthcheck with curl
- **Game State**: Turn logs provide detailed game analytics

### Logging
```bash
# View application logs
docker-compose logs -f app

# Game turn logs (JSON format)
tail -f logs/game_turns.log

# Error tracking
grep ERROR logs/app.log
```

## 🔒 Security

### API Keys
- Store in environment variables, never in code
- Use secrets management in production
- AI features gracefully degrade without keys

### Network Security
- Default Docker network isolation
- No external database dependencies
- Stateless application design

## 🚀 Performance

### Optimization
- **Deterministic engine**: No external API calls for core gameplay
- **Efficient state management**: Minimal memory footprint
- **Fast turn execution**: < 100ms per turn
- **Scalable architecture**: Stateless design supports horizontal scaling

### Resource Requirements
- **Memory**: ~100MB per instance
- **CPU**: Minimal (single-threaded game logic)
- **Storage**: Logs only (configurable retention)

## 🛠️ Troubleshooting

### Common Issues

1. **Port 8501 already in use**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "8502:8501"
   ```

2. **Import errors**
   ```bash
   # Ensure PYTHONPATH is set
   export PYTHONPATH=$(pwd)/src
   ```

3. **AI agents not responding**
   - Check API keys in .env file
   - Verify network connectivity
   - Game works without AI agents

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
streamlit run src/ui/app.py --logger.level=debug
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Multiple instances with load balancer
docker-compose up -d --scale app=3

# Use Redis for shared session storage
docker-compose --profile redis up -d
```

### Performance Tuning
- Enable Redis for session management
- Use CDN for static assets
- Configure reverse proxy (nginx/traefik)

## 🎯 Next Steps

1. **Deploy to production** using Docker
2. **Configure monitoring** and alerting
3. **Set up CI/CD** pipeline
4. **Add custom game modes** or mechanics
5. **Integrate additional AI models**

## 📞 Support

- **Documentation**: See README.md for detailed game mechanics
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Architecture**: See ADRs/ directory for design decisions

---

🎮 **Ready to deploy your labyrinth adventure!** 🏛️
