# Data Models Reference

Complete reference for all data models used in ChainReaction.

## Table of Contents

- [Overview](#overview)
- [Enums](#enums)
- [Supply Chain Entities](#supply-chain-entities)
- [Risk Models](#risk-models)
- [Impact Models](#impact-models)
- [Alert Models](#alert-models)
- [Relationship Models](#relationship-models)
- [API Models](#api-models)

## Overview

ChainReaction uses Pydantic 2.x models for data validation and serialization. All models are defined in `src/models.py`.

### Base Classes

```python
class BaseNode(BaseModel):
    """Base class for all graph nodes."""
    
    id: str                    # Unique identifier
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
```

```python
class BaseRelationship(BaseModel):
    """Base class for all graph relationships."""
    
    source_id: str             # Source node ID
    target_id: str             # Target node ID
    relationship_type: str     # Type of relationship
    properties: dict           # Additional properties
```

---

## Enums

### EventType

Types of supply chain disruption events.

```python
class EventType(str, Enum):
    STRIKE = "Strike"
    WEATHER = "Weather"
    BANKRUPTCY = "Bankruptcy"
    GEOPOLITICAL = "Geopolitical"
    FIRE = "Fire"
    PANDEMIC = "Pandemic"
    CYBER_ATTACK = "CyberAttack"
    TRANSPORT = "Transport"
    OTHER = "Other"
```

**Usage:**
```python
from src.models import EventType

event_type = EventType.WEATHER
print(event_type.value)  # "Weather"
```

### SeverityLevel

Impact severity levels for risk events.

```python
class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"
```

**Priority mapping:**
| Level    | Score | Response Time |
| -------- | ----- | ------------- |
| Low      | 0.25  | Days          |
| Medium   | 0.50  | Hours         |
| High     | 0.75  | < 4 hours     |
| Critical | 1.00  | Immediate     |

### EntityTier

Supply chain entity tiers.

```python
class EntityTier(str, Enum):
    RAW_MATERIAL = "Raw Material"
    COMPONENT = "Component"
    SUB_ASSEMBLY = "Sub-Assembly"
    FINAL_PRODUCT = "Final Product"
```

### RelationshipType

Types of relationships between supply chain entities.

```python
class RelationshipType(str, Enum):
    SUPPLIES = "SUPPLIES"
    LOCATED_IN = "LOCATED_IN"
    BACKUP_FOR = "BACKUP_FOR"
    PART_OF = "PART_OF"
    REQUIRES = "REQUIRES"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    MANUFACTURES = "MANUFACTURES"
```

---

## Supply Chain Entities

### Supplier

A supplier entity in the supply chain graph.

```python
class Supplier(BaseNode):
    name: str                  # Company name
    location: str              # Primary location
    risk_score: float          # 0.0 - 1.0
    tier: int                  # 1-4
```

**Example:**
```python
supplier = Supplier(
    id="SUP-001",
    name="Taiwan Semiconductor",
    location="Taiwan",
    risk_score=0.35,
    tier=1
)
```

**Validation:**
- `risk_score`: Clamped to 0.0 - 1.0
- `tier`: Must be 1-4

### Component

A component or part in the supply chain.

```python
class Component(BaseNode):
    name: str                  # Component name
    category: str              # Category (e.g., "Semiconductors")
    specifications: dict       # Technical specifications
    lead_time_days: int | None # Standard lead time
    critical: bool             # Whether critical component
```

**Example:**
```python
component = Component(
    id="COMP-001",
    name="CPU Chip A7",
    category="Semiconductors",
    specifications={"frequency": "3.2GHz", "cores": 8},
    lead_time_days=45,
    critical=True
)
```

### Product

A final product in the supply chain.

```python
class Product(BaseNode):
    name: str                  # Product name
    product_line: str          # Product line/family
    revenue_impact: float      # Revenue impact score
    sku: str | None            # Stock keeping unit
    launch_date: datetime | None
```

**Example:**
```python
product = Product(
    id="PROD-001",
    name="Smartphone Pro",
    product_line="Mobile",
    revenue_impact=2500000.00,
    sku="SPP-2024-001"
)
```

### Location

A geographic location in the supply chain.

```python
class Location(BaseNode):
    name: str                  # Location name
    country: str               # Country
    region: str                # Geographic region
    risk_factors: list[str]    # Known risk factors
    latitude: float | None     # -90.0 to 90.0
    longitude: float | None    # -180.0 to 180.0
```

**Example:**
```python
location = Location(
    id="LOC-001",
    name="Hsinchu Science Park",
    country="Taiwan",
    region="East Asia",
    risk_factors=["typhoon", "earthquake"],
    latitude=24.8047,
    longitude=120.9896
)
```

---

## Risk Models

### RawEvent

Raw event data from external sources before processing.

```python
class RawEvent(BaseModel):
    source: str                # Source name (e.g., "tavily")
    url: str                   # Source URL
    title: str                 # Article title
    content: str               # Full content
    published_at: datetime | None
    fetched_at: datetime       # When fetched
```

**Example:**
```python
raw_event = RawEvent(
    source="tavily",
    url="https://news.example.com/article",
    title="Typhoon Warning for Taiwan",
    content="A major typhoon is approaching...",
    published_at=datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc)
)
```

### RiskEvent

A validated supply chain risk event.

```python
class RiskEvent(BaseModel):
    id: str                    # Unique identifier
    event_type: EventType      # Type of event
    description: str           # Event description
    location: str              # Affected location
    severity: SeverityLevel    # Severity level
    confidence: float          # 0.0 - 1.0
    detected_at: datetime      # Detection timestamp
    source_url: str            # Original source URL
    affected_entities: list[str]  # Affected entity IDs/names
```

**Example:**
```python
risk = RiskEvent(
    id="RISK-0001",
    event_type=EventType.WEATHER,
    description="Typhoon threatening semiconductor production",
    location="Taiwan",
    severity=SeverityLevel.HIGH,
    confidence=0.85,
    detected_at=datetime.now(timezone.utc),
    source_url="https://news.example.com/article",
    affected_entities=["TSMC", "UMC"]
)
```

**Validation:**
- `confidence`: Must be 0.0 - 1.0
- `id`: Generated if not provided

---

## Impact Models

### ImpactPath

A path through the supply chain graph showing impact propagation.

```python
class ImpactPath(BaseModel):
    path: list[str]            # Node IDs in order
    length: int                # Number of hops
    risk_score: float          # Combined risk score
    bottleneck: str | None     # Critical node in path
```

**Example:**
```python
impact_path = ImpactPath(
    path=["SUP-001", "COMP-003", "PROD-001"],
    length=2,
    risk_score=0.75,
    bottleneck="COMP-003"
)
```

### ImpactAssessment

Complete impact assessment for a risk event.

```python
class ImpactAssessment(BaseModel):
    risk_event_id: str         # Associated risk event
    affected_suppliers: list[str]
    affected_components: list[str]
    affected_products: list[str]
    impact_paths: list[ImpactPath]
    severity_score: float      # 0 - 10
    redundancy_level: float    # 0.0 - 1.0
    mitigation_options: list[str]
    estimated_resolution_days: int | None
```

**Example:**
```python
assessment = ImpactAssessment(
    risk_event_id="RISK-0001",
    affected_suppliers=["SUP-001"],
    affected_components=["COMP-001", "COMP-002"],
    affected_products=["PROD-001", "PROD-002"],
    impact_paths=[...],
    severity_score=7.5,
    redundancy_level=0.3,
    mitigation_options=["Activate backup supplier", "Increase safety stock"],
    estimated_resolution_days=45
)
```

---

## Alert Models

### Alert

Risk alert generated by the system.

```python
class Alert(BaseModel):
    id: str                    # Unique identifier
    risk_event_id: str         # Associated risk
    product_ids: list[str]     # Affected products
    severity: SeverityLevel    # Alert severity
    title: str                 # Alert title
    message: str               # Alert message
    created_at: datetime       # Creation time
    acknowledged: bool         # Acknowledgment status
    acknowledged_at: datetime | None
    acknowledged_by: str | None
```

**Example:**
```python
alert = Alert(
    id="ALERT-0001",
    risk_event_id="RISK-0001",
    product_ids=["PROD-001", "PROD-002"],
    severity=SeverityLevel.HIGH,
    title="High Alert: Weather Event",
    message="Typhoon threatening Taiwan production",
    acknowledged=False
)
```

### ProcessingError

Error that occurred during event processing.

```python
class ProcessingError(BaseModel):
    error_type: str            # Type of error
    message: str               # Error message
    source: str | None         # Source of error
    occurred_at: datetime      # When it occurred
    recoverable: bool          # Can retry?
    details: dict              # Additional details
```

---

## Relationship Models

### SuppliesRelation

Relationship between a supplier and a component.

```python
class SuppliesRelation(BaseModel):
    supplier_id: str           # Supplier ID
    component_id: str          # Component ID
    is_primary: bool           # Primary supplier?
    lead_time_days: int | None # Lead time for this relationship
```

**Example:**
```python
relation = SuppliesRelation(
    supplier_id="SUP-001",
    component_id="COMP-001",
    is_primary=True,
    lead_time_days=30
)
```

### PartOfRelation

Relationship between a component and a product.

```python
class PartOfRelation(BaseModel):
    component_id: str          # Component ID
    product_id: str            # Product ID
    quantity: int              # Quantity needed per product
```

**Example:**
```python
relation = PartOfRelation(
    component_id="COMP-001",
    product_id="PROD-001",
    quantity=2
)
```

---

## API Models

### APIResponse

Standardized API response format.

```python
class APIResponse(BaseModel):
    success: bool              # Success status
    data: Any | None           # Response data
    error: dict | None         # Error details if failed
    meta: dict                 # Metadata (timestamp, version)
```

**Success response:**
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

**Error response:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  },
  "meta": { ... }
}
```

---

## Model Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Supply Chain Graph                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐                                                       │
│  │ Location │                                                       │
│  │   🌍     │                                                       │
│  └──────────┘                                                       │
│       ▲                                                             │
│       │ LOCATED_IN                                                  │
│       │                                                             │
│  ┌──────────┐     SUPPLIES      ┌───────────┐      PART_OF         │
│  │ Supplier │─────────────────▶│ Component │──────────────────────▶│
│  │    🔵    │                   │     🟣    │                       │
│  │          │◀─────────────────│           │                       │
│  └──────────┘    BACKUP_FOR     └───────────┘                       │
│                                                      ┌─────────┐   │
│                                                      │ Product │   │
│                                                      │   🟢    │   │
│                                                      └─────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         Event Pipeline                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  RawEvent ──▶ RiskEvent ──▶ ImpactAssessment ──▶ Alert             │
│                                                                     │
│  (Fetched)    (Extracted)   (Analyzed)          (Generated)        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Creating a Complete Supply Chain

```python
from src.models import Supplier, Component, Product
from src.data import EntityManager

manager = EntityManager()

# Create supplier
sup = manager.create_supplier(
    name="TSMC",
    location="Taiwan",
    tier=1
)

# Create component
comp = manager.create_component(
    name="A17 Chip",
    category="Semiconductors"
)

# Create product
prod = manager.create_product(
    name="iPhone 15 Pro",
    product_line="Mobile"
)

# Create relationships
manager.add_supplies_relation(sup.entity_id, comp.entity_id)
manager.add_part_of_relation(comp.entity_id, prod.entity_id)
```

### Working with Risk Events

```python
from src.models import RiskEvent, EventType, SeverityLevel
from datetime import datetime, timezone

# Create risk event
risk = RiskEvent(
    id="RISK-0001",
    event_type=EventType.WEATHER,
    description="Typhoon approaching Taiwan",
    location="Taiwan",
    severity=SeverityLevel.HIGH,
    confidence=0.85,
    detected_at=datetime.now(timezone.utc),
    source_url="https://news.example.com",
    affected_entities=["TSMC"]
)

# Serialize to JSON
json_data = risk.model_dump_json()

# Deserialize from JSON
risk_from_json = RiskEvent.model_validate_json(json_data)
```

### Generating Impact Assessments

```python
from src.models import ImpactAssessment, ImpactPath

assessment = ImpactAssessment(
    risk_event_id="RISK-0001",
    affected_suppliers=["SUP-001"],
    affected_components=["COMP-001", "COMP-002"],
    affected_products=["PROD-001"],
    impact_paths=[
        ImpactPath(
            path=["SUP-001", "COMP-001", "PROD-001"],
            length=2,
            risk_score=0.8,
            bottleneck="COMP-001"
        )
    ],
    severity_score=7.5,
    redundancy_level=0.3,
    mitigation_options=["Activate backup suppliers"]
)

print(f"Affected products: {len(assessment.affected_products)}")
print(f"Severity: {assessment.severity_score}/10")
```
