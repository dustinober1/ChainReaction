# ChainReaction

**AI-Powered Supply Chain Risk Monitoring System**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-289%20passing-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

ChainReaction is an intelligent supply chain risk monitoring platform that combines real-time news analysis, graph-based impact tracing, and AI-powered risk assessment to proactively identify and prioritize supply chain disruptions.

## 🚀 Features

- **Autonomous Monitoring**: Scout Agent continuously monitors news sources for supply chain events
- **AI-Powered Analysis**: DSPy-based risk extraction with confidence scoring
- **Graph-Based Impact Tracing**: Neo4j-powered GraphRAG engine traces multi-hop impact paths
- **Multi-Agent Orchestration**: LangGraph coordinates specialized agents for comprehensive analysis
- **Real-Time Alerts**: Webhook-based notification system with configurable triggers
- **Interactive Dashboard**: Next.js frontend with force-directed graph visualization
- **REST API**: FastAPI backend with authentication, rate limiting, and standardized responses
- **Local LLM Support**: Run entirely locally with Ollama - no API keys required!

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [LLM Configuration](#-llm-configuration)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Frontend Dashboard](#-frontend-dashboard)
- [Testing](#-testing)
- [Documentation](#-documentation)

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/dustinober1/ChainReaction.git
cd ChainReaction

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env with your API keys (or configure Ollama for local LLM)

# Run tests
pytest tests/ -v

# Start the API server
python -m uvicorn src.api.main:app --reload

# Start the frontend (in another terminal)
cd frontend
npm install
npm run dev
```

## 🏗️ Architecture

ChainReaction uses a modular, event-driven architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ChainReaction System                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────┐    ┌────────────┐    ┌─────────────┐                │
│  │   Scout   │───▶│   DSPy     │───▶│  GraphRAG   │                │
│  │   Agent   │    │  Analysis  │    │   Engine    │                │
│  └───────────┘    └────────────┘    └─────────────┘                │
│       │                │                   │                        │
│       ▼                ▼                   ▼                        │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │              LangGraph Orchestration                     │       │
│  └─────────────────────────────────────────────────────────┘       │
│                            │                                        │
│       ┌────────────────────┴────────────────────┐                  │
│       ▼                                         ▼                   │
│  ┌─────────┐                              ┌───────────┐            │
│  │  REST   │◀────────────────────────────▶│  Neo4j    │            │
│  │   API   │                              │  Database │            │
│  └─────────┘                              └───────────┘            │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │                  Next.js Dashboard                       │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │       │
│  │  │  Graph   │  │   Chat   │  │  Alerts  │              │       │
│  │  │   View   │  │ Interface│  │  Panel   │              │       │
│  │  └──────────┘  └──────────┘  └──────────┘              │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component              | Description                                   | Technology                 |
| ---------------------- | --------------------------------------------- | -------------------------- |
| **Scout Agent**        | Monitors news sources for supply chain events | Python, HTTPX, Tavily API  |
| **DSPy Analysis**      | Extracts risks, entities, and assessments     | DSPy, OpenAI/Ollama        |
| **GraphRAG Engine**    | Traces impact paths through supply chain      | Neo4j, Cypher              |
| **LangGraph Workflow** | Orchestrates multi-agent processing           | LangGraph                  |
| **REST API**           | Provides data access and management           | FastAPI                    |
| **Web Dashboard**      | Interactive visualization interface           | Next.js, React Force Graph |

## 📦 Installation

### Prerequisites

- Python 3.13+
- Node.js 18+
- Neo4j 5.x (optional, for production)
- **Either**: OpenAI API key **or** Ollama (for local LLM)

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
python -c "import src; print('ChainReaction installed successfully')"
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Database Setup (Optional)

For production use with Neo4j:

```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  neo4j:5

# Update .env with Neo4j credentials
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

## 🤖 LLM Configuration

ChainReaction supports both **OpenAI** and **Ollama** for AI-powered analysis.

### Option 1: OpenAI (Cloud)

Best for: Production deployments, highest quality results

```bash
# In .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### Option 2: Ollama (Local)

Best for: Development, privacy-sensitive deployments, no API costs

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull qwen3:1.7b

# 3. Configure .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:1.7b
```

### Recommended Ollama Models

| Model          | Size | Quality | Speed | Best For                   |
| -------------- | ---- | ------- | ----- | -------------------------- |
| `qwen3:1.7b`   | 1.7B | ★★★☆☆   | ★★★★★ | Development, fast testing  |
| `llama3.2`     | 3B   | ★★★☆☆   | ★★★★★ | Development, quick testing |
| `llama3.1`     | 8B   | ★★★★☆   | ★★★★☆ | Balanced performance       |
| `llama3.1:70b` | 70B  | ★★★★★   | ★★☆☆☆ | Production quality         |
| `mistral`      | 7B   | ★★★★☆   | ★★★★★ | Fast and capable           |
| `mixtral`      | 8x7B | ★★★★★   | ★★★☆☆ | Best open-source quality   |

### Checking LLM Status

```bash
# Check which LLM is configured
curl http://localhost:8000/health

# Check LLM availability
curl http://localhost:8000/llm/status
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```bash
# Application
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here

# LLM Provider (openai or ollama)
LLM_PROVIDER=openai

# OpenAI (if using OpenAI)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Ollama (if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:1.7b

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# News APIs
TAVILY_API_KEY=tvly-your-key-here
NEWS_API_KEY=your-newsapi-key-here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=dev-api-key-12345

# Monitoring
MONITOR_INTERVAL=300
MAX_EVENTS_PER_CYCLE=50
CONFIDENCE_THRESHOLD=0.7
```

## 📡 API Reference

### Authentication

All API endpoints (except health checks) require an API key:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/risks
```

### Endpoints

#### Risks

| Method   | Endpoint                           | Description         |
| -------- | ---------------------------------- | ------------------- |
| `GET`    | `/api/v1/risks`                    | List all risks      |
| `POST`   | `/api/v1/risks`                    | Create a risk event |
| `GET`    | `/api/v1/risks/{id}`               | Get risk by ID      |
| `DELETE` | `/api/v1/risks/{id}`               | Delete a risk       |
| `GET`    | `/api/v1/risks/query/product/{id}` | Query product risks |

#### Supply Chain

| Method | Endpoint                          | Description     |
| ------ | --------------------------------- | --------------- |
| `GET`  | `/api/v1/supply-chain/suppliers`  | List suppliers  |
| `GET`  | `/api/v1/supply-chain/components` | List components |
| `GET`  | `/api/v1/supply-chain/products`   | List products   |
| `GET`  | `/api/v1/supply-chain/stats`      | Get statistics  |

#### Alerts

| Method | Endpoint                          | Description       |
| ------ | --------------------------------- | ----------------- |
| `GET`  | `/api/v1/alerts`                  | List alerts       |
| `GET`  | `/api/v1/alerts/{id}`             | Get alert by ID   |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |

#### Webhooks

| Method   | Endpoint                     | Description       |
| -------- | ---------------------------- | ----------------- |
| `GET`    | `/api/v1/webhooks`           | List webhooks     |
| `POST`   | `/api/v1/webhooks`           | Register webhook  |
| `PATCH`  | `/api/v1/webhooks/{id}`      | Update webhook    |
| `DELETE` | `/api/v1/webhooks/{id}`      | Delete webhook    |
| `POST`   | `/api/v1/webhooks/{id}/test` | Send test webhook |

### Response Format

All responses follow a standardized format:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

## 🖥️ Frontend Dashboard

The dashboard provides an interactive interface for exploring supply chain risks:

### Starting the Dashboard

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

### Features

- **Graph Visualization**: Interactive force-directed graph showing suppliers, components, and products
- **Risk Highlighting**: Color-coded nodes (red = risk source, orange = at-risk)
- **Chat Interface**: Natural language queries about supply chain risks
- **Alerts Panel**: Real-time alert monitoring with acknowledgment

## 🧪 Testing

ChainReaction includes comprehensive testing with 289 tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test types
pytest tests/unit/ -v           # Unit tests (156)
pytest tests/property/ -v       # Property tests (121)
pytest tests/integration/ -v    # Integration tests (12)

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py -v
```

### Test Categories

| Category    | Tests | Description                     |
| ----------- | ----- | ------------------------------- |
| Unit        | 156   | Component isolation tests       |
| Property    | 121   | Hypothesis-based property tests |
| Integration | 12    | End-to-end workflow tests       |

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- [Architecture Guide](docs/architecture.md) - System design and components
- [API Documentation](docs/api.md) - Complete API reference
- [Developer Guide](docs/development.md) - Setup and contribution guide
- [Deployment Guide](docs/deployment.md) - Production deployment
- [Data Models](docs/models.md) - Data structures and schemas

## 🔧 Development

### Project Structure

```
ChainReaction/
├── src/
│   ├── analysis/       # DSPy modules, prioritization, reporting
│   ├── api/            # FastAPI routes, auth, webhooks
│   ├── data/           # Import/export, entity management
│   ├── graph/          # GraphRAG engine, impact tracing
│   ├── scout/          # Scout Agent, news monitoring
│   ├── workflow/       # LangGraph orchestration
│   ├── config.py       # Configuration management
│   └── models.py       # Pydantic data models
├── frontend/
│   └── app/
│       ├── components/ # React components
│       └── page.tsx    # Main dashboard
├── tests/
│   ├── unit/           # Unit tests
│   ├── property/       # Property-based tests
│   └── integration/    # Integration tests
├── docs/               # Documentation
└── .env.example        # Environment template
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [DSPy](https://github.com/stanfordnlp/dspy) for structured AI interactions
- Graph database powered by [Neo4j](https://neo4j.com/)
- Workflow orchestration with [LangGraph](https://github.com/langchain-ai/langgraph)
- Frontend visualization with [React Force Graph](https://github.com/vasturiano/react-force-graph)
