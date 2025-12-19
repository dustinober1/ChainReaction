# Architecture Guide

This document provides a detailed overview of ChainReaction's architecture, design decisions, and component interactions.

## Table of Contents

- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Analysis Modules](#analysis-modules)
- [Data Flow](#data-flow)
- [Design Principles](#design-principles)
- [Technology Stack](#technology-stack)
- [Component Deep Dives](#component-deep-dives)
- [Plugin Architecture](#plugin-architecture)
- [Performance Optimization](#performance-optimization)
- [Accessibility](#accessibility)

## System Overview

ChainReaction is designed as a modular, event-driven system that continuously monitors external news sources, analyzes potential supply chain risks, traces impact through a graph database, and delivers actionable alerts to stakeholders.

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              External Sources                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  News APIs   │  │  RSS Feeds   │  │  Webhooks    │  │   Custom     │   │
│  │   (Tavily)   │  │              │  │   (Inbound)  │  │   Plugins    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            Scout Agent Layer                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  • Configurable monitoring intervals                                  │  │
│  │  • Rate limiting per source                                           │  │
│  │  • Error handling with exponential backoff                            │  │
│  │  • Raw event normalization                                            │  │
│  │  • Plugin support for custom sources                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (RawEvent)
┌────────────────────────────────────────────────────────────────────────────┐
│                            Analysis Layer (DSPy)                            │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │ RiskExtractor │  │EntityExtractor│  │ImpactAssessor │                   │
│  │               │──▶               │──▶               │                   │
│  │ • Event type  │  │ • Suppliers   │  │ • Severity    │                   │
│  │ • Severity    │  │ • Components  │  │ • Paths       │                   │
│  │ • Location    │  │ • Products    │  │ • Options     │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │    Alerts     │  │    Search     │  │  Performance  │                   │
│  │               │  │               │  │               │                   │
│  │ • Multi-chan  │  │ • Full-text   │  │ • Caching     │                   │
│  │ • Escalation  │  │ • Filtering   │  │ • Batching    │                   │
│  │ • Ack tracking│  │ • Export      │  │ • Monitoring  │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (RiskEvent, ImpactAssessment)
┌────────────────────────────────────────────────────────────────────────────┐
│                         GraphRAG Engine Layer                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Neo4j Graph Database                                                 │  │
│  │  ┌─────────┐  ────SUPPLIES────▶  ┌───────────┐  ────PART_OF────▶     │  │
│  │  │Supplier │                     │ Component │                        │  │
│  │  │   🔵    │◀────BACKUP_FOR────  │    🟣     │                        │  │
│  │  └─────────┘                     └───────────┘                        │  │
│  │                                                     ┌─────────┐       │  │
│  │                                                     │ Product │       │  │
│  │                                                     │   🟢    │       │  │
│  │                                                     └─────────┘       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Impact Path Tracer                                                   │  │
│  │  • Multi-hop traversal                                                │  │
│  │  • Redundancy calculation                                             │  │
│  │  • Alternative path detection                                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        LangGraph Orchestration                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        Workflow State Machine                         │  │
│  │                                                                       │  │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐           │  │
│  │  │ Monitor │───▶│ Analyze │───▶│  Trace  │───▶│  Alert  │           │  │
│  │  │  Node   │    │  Node   │    │  Node   │    │  Node   │           │  │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘           │  │
│  │       │              │              │              │                 │  │
│  │       └──────────────┴──────────────┴──────────────┘                 │  │
│  │                           State                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
┌────────────────────────────────┐  ┌────────────────────────────────────────┐
│          REST API (v1 & v2)    │  │              Webhooks                   │
│  • Authentication              │  │  • Event-based delivery                │
│  • Rate limiting               │  │  • HMAC signature verification         │
│  • Standardized responses      │  │  • Retry with exponential backoff      │
│  • Resilience metrics (v2)     │  │  • Multi-channel (email, Slack)        │
│  • Advanced search (v2)        │  │                                        │
└────────────────────────────────┘  └────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Frontend Dashboard                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │   Graph View     │  │   Chat Interface │  │   Alerts Panel   │         │
│  │   (Force Graph)  │  │   (AI Queries)   │  │   (Real-time)    │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │    Risk Map      │  │ Severity Filter  │  │  Node Details    │         │
│  │  (Geographic)    │  │  (WCAG AA)       │  │    Panel         │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
└────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Scout Agent (`src/scout/`)

The Scout Agent is responsible for autonomous data collection from external sources.

**Key Features:**
- Configurable monitoring intervals
- Multi-source support (Tavily, NewsAPI, custom plugins)
- Rate limiting per source
- Error handling with retries
- Raw event normalization

**Design Pattern:** Observer pattern with event queuing

```python
# Example: Starting the Scout Agent
from src.scout import ScoutAgent

agent = ScoutAgent()
await agent.start_monitoring()
```

### 2. DSPy Analysis Module (`src/analysis/`)

Provides AI-powered extraction and analysis using DSPy signatures.

**Components:**
- `RiskExtractor`: Extracts risk events from raw text
- `EntityExtractor`: Links entities to supply chain graph
- `ImpactAssessor`: Assesses severity and generates mitigations
- `ExtractionValidator`: Validates extraction quality

**Design Pattern:** Chain of Responsibility

```python
# Example: Extracting risks
from src.analysis import RiskAnalyst

analyst = RiskAnalyst()
risk = analyst.forward(content="Typhoon warning for Taiwan...")
```

### 3. GraphRAG Engine (`src/graph/`)

Graph-based retrieval-augmented generation for impact analysis.

**Features:**
- Multi-hop path traversal
- Redundancy level calculation
- Alternative source detection
- Priority-based traversal

**Design Pattern:** Strategy pattern for path algorithms

```python
# Example: Tracing impact
from src.graph import ImpactTracer

tracer = ImpactTracer(neo4j_client)
paths = tracer.trace_impact(supplier_id="SUP-001")
```

### 4. LangGraph Workflow (`src/workflow/`)

Orchestrates the complete risk detection pipeline.

**Nodes:**
1. **Monitor Node**: Fetches events from Scout Agent
2. **Analyze Node**: Processes with DSPy modules
3. **Trace Node**: Traces impact with GraphRAG
4. **Alert Node**: Generates and dispatches alerts

**Design Pattern:** State Machine

```python
# Example: Running workflow
from src.workflow import RiskDetectionWorkflow

workflow = RiskDetectionWorkflow()
result = await workflow.run()
```

### 5. REST API (`src/api/`)

FastAPI-based REST interface for external access.

**Features:**
- API key authentication
- Role-based access control
- Rate limiting
- Standardized response format
- OpenAPI documentation
- v1 and v2 API versions

**Design Pattern:** Router pattern with middleware

### 6. Webhook System (`src/api/webhooks.py`)

Real-time notification delivery system.

**Features:**
- Event-based triggers
- HMAC signature verification
- Retry with exponential backoff
- Delivery tracking

**Design Pattern:** Publisher-Subscriber

### 7. Web Dashboard (`frontend/`)

Interactive visualization interface.

**Components:**
- `SupplyChainGraph`: Force-directed graph visualization
- `ChatInterface`: Natural language query interface
- `AlertsPanel`: Real-time alert monitoring
- `NodeDetailsPanel`: Entity detail view
- `RiskMap`: Geographic risk visualization
- `SeverityFilter`: Severity-based filtering

**Design Pattern:** Component-based architecture

## Analysis Modules

ChainReaction includes comprehensive analysis modules in `src/analysis/`:

| Module            | File               | Description                      |
| ----------------- | ------------------ | -------------------------------- |
| **Core Analysis** | `modules.py`       | DSPy signatures and modules      |
| **Validation**    | `validation.py`    | Extraction quality validation    |
| **Alerts**        | `alerts.py`        | Multi-channel alerting system    |
| **Search**        | `search.py`        | Full-text search and filtering   |
| **Performance**   | `performance.py`   | Caching and batch processing     |
| **Accessibility** | `accessibility.py` | WCAG 2.1 AA compliance utilities |
| **Plugins**       | `plugins.py`       | Extensible plugin architecture   |

### Alerts Module (`src/analysis/alerts.py`)

**Features:**
- Multi-channel delivery (email, Slack, webhooks)
- Escalation rules with configurable timing
- Acknowledgment tracking
- Alert rule definitions
- Delivery status tracking

```python
from src.analysis.alerts import AlertManager, DeliveryChannel

manager = AlertManager()
manager.register_channel(
    DeliveryChannel.EMAIL,
    recipient="alerts@company.com"
)
manager.send_alert(alert)
```

### Search Module (`src/analysis/search.py`)

**Features:**
- Full-text search with fuzzy matching
- Advanced filtering with operators
- Saved search queries
- Export to CSV, JSON, Excel

```python
from src.analysis.search import SearchEngine, SearchFilter

engine = SearchEngine()
results = engine.search(
    query="semiconductor shortage",
    filters=[
        SearchFilter(field="severity", operator="IN", value=["High", "Critical"])
    ]
)
```

### Performance Module (`src/analysis/performance.py`)

**Features:**
- Query caching with TTL (LRU, LFU strategies)
- Batch processing at 100+ events/minute
- Resource monitoring (CPU, memory, disk)
- Data retention policies
- Horizontal scaling support

```python
from src.analysis.performance import QueryCache, BatchProcessor

cache = QueryCache(max_size=1000, default_ttl=300)
cache.set("key", value)
result = cache.get("key")
```

### Accessibility Module (`src/analysis/accessibility.py`)

**Features:**
- WCAG 2.1 AA color contrast checking
- Keyboard navigation support
- Data dictionary generation for exports

```python
from src.analysis.accessibility import ColorContrastChecker

checker = ColorContrastChecker()
ratio = checker.calculate_contrast_ratio("#ffffff", "#000000")  # 21.0
```

## Data Flow

### Event Processing Pipeline

```
1. Scout Agent fetches raw news articles
                    │
                    ▼
2. RawEvent created with metadata
   {source, url, title, content, timestamp}
                    │
                    ▼
3. RiskExtractor analyzes content
   Extracts: event_type, severity, location, entities
                    │
                    ▼
4. EntityExtractor links to graph
   Maps: affected suppliers, components, products
                    │
                    ▼
5. ImpactAssessor evaluates severity
   Calculates: severity_score, redundancy, mitigations
                    │
                    ▼
6. GraphRAG traces impact paths
   Traverses: multi-hop relationships, alternatives
                    │
                    ▼
7. Prioritizer ranks risks
   Scores: severity, timeline, revenue impact
                    │
                    ▼
8. Alert generated and dispatched
   Delivers: email, Slack, webhooks, dashboard
```

### Data Models

```
BaseNode
├── Supplier    (id, name, location, tier, risk_score)
├── Component   (id, name, category, critical)
├── Product     (id, name, product_line, revenue_impact)
└── Location    (id, name, country, region)

RawEvent → RiskEvent → ImpactAssessment → Alert

Relationships:
- Supplier ──SUPPLIES──▶ Component
- Component ──PART_OF──▶ Product
- Supplier ──BACKUP_FOR──▶ Supplier
- Entity ──LOCATED_IN──▶ Location
```

## Design Principles

### 1. Separation of Concerns
Each component has a single responsibility and communicates through well-defined interfaces.

### 2. Event-Driven Architecture
Components communicate through events, enabling loose coupling and scalability.

### 3. Fail-Safe Design
Error handling with graceful degradation and automatic recovery.

### 4. Testability
Property-based testing with Hypothesis ensures correctness invariants. 334 property tests validate all core functionality.

### 5. Configuration-Driven
All thresholds, intervals, and weights are configurable.

### 6. Accessibility First
WCAG 2.1 AA compliance built into all user-facing components.

### 7. Extensibility
Plugin architecture allows custom sources, risk types, and analysis modules.

## Technology Stack

| Layer             | Technology         | Purpose                    |
| ----------------- | ------------------ | -------------------------- |
| **Runtime**       | Python 3.13+       | Backend language           |
| **AI/ML**         | DSPy, OpenAI       | Structured AI interactions |
| **Graph DB**      | Neo4j              | Supply chain relationships |
| **Orchestration** | LangGraph          | Multi-agent coordination   |
| **API**           | FastAPI            | REST interface             |
| **Frontend**      | Next.js 15         | Dashboard UI               |
| **Visualization** | React Force Graph  | Graph rendering            |
| **Testing**       | Pytest, Hypothesis | Test framework             |
| **Validation**    | Pydantic           | Data validation            |

## Component Deep Dives

### Scout Agent Architecture

```
ScoutAgent
├── SourceManager
│   ├── TavilySource
│   ├── NewsAPISource
│   └── PluginSources (extensible)
├── RateLimiter
│   └── Per-source limits
├── EventQueue
│   └── Thread-safe queue
└── ErrorHandler
    └── Retry with backoff
```

### DSPy Module Chain

```
Input: Raw Text Content
           │
    ┌──────┴──────┐
    ▼             ▼
RiskAnalyst  EntityAnalyst
    │             │
    └──────┬──────┘
           ▼
    ImpactAnalyst
           │
           ▼
    ValidationLayer
           │
           ▼
Output: Validated RiskEvent + ImpactAssessment
```

### GraphRAG Query Flow

```
1. Identify affected supplier(s) from location
   MATCH (s:Supplier)-[:LOCATED_IN]->(l:Location {name: $location})
   
2. Find components supplied by affected suppliers
   MATCH (s)-[:SUPPLIES]->(c:Component)
   
3. Trace to products using components
   MATCH (c)-[:PART_OF]->(p:Product)
   
4. Calculate redundancy levels
   MATCH (c)<-[:SUPPLIES]-(alt:Supplier)
   WHERE alt <> s
   
5. Return impact paths with alternatives
```

### API Request Flow

```
Request
    │
    ▼
┌─────────────┐
│ Rate Limiter│
└─────────────┘
    │
    ▼
┌─────────────┐
│ Auth Check  │
│ (API Key)   │
└─────────────┘
    │
    ▼
┌─────────────┐
│ Role Check  │
│ (RBAC)      │
└─────────────┘
    │
    ▼
┌─────────────┐
│ Business    │
│ Logic       │
└─────────────┘
    │
    ▼
┌─────────────┐
│ Response    │
│ Formatting  │
└─────────────┘
    │
    ▼
Response (APIResponse)
```

## Plugin Architecture

ChainReaction supports a comprehensive plugin system for extensibility.

### Plugin Types

| Type            | Base Class          | Purpose                    |
| --------------- | ------------------- | -------------------------- |
| **Source**      | `SourcePlugin`      | Custom data sources        |
| **Analysis**    | `AnalysisPlugin`    | Custom DSPy modules        |
| **Integration** | `IntegrationPlugin` | Bidirectional integrations |
| **Risk Type**   | `CustomRiskType`    | Custom risk definitions    |

### Plugin Lifecycle

```
┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌────────┐
│ UNLOADED │───▶│  LOADED  │───▶│ INITIALIZED │───▶│ ACTIVE │
└──────────┘    └──────────┘    └─────────────┘    └────────┘
     ▲                                                  │
     │                                                  │
     │           ┌──────────┐                          │
     └───────────│ DISABLED │◀─────────────────────────┘
                 └──────────┘
```

### Plugin Manager

```python
from src.analysis.plugins import PluginManager, SourcePlugin

manager = PluginManager()

# Register a plugin
manager.register_plugin(MyCustomSourcePlugin())

# Collect data from all active source plugins
data = manager.collect_source_data()

# Run analysis plugins
results = manager.run_analysis_plugins(input_data)
```

### Risk Type Registry

```python
from src.analysis.plugins import RiskTypeRegistry, CustomRiskType

registry = RiskTypeRegistry()

# Register custom risk type
registry.register(CustomRiskType(
    type_id="cyber_attack",
    name="Cyber Attack",
    description="Cyber security incidents",
    keywords=["ransomware", "breach", "hack"],
    severity_default="Critical"
))

# Match text against risk types
matches = registry.match_text("Ransomware attack disrupts factory operations")
```

## Performance Optimization

### Caching Strategy

```
┌─────────────────────────────────────────────────┐
│                 Query Cache                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │     LRU     │  │     TTL     │  │   LFU   │ │
│  │   (Default) │  │   (Time)    │  │ (Freq)  │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│             Performance Thresholds               │
│  • Viewport culling: 1000+ nodes                │
│  • WebGL rendering: 50000+ nodes                │
│  • Disable animations: 100000+ nodes            │
│  • Max labels: scales with node count           │
└─────────────────────────────────────────────────┘
```

### Batch Processing

- Target throughput: 100+ events/minute
- Configurable batch sizes
- Async processing support
- Throughput metrics tracking

### Resource Monitoring

- CPU, memory, network, disk monitoring
- Configurable limits with alerts
- Usage history tracking
- Violation callbacks

## Accessibility

ChainReaction implements WCAG 2.1 AA compliance:

### Color Contrast

- All color combinations audited
- Minimum 4.5:1 ratio for normal text
- Minimum 3:1 ratio for large text
- Automatic color suggestion for failing combinations

### Keyboard Navigation

- Full keyboard support for all interactions
- Tab navigation through UI elements
- Keyboard shortcuts for common actions:
  - `Ctrl++` / `Ctrl+-`: Zoom in/out
  - `Arrow keys`: Pan graph
  - `1-4`: Toggle severity filters
  - `R`: Reset view
  - `?`: Show help

### Data Dictionary

- All exports include field documentation
- Markdown and JSON Schema generation
- Field types, formats, and examples documented

## Scaling Considerations

### Horizontal Scaling
- Scout Agent: Multiple instances with source partitioning
- API: Load-balanced with stateless design
- GraphRAG: Neo4j clustering for read replicas

### Vertical Scaling
- Batch processing for high-volume events
- Caching layer for frequently accessed paths
- Async processing for non-critical operations

### Performance Optimizations
- Connection pooling for database access
- Result caching with TTL
- Lazy loading for graph traversals
- Viewport culling for large graphs

## Deployment Architecture

ChainReaction is fully containerized using Docker:

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose Stack                   │
│                                                             │
│  ┌────────────────┐      ┌────────────────┐                 │
│  │   Frontend     │      │    Backend     │                 │
│  │   (Next.js)    │◀────▶│   (FastAPI)    │                 │
│  │   Port 3000    │      │   Port 8000    │                 │
│  └────────────────┘      └───────┬────────┘                 │
│                                  │                           │
│                                  ▼                           │
│                          ┌────────────────┐                 │
│                          │     Neo4j      │                 │
│                          │   (Graph DB)   │                 │
│                          │   Port 7687    │                 │
│                          └────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Deployment Features:**
- **Multi-stage Builds**: Optimizes image size and security
- **Non-root Users**: Containers run as restricted users
- **Health Checks**: Integrated Docker health checks
- **Persistent Volumes**: Data durability for Neo4j
- **Simplified Orchestration**: Makefile for common commands
