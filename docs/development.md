# Developer Guide

Complete guide for developing, testing, and contributing to ChainReaction.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Testing](#testing)
- [Adding New Features](#adding-new-features)
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
│   │   └── reporting.py       # Report generation
│   │
│   ├── api/                   # FastAPI REST API
│   │   ├── __init__.py
│   │   ├── main.py            # API application
│   │   ├── routes.py          # API routes
│   │   ├── auth.py            # Authentication
│   │   └── webhooks.py        # Webhook management
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
│   │   ├── globals.css        # Global styles
│   │   ├── layout.tsx         # Root layout
│   │   └── page.tsx           # Main page
│   └── package.json
│
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── property/              # Property-based tests
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

| Type        | Directory            | Purpose                                 |
| ----------- | -------------------- | --------------------------------------- |
| Unit        | `tests/unit/`        | Test individual components in isolation |
| Property    | `tests/property/`    | Hypothesis-based property tests         |
| Integration | `tests/integration/` | Test component interactions             |

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/unit/ -v
pytest tests/property/ -v
pytest tests/integration/ -v

# Run specific file
pytest tests/unit/test_models.py -v

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

1. Add the route in `src/api/routes.py`:
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
