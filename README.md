# ChainReaction

**Autonomous Supply Chain Risk Monitor** using GraphRAG, DSPy, and LangGraph.

## Overview

ChainReaction is an AI-powered system that maintains a knowledge graph of a company's products and suppliers, continuously monitoring global events to instantly calculate downstream impacts on supply chain operations.

### Key Features

- **🔍 Autonomous Monitoring**: Scout Agents continuously scan news sources for supply chain disruptions
- **🧠 Intelligent Extraction**: DSPy-optimized modules ensure reliable extraction from unstructured news
- **📊 Graph-Based Analysis**: Neo4j-powered GraphRAG for relationship-aware impact assessment
- **⚡ Real-Time Alerts**: Instant notifications when risks affect your products
- **🎯 Interactive Dashboard**: Visualize supply chain relationships and risks

## Tech Stack

| Component            | Technology                  |
| -------------------- | --------------------------- |
| **Frontend**         | Next.js + React Force Graph |
| **Backend API**      | FastAPI                     |
| **Orchestration**    | LangGraph                   |
| **Graph Database**   | Neo4j                       |
| **LLM Optimization** | DSPy                        |
| **Testing**          | Pytest + Hypothesis         |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Neo4j 5.x (or Neo4j Aura account)
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ChainReaction.git
cd ChainReaction

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment configuration
cp .env.example .env
# Edit .env with your credentials
```

### Running the System

```bash
# Start the backend API
uvicorn src.api.main:app --reload

# In another terminal, start the frontend
cd src/frontend
npm install
npm run dev
```

## Project Structure

```
ChainReaction/
├── src/
│   ├── agents/          # LangGraph orchestration & Scout Agents
│   ├── analysis/        # DSPy extraction modules
│   ├── graph/           # Neo4j connection & GraphRAG engine
│   ├── api/             # FastAPI endpoints
│   └── frontend/        # Next.js dashboard
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── property/        # Property-based tests (Hypothesis)
├── data/                # Sample data and generated datasets
├── scripts/             # Utility scripts
└── .kiro/specs/         # Project specifications
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Data Sources                        │
│              (News APIs, Event Databases, Social)                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                        Agent Layer                               │
│              Scout Agent ◄──► LangGraph Orchestrator             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Analysis Layer                              │
│         DSPy Analyst ◄──► Risk Extractor ◄──► Validator          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Knowledge Layer                             │
│           Neo4j Graph DB ◄──► GraphRAG Engine ◄──► Impact Calc   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Presentation Layer                           │
│              REST API ◄──► Dashboard ◄──► Alerts                 │
└─────────────────────────────────────────────────────────────────┘
```

## Testing

```bash
# Run all tests
pytest

# Run property-based tests only
pytest -m property

# Run with coverage
pytest --cov=src --cov-report=html
```

## License

MIT License - see [LICENSE](LICENSE) for details.
