# Architecture Guide

This document provides a detailed overview of ChainReaction's architecture, design decisions, and component interactions.

## Table of Contents

- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Design Principles](#design-principles)
- [Technology Stack](#technology-stack)
- [Component Deep Dives](#component-deep-dives)

## System Overview

ChainReaction is designed as a modular, event-driven system that continuously monitors external news sources, analyzes potential supply chain risks, traces impact through a graph database, and delivers actionable alerts to stakeholders.

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              External Sources                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │  News APIs   │  │  RSS Feeds   │  │  Webhooks    │                      │
│  │   (Tavily)   │  │              │  │   (Inbound)  │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
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
│          REST API              │  │              Webhooks                   │
│  • Authentication              │  │  • Event-based delivery                │
│  • Rate limiting               │  │  • HMAC signature verification         │
│  • Standardized responses      │  │  • Retry with exponential backoff      │
└────────────────────────────────┘  └────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         Frontend Dashboard                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │   Graph View     │  │   Chat Interface │  │   Alerts Panel   │         │
│  │   (Force Graph)  │  │   (AI Queries)   │  │   (Real-time)    │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
└────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Scout Agent (`src/scout/`)

The Scout Agent is responsible for autonomous data collection from external sources.

**Key Features:**
- Configurable monitoring intervals
- Multi-source support (Tavily, NewsAPI)
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

**Design Pattern:** Component-based architecture

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
   Delivers: webhooks, API, dashboard
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
Property-based testing with Hypothesis ensures correctness invariants.

### 5. Configuration-Driven
All thresholds, intervals, and weights are configurable.

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
│   └── CustomSource (extensible)
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

## Deployment Architecture

ChainReaction is fully containerized using Docker, allowing for consistent environments from development to production.

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
- **Multi-stage Builds**: Optimizes image size and security by separating build and runtime environments.
- **Non-root Users**: Containers run as restricted users for enhanced security.
- **Health Checks**: Integrated Docker health checks for automated service recovery.
- **Persistent Volumes**: Data durability for Neo4j and local file storage.
- **Simplified Orchestration**: `Makefile` providing intuitive commands for complex Docker lifecycle management.
