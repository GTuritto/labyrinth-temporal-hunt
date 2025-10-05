# 🏛️ Labyrinth Temporal Hunt

> **A sophisticated turn-based AI game engine with LangGraph orchestration, temporal mechanics, and modern web interface**

[![Tests](https://img.shields.io/badge/tests-100%25%20passing-brightgreen)](https://github.com/GTuritto/labyrinth-temporal-hunt)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://docker.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-integrated-purple)](https://langchain.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)](https://streamlit.io)

## 🎯 Overview

Labyrinth Temporal Hunt is a production-ready turn-based game engine that combines:
- **🤖 AI Agent Integration** with Mistral and Gemini models
- **🔄 LangGraph Workflow** orchestration for complex turn logic
- **⏰ Temporal Mechanics** with sophisticated state transitions
- **🎮 Modern Web UI** built with Streamlit
- **🧪 100% Test Coverage** with comprehensive validation

Perfect for AI research, game development, or as a sophisticated coding showcase.

## ✨ Key Features

### 🎮 **Advanced Game Engine**
- **Deterministic Physics**: Realistic movement, stamina, collision detection
- **3D Labyrinth**: Navigate a 50×50 grid with multi-level support
- **Smart AI Opponent**: Distance-based Minotaur behavior with temporal abilities
- **Win/Lose Conditions**: Collect 3 stones to escape, avoid the hunting Minotaur

### 🤖 **AI Integration**
- **LangGraph Turn Loop**: 4-node workflow with user/minotaur phases
- **Natural Language Processing**: "move north 5" → structured commands
- **AI Agents**: Mistral (tactical hunter) + Gemini (cunning minotaur)
- **Flexible Input**: JSON or natural language command parsing

### ⏰ **Temporal Mechanics**
- **Minotaur Vanishing**: Random disappearances (5-10s) with cooldowns
- **Lantern Paralysis**: Stun the Minotaur for 120 seconds
- **State Transitions**: CHASING → VANISHED → PARALYZED cycles
- **Immunity System**: Safe zones during temporal states

### 🏗️ **Production Architecture**
- **Type-Safe**: Pydantic v2 validation throughout
- **Modular Design**: Clean separation of concerns
- **Docker Ready**: Complete containerization
- **Scalable**: Stateless design supports horizontal scaling

## 🚀 Quick Start

### 🐳 **Docker (Recommended)**
```bash
git clone https://github.com/GTuritto/labyrinth-temporal-hunt.git
cd labyrinth-temporal-hunt
docker-compose up --build
```
→ Open http://localhost:8501 and start playing!

### 💻 **Local Development**
```bash
pip install -r requirements.txt
export PYTHONPATH=$(pwd)/src
streamlit run src/ui/app.py
```

### 🧪 **Run Tests**
```bash
pytest tests/ -v  # All 100 tests should pass
```

## 🎮 How to Play

### **Basic Commands**
- **Movement**: `move north 5`, `move east 3`
- **Observation**: `look` (examine surroundings)
- **Collection**: `grab red stone`, `grab blue stone`
- **Special**: `use lantern` (paralyze Minotaur), `halt` (listen)

### **Game Objectives**
1. **🔴 Collect Stones**: Find and grab RED, BLUE, YELLOW stones
2. **👹 Avoid Minotaur**: Listen for audio cues, use temporal mechanics
3. **🏃 Manage Stamina**: Balance speed vs. endurance
4. **🏮 Use Lantern**: Strategic paralysis when Minotaur gets close
5. **🎯 Escape**: Collect all 3 stones to win!

### **Audio Cues**
- 🔇 **Quiet**: Minotaur far away (>15 units)
- 🔊 **Distant**: Moderate distance (8-15 units)  
- 👣 **Footsteps**: Getting close (3-8 units)
- 😤 **Breathing**: Very close (≤3 units) - RUN!

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

### **Core Components**

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **🎮 UI Layer** | Web interface | Real-time updates, command buttons, AI integration |
| **🔄 LangGraph** | Turn orchestration | 4-node workflow, state management, error handling |
| **⚙️ Game Engine** | Core mechanics | Physics, temporal logic, win/lose conditions |
| **🤖 AI Agents** | Strategic advice | Natural language analysis, game state evaluation |
| **📋 Models** | Type safety | Pydantic validation, JSON contracts, error prevention |

## 📁 Project Structure

```
labyrinth-temporal-hunt/
├── 🎮 src/
│   ├── ui/           # Streamlit web interface
│   ├── graph/        # LangGraph turn loop
│   ├── gsm/          # Game State Manager
│   │   ├── engine.py     # Core game logic
│   │   ├── physics.py    # Movement & collision
│   │   ├── temporal.py   # Time-based mechanics
│   │   └── models.py     # Pydantic contracts
│   ├── agents/       # AI agent implementations
│   └── infra/        # Configuration & settings
├── 🧪 tests/         # Comprehensive test suite (100% coverage)
├── 📋 ADRs/          # Architecture Decision Records
├── 🐳 Docker files   # Containerization
└── 📚 Documentation # Deployment & usage guides
```

## 🧪 Testing

**100 tests passing** across all components:

```bash
# Run all tests
pytest tests/ -v

# Specific test suites
pytest tests/test_turn_loop.py -v      # LangGraph (22 tests)
pytest tests/test_engine_response.py -v # Game engine (11 tests)
pytest tests/test_temporal_logic.py -v  # Temporal mechanics (17 tests)
pytest tests/test_contracts.py -v      # Pydantic models (15 tests)

# Coverage report
pytest tests/ --cov=src --cov-report=html
```

### **Test Categories**
- ✅ **Unit Tests**: Individual component validation
- ✅ **Integration Tests**: Cross-component workflows  
- ✅ **End-to-End Tests**: Complete game scenarios
- ✅ **Error Handling**: Graceful failure modes
- ✅ **Performance Tests**: Turn execution timing

## 🔧 Configuration

### **Environment Variables**
```bash
# Core settings
APP_MODE=production          # development/production
LOG_LEVEL=INFO              # DEBUG/INFO/WARNING/ERROR
RANDOM_SEED=42              # Game randomization

# AI Integration (optional)
MISTRAL_API_KEY=your_key    # For hunter AI agent
GEMINI_API_KEY=your_key     # For minotaur AI agent
```

### **Game Tuning**
Modify `src/gsm/physics.py` for custom gameplay:
```python
GRID_SIZE = 50              # Labyrinth dimensions
STAMINA_DRAIN_RATE = 0.1    # Running exhaustion
SIGHT_RADIUS = 8.0          # Visibility range
MINOTAUR_JUMP_COOLDOWN = 600.0  # Vanish ability cooldown
```

## 🚀 Deployment

### **Production Deployment**
```bash
# Docker production
docker-compose up -d

# With Redis scaling
docker-compose --profile redis up -d

# Health check
curl http://localhost:8501/_stcore/health
```

### **Cloud Platforms**
- **Streamlit Cloud**: Direct deployment from GitHub
- **Heroku**: Buildpack-ready with Procfile
- **AWS/GCP/Azure**: Container service compatible
- **Railway/Render**: One-click deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## 🎯 Game Mechanics Deep Dive

### **Physics System**
- **Grid-based Movement**: Discrete 3D coordinates with collision detection
- **Stamina Management**: Running (speed=2) drains stamina, walking (speed=1) recovers
- **Visibility System**: Dynamic item/path discovery based on position
- **Realistic Timing**: Movement takes time, affecting temporal mechanics

### **Temporal Logic**
```python
# Minotaur state transitions
CHASING_3D → [trigger_jump] → VANISHED (5-10s) → CHASING_3D
CHASING_3D → [lantern_use] → PARALYZED (120s) → CHASING_3D

# Cooldowns prevent exploitation
Jump Cooldown: 600s (10 minutes)
Lantern Respawn: 720s (12 minutes)
```

### **AI Behavior**
```python
# Distance-based Minotaur decisions
distance > 10.0:  JUMP (vanish and relocate)
distance > 5.0:   PATHFIND (move strategically)
distance ≤ 5.0:   CHASE (direct pursuit)
game_over:        WAIT (no action needed)
```

## 🤝 Contributing

### **Development Setup**
```bash
# Fork and clone
git clone https://github.com/yourusername/labyrinth-temporal-hunt.git
cd labyrinth-temporal-hunt

# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

### **Code Standards**
- **Type Hints**: All functions must have type annotations
- **Pydantic Models**: Use for all data structures
- **Test Coverage**: Maintain 100% coverage
- **Documentation**: Update ADRs for architectural changes

## 📊 Performance

### **Benchmarks**
- **Turn Execution**: < 100ms average
- **Memory Usage**: ~100MB per instance
- **Test Suite**: < 5 seconds complete run
- **Startup Time**: < 3 seconds to ready state

### **Scalability**
- **Stateless Design**: Horizontal scaling ready
- **No External Dependencies**: Core game works offline
- **Efficient State Management**: Minimal memory footprint
- **Docker Optimized**: Multi-stage builds, small images

## 🎖️ Recognition

This project demonstrates:
- **🏗️ Production Architecture**: Clean, scalable, maintainable code
- **🧪 Testing Excellence**: Comprehensive validation and error handling  
- **🤖 AI Integration**: Modern LLM workflow orchestration
- **📚 Documentation**: Thorough guides and architectural decisions
- **🚀 DevOps Ready**: Complete containerization and deployment

Perfect for:
- **Portfolio Showcase**: Demonstrates advanced Python/AI skills
- **Research Platform**: Extensible for AI/game research
- **Learning Resource**: Well-documented, tested codebase
- **Production Use**: Ready for real-world deployment

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangGraph**: Workflow orchestration framework
- **Streamlit**: Rapid web app development
- **Pydantic**: Data validation and settings management
- **Docker**: Containerization platform

---

<div align="center">

**🎮 Ready to enter the labyrinth? 🏛️**

[🚀 Get Started](#-quick-start) • [📖 Documentation](DEPLOYMENT.md) • [🐛 Issues](https://github.com/GTuritto/labyrinth-temporal-hunt/issues) • [💬 Discussions](https://github.com/GTuritto/labyrinth-temporal-hunt/discussions)

</div>
