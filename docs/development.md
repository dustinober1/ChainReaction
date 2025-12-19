# Developer Guide

Complete guide for developing, testing, and contributing to ChainReaction.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Testing](#testing)
- [Adding New Features](#adding-new-features)
- [Plugin Development](#plugin-development)
- [Common Tasks](#common-tasks)
- [Debugging](#debugging)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- Python 3.13+
- Node.js 18+ (for frontend)
- Git
- Docker (optional, for Neo4j)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/dustinober1/ChainReaction.git
cd ChainReaction

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Run tests to verify setup
pytest tests/ -v
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Docker Development (Recommended for Database)

If you have Docker installed, you can run the entire stack or just the database:

```bash
# Start everything (Database, Backend, Frontend)
make docker-up

# Start only the Neo4j database
docker compose up -d neo4j

# Check logs
make docker-logs
```

Using Docker ensures you have the correct Neo4j version and APOC plugins pre-configured.

### Local LLM with Ollama

For a fully local development experience:

1. [Install Ollama](https://ollama.ai/)
2. Pull the recommended model: `ollama pull qwen3:1.7b`
3. Update `.env`:
   ```bash
   LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434 # or http://host.docker.internal:11434 if in Docker
   OLLAMA_MODEL=qwen3:1.7b
   ```

### IDE Configuration

#### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.pylance)
- Black Formatter (ms-python.black-formatter)
- Ruff (charliermarsh.ruff)

Settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

#### PyCharm

1. Set Python interpreter to `.venv`
2. Enable "Format on Save" with Black
3. Install pytest plugin

## Project Structure

```
ChainReaction/
├── src/                        # Main source code
│   ├── analysis/              # DSPy modules and AI analysis
│   │   ├── __init__.py
│   │   ├── signatures.py      # DSPy signatures
│   │   ├── modules.py         # Analysis modules
│   │   ├── validation.py      # Extraction validation
│   │   ├── training.py        # Training data management
│   │   ├── prioritization.py  # Risk prioritization
│   │   ├── reporting.py       # Report generation
│   │   ├── alerts.py          # Multi-channel alert system
│   │   ├── search.py          # Full-text search & filtering
│   │   ├── performance.py     # Caching & batch processing
│   │   ├── accessibility.py   # WCAG 2.1 AA compliance
│   │   └── plugins.py         # Plugin architecture
│   │
│   ├── api/                   # FastAPI REST API
│   │   ├── __init__.py
│   │   ├── main.py            # API application
│   │   ├── routes.py          # API routes (v1)
│   │   ├── routes_v2.py       # API routes (v2)
│   │   ├── auth.py            # Authentication
│   │   ├── webhooks.py        # Webhook management
│   │   └── webhooks_routes.py # Webhook endpoints
│   │
│   ├── data/                  # Data management
│   │   ├── __init__.py
│   │   ├── import_export.py   # Import/export utilities
│   │   └── entity_manager.py  # Entity CRUD operations
│   │
│   ├── graph/                 # Graph database integration
│   │   ├── __init__.py
│   │   ├── client.py          # Neo4j client
│   │   ├── impact_tracer.py   # Impact path tracing
│   │   └── queries.py         # Cypher query templates
│   │
│   ├── scout/                 # Data collection agent
│   │   ├── __init__.py
│   │   ├── agent.py           # Scout agent
│   │   ├── sources.py         # News source adapters
│   │   └── rate_limiter.py    # Rate limiting
│   │
│   ├── workflow/              # LangGraph orchestration
│   │   ├── __init__.py
│   │   ├── executor.py        # Workflow executor
│   │   ├── nodes.py           # Workflow nodes
│   │   └── state.py           # Workflow state
│   │
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic data models
│   └── interfaces.py          # ABC interfaces
│
├── frontend/                  # Next.js dashboard
│   ├── app/
│   │   ├── components/        # React components
│   │   ├── utils/             # Dashboard utilities
│   │   ├── globals.css        # Global styles
│   │   ├── layout.tsx         # Root layout
│   │   └── page.tsx           # Main page
│   └── package.json
│
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── property/              # Property-based tests (334 tests)
│   ├── integration/           # Integration tests
│   └── conftest.py            # Pytest fixtures
│
├── docs/                      # Documentation
│   ├── architecture.md
│   ├── api.md
│   ├── development.md
│   ├── deployment.md
│   └── models.md
│
├── .env.example               # Environment template
├── pyproject.toml             # Python project config
└── README.md
```

### Analysis Module Overview

| Module             | Purpose                | Key Classes                     |
| ------------------ | ---------------------- | ------------------------------- |
| `modules.py`       | DSPy analysis modules  | `RiskAnalyst`, `EntityAnalyst`  |
| `alerts.py`        | Multi-channel alerting | `AlertManager`, `AlertRule`     |
| `search.py`        | Full-text search       | `SearchEngine`, `SearchFilter`  |
| `performance.py`   | Caching & batching     | `QueryCache`, `BatchProcessor`  |
| `accessibility.py` | WCAG 2.1 AA compliance | `ColorContrastChecker`          |
| `plugins.py`       | Plugin architecture    | `PluginManager`, `SourcePlugin` |

## Code Style

### Python

We use Black for formatting and Ruff for linting.

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Fix auto-fixable issues
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Style Guidelines

1. **Type hints**: Always use type hints for function parameters and returns
```python
def calculate_risk(severity: SeverityLevel, confidence: float) -> float:
    ...
```

2. **Docstrings**: Use Google-style docstrings
```python
def trace_impact(self, supplier_id: str) -> list[ImpactPath]:
    """
    Trace impact paths from a supplier through the supply chain.
    
    Args:
        supplier_id: The ID of the affected supplier.
    
    Returns:
        List of impact paths to affected products.
    
    Raises:
        ValueError: If supplier_id is not found.
    """
```

3. **Naming conventions**:
   - Classes: `PascalCase`
   - Functions/methods: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: Leading underscore `_private_method`

### TypeScript/React

```bash
cd frontend

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

## Testing

### Test Categories

| Type        | Directory                 | Tests | Purpose                                 |
| ----------- | ------------------------- | ----- | --------------------------------------- |
| Unit        | `tests/unit/`             | 156   | Test individual components in isolation |
| Property    | `tests/property/`         | 334   | Hypothesis-based property tests         |
| Integration | `tests/integration/`      | 12    | Test component interactions             |
| Frontend    | `frontend/app/__tests__/` | 37    | Jest tests for dashboard utilities      |

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/unit/ -v
pytest tests/property/ -v
pytest tests/integration/ -v

# Run specific file
pytest tests/property/test_alerts.py -v

# Run specific test
pytest tests/unit/test_models.py::TestRiskEvent::test_creation -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Run with verbose output
pytest tests/ -v --tb=long

# Run failed tests only
pytest tests/ --lf
```

### Property Test Coverage

ChainReaction uses property-based testing extensively with Hypothesis:

| Module        | Properties Tested                           | Tests |
| ------------- | ------------------------------------------- | ----- |
| Models        | ID generation, validation, serialization    | 40    |
| DSPy          | Extraction, entity linking, assessment      | 32    |
| Graph         | Path traversal, redundancy, alternatives    | 24    |
| Workflow      | State management, event flow                | 20    |
| API           | Response format, authentication             | 24    |
| Alerts        | Rules, channels, escalation, acknowledgment | 27    |
| Search        | Full-text, filters, export                  | 25    |
| Performance   | Caching, batching, monitoring               | 28    |
| Accessibility | Color contrast, keyboard nav, dictionary    | 26    |
| Plugins       | Registration, lifecycle, compatibility      | 28    |
| Dashboard     | Visualization utilities                     | 37    |

### Writing Tests

#### Unit Tests

```python
# tests/unit/test_example.py
import pytest
from src.analysis.prioritization import RiskPrioritizer

class TestRiskPrioritizer:
    """Tests for RiskPrioritizer."""
    
    def test_priority_weights_sum_to_one(self):
        """Test that default weights sum to 1.0."""
        prioritizer = RiskPrioritizer()
        assert prioritizer.weights.validate()
    
    def test_critical_has_highest_score(self):
        """Test that critical severity has highest score."""
        prioritizer = RiskPrioritizer()
        assert prioritizer.SEVERITY_SCORES[SeverityLevel.CRITICAL] == 1.0
```

#### Property Tests

```python
# tests/property/test_example.py
import pytest
from hypothesis import given, strategies as st

class TestRiskScoring:
    """Property-based tests for risk scoring."""
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_score_is_bounded(self, confidence: float):
        """Property: All scores should be between 0 and 1."""
        score = calculate_score(confidence)
        assert 0.0 <= score <= 1.0
```

### Test Fixtures

Common fixtures are in `tests/conftest.py`:

```python
@pytest.fixture
def sample_risk():
    """Create a sample risk event for testing."""
    return RiskEvent(
        id="RISK-TEST",
        event_type=EventType.WEATHER,
        description="Test risk",
        location="Taiwan",
        severity=SeverityLevel.HIGH,
        confidence=0.9,
        detected_at=datetime.now(timezone.utc),
        source_url="https://example.com",
        affected_entities=["TSMC"],
    )

@pytest.fixture
def entity_manager():
    """Create an EntityManager for testing."""
    return EntityManager()
```

## Adding New Features

### 1. Adding a New Event Type

1. Update the `EventType` enum in `src/models.py`:
```python
class EventType(str, Enum):
    # ... existing types
    NEW_TYPE = "NewType"
```

2. Add extraction rules in `src/analysis/signatures.py`

3. Add tests in `tests/unit/test_models.py`

### 2. Adding a New API Endpoint

1. Add the route in `src/api/routes.py` (v1) or `src/api/routes_v2.py` (v2):
```python
@router.get("/new-endpoint")
async def new_endpoint(api_key: str = Depends(require_api_key)):
    """New endpoint description."""
    return APIResponse(success=True, data={"message": "Hello"})
```

2. Add tests in `tests/unit/test_api.py`

3. Update API documentation in `docs/api.md`

### 3. Adding a New Scout Source

1. Create source adapter in `src/scout/sources.py`:
```python
class NewSource(BaseSource):
    """Adapter for new data source."""
    
    async def fetch_events(self) -> list[RawEvent]:
        # Implementation
        pass
```

2. Register in `ScoutAgent`

3. Add tests and documentation

### 4. Adding a New Analysis Module

See [Plugin Development](#plugin-development) for extending analysis capabilities.

## Plugin Development

ChainReaction supports custom plugins for extensibility.

### Plugin Types

| Type            | Base Class             | Purpose                    |
| --------------- | ---------------------- | -------------------------- |
| **Source**      | `SourcePlugin`         | Custom data sources        |
| **Analysis**    | `AnalysisPlugin`       | Custom DSPy modules        |
| **Integration** | `IntegrationPlugin`    | Bidirectional integrations |
| **Risk Type**   | Via `RiskTypeRegistry` | Custom risk definitions    |

### Creating a Source Plugin

```python
from src.analysis.plugins import (
    SourcePlugin,
    PluginMetadata,
    PluginVersion,
    PluginType,
)
from typing import Any

class MyCustomSource(SourcePlugin):
    """Custom news source plugin."""
    
    def __init__(self, api_key: str):
        super().__init__()
        self._api_key = api_key
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my-custom-source",
            name="My Custom Source",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.SOURCE,
            description="Custom news source for supply chain events",
            author="Your Name",
        )
    
    def fetch_data(self) -> list[dict[str, Any]]:
        """Fetch data from the custom source."""
        # Your implementation here
        return [
            {"id": "evt-1", "content": "Event content..."}
        ]
    
    def get_source_info(self) -> dict[str, Any]:
        """Return source metadata."""
        return {
            "type": "custom_api",
            "url": "https://api.example.com",
        }

# Register with plugin manager
from src.analysis.plugins import PluginManager

manager = PluginManager()
plugin = MyCustomSource(api_key="...")
manager.register_plugin(plugin)
manager.activate_plugin("my-custom-source")

# Collect data from all sources
data = manager.collect_source_data()
```

### Creating an Analysis Plugin

```python
from src.analysis.plugins import (
    AnalysisPlugin,
    PluginMetadata,
    PluginVersion,
    PluginType,
)

class CustomSentimentAnalyzer(AnalysisPlugin):
    """Custom sentiment analysis plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="sentiment-analyzer",
            name="Sentiment Analyzer",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.ANALYSIS,
        )
    
    def analyze(self, data: dict) -> dict:
        """Perform sentiment analysis."""
        content = data.get("content", "")
        # Your analysis logic
        return {
            "sentiment": "negative",
            "score": 0.85,
            "keywords": ["disruption", "delay"],
        }
    
    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"}
            }
        }
```

### Registering Custom Risk Types

```python
from src.analysis.plugins import RiskTypeRegistry, CustomRiskType

registry = RiskTypeRegistry()

# Register a custom risk type
registry.register(CustomRiskType(
    type_id="cyber_attack",
    name="Cyber Attack",
    description="Cyber security incidents affecting supply chain",
    severity_default="Critical",
    keywords=["ransomware", "breach", "hack", "malware"],
    extraction_patterns=[r"cyber\s*attack", r"data\s*breach"],
    color="#dc2626",
    icon="shield-alert",
))

# Add custom extraction rules
registry.add_extraction_rule(
    "cyber_attack",
    lambda text: "zero-day" in text.lower(),
)

# Match text
matches = registry.match_text("Ransomware attack disrupts factory operations")
# ['cyber_attack']
```

### Plugin Lifecycle

```
UNLOADED → LOADED → INITIALIZED → ACTIVE → DISABLED → UNLOADED
```

```python
plugin = MyPlugin()
plugin.load()        # LOADED
plugin.initialize()  # INITIALIZED
plugin.activate()    # ACTIVE
plugin.deactivate()  # DISABLED
plugin.unload()      # UNLOADED
```

## Common Tasks

### Generating Sample Data

```python
from src.data import EntityManager

manager = EntityManager()

# Create suppliers
manager.create_supplier(name="TSMC", location="Taiwan", tier=1)
manager.create_supplier(name="Samsung", location="South Korea", tier=1)

# Create components
manager.create_component(name="CPU Chip", category="Semiconductors")

# Create products
manager.create_product(name="Smartphone", product_line="Mobile")

# Create relationships
manager.add_supplies_relation("SUP-001", "COMP-001")
manager.add_part_of_relation("COMP-001", "PROD-001")
```

### Using the Search Engine

```python
from src.analysis.search import SearchEngine, SearchFilter, FilterOperator

engine = SearchEngine()

# Index some events
engine.index_event({
    "id": "RISK-001",
    "event_type": "weather",
    "location": "Taiwan",
    "severity": "High",
})

# Search with filters
results = engine.search(
    query="semiconductor shortage",
    filters=[
        SearchFilter(
            field="severity",
            operator=FilterOperator.IN,
            value=["High", "Critical"]
        ),
        SearchFilter(
            field="location",
            operator=FilterOperator.EQUALS,
            value="Taiwan"
        ),
    ],
    limit=10
)
```

### Using the Alert System

```python
from src.analysis.alerts import AlertManager, AlertRule, DeliveryChannel

manager = AlertManager()

# Create a rule
rule = AlertRule(
    id="rule-001",
    name="Critical Alert Rule",
    conditions={"severity": ["Critical"]},
    channels=[DeliveryChannel.EMAIL, DeliveryChannel.SLACK],
    recipients=["alerts@company.com"],
)
manager.register_rule(rule)

# Evaluate and send alerts
triggered = manager.evaluate_rules(risk_event)
for alert in triggered:
    manager.send_alert(alert)
```

### Running the Workflow

```python
import asyncio
from src.workflow import RiskDetectionWorkflow

async def main():
    workflow = RiskDetectionWorkflow()
    result = await workflow.run()
    print(f"Detected {len(result.risk_events)} risks")

asyncio.run(main())
```

### Generating Reports

```python
from src.analysis import ReportGenerator

generator = ReportGenerator()
report = generator.generate_report(risk_event, impact_assessment)

# Export as JSON
json_report = generator.export_json(report)

# Export as Markdown
md_report = generator.export_markdown(report)
```

## Debugging

### Logging

ChainReaction uses `structlog` for structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Processing event", event_id="EVT-001", source="tavily")
logger.error("Failed to trace impact", error=str(e), supplier_id="SUP-001")
```

Set log level in `.env`:
```
LOG_LEVEL=DEBUG
```

### Common Issues

#### Import Errors

```bash
# Ensure package is installed in development mode
pip install -e .

# Check Python path
python -c "import src; print(src.__file__)"
```

#### Neo4j Connection Issues

```bash
# Check Neo4j is running
curl http://localhost:7474

# Verify credentials in .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

#### Test Failures

```bash
# Run with verbose output
pytest tests/ -v --tb=long

# Run specific failing test
pytest tests/unit/test_models.py::test_name -v --pdb
```

## Contributing

### Git Workflow

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and commit:
```bash
git add -A
git commit -m "feat: Add new feature

Detailed description of the changes."
```

3. Push and create PR:
```bash
git push origin feature/your-feature-name
```

### Commit Message Format

Follow conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Pull Request Checklist

- [ ] Tests pass: `pytest tests/ -v`
- [ ] Code formatted: `black src/ tests/`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Documentation updated
- [ ] Commit messages follow convention

### Code Review Guidelines

1. Check for correctness
2. Verify test coverage
3. Review error handling
4. Ensure documentation is complete
5. Validate performance implications
