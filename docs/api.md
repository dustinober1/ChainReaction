# API Documentation

Complete reference for the ChainReaction REST API.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Response Format](#response-format)
- [API v1 Endpoints](#api-v1-endpoints)
  - [Health](#health)
  - [Risks](#risks)
  - [Supply Chain](#supply-chain)
  - [Alerts](#alerts)
  - [Webhooks](#webhooks)
- [API v2 Endpoints](#api-v2-endpoints)
  - [Resilience Metrics](#resilience-metrics)
  - [Advanced Search](#advanced-search)
  - [Mitigations](#mitigations)
  - [Alert Rules](#alert-rules)
  - [Predictive Analytics](#predictive-analytics)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The ChainReaction API provides programmatic access to supply chain risk data, alerts, and management functionality.

**Base URL:** `http://localhost:8000`

**API Versions:**
- **v1**: Core functionality - `http://localhost:8000/api/v1`
- **v2**: Enhanced features - `http://localhost:8000/api/v2`

## Authentication

All API endpoints (except `/health` and `/`) require API key authentication.

### API Key Header

Include the API key in the `X-API-Key` header:

```http
GET /api/v1/risks HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key-here
```

### Roles

API keys are assigned roles that control access:

| Role     | Permissions                               |
| -------- | ----------------------------------------- |
| `reader` | Read-only access to all endpoints         |
| `writer` | Read + create/update operations           |
| `admin`  | Full access including delete and webhooks |

### Error Responses

```json
// Missing API key
{
  "detail": "Missing API key. Include X-API-Key header."
}

// Invalid API key
{
  "detail": "Invalid API key"
}

// Insufficient permissions
{
  "detail": "Insufficient permissions. Required role: admin"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default limit:** 100 requests per minute per API key
- Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705320000
```

When rate limited:

```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

## Response Format

All responses follow a standardized format:

### Success Response

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

### List Response (with pagination)

```json
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 150,
      "total_pages": 8
    }
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": null
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

---

## API v1 Endpoints

### Health

Health check endpoints that don't require authentication.

#### GET /health

Check system health status.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET /

Get API information.

**Response:**

```json
{
  "success": true,
  "data": {
    "name": "ChainReaction API",
    "version": "1.0.0",
    "description": "Supply Chain Risk Monitoring API"
  }
}
```

---

### Risks

Manage supply chain risk events.

#### GET /api/v1/risks

List all risk events.

**Query Parameters:**

| Parameter    | Type    | Description                                      |
| ------------ | ------- | ------------------------------------------------ |
| `severity`   | string  | Filter by severity (Low, Medium, High, Critical) |
| `event_type` | string  | Filter by event type                             |
| `location`   | string  | Filter by location                               |
| `page`       | integer | Page number (default: 1)                         |
| `page_size`  | integer | Items per page (default: 20, max: 100)           |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/risks?severity=High&page=1" \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "RISK-0001",
      "event_type": "Weather",
      "description": "Typhoon affecting Taiwan semiconductor production",
      "location": "Taiwan",
      "severity": "High",
      "confidence": 0.85,
      "detected_at": "2024-01-15T08:00:00Z",
      "source_url": "https://news.example.com/article",
      "affected_entities": ["TSMC", "UMC"]
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 1,
      "total_pages": 1
    }
  }
}
```

#### POST /api/v1/risks

Create a new risk event.

**Required Role:** `writer` or `admin`

**Request Body:**

```json
{
  "event_type": "Weather",
  "location": "Taiwan",
  "affected_entities": ["TSMC"],
  "severity": "High",
  "confidence": 0.9,
  "source_url": "https://news.example.com",
  "description": "Typhoon threatening production"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "RISK-0002",
    "event_type": "Weather",
    "location": "Taiwan",
    "severity": "High",
    "confidence": 0.9,
    "detected_at": "2024-01-15T10:30:00Z",
    "source_url": "https://news.example.com",
    "affected_entities": ["TSMC"],
    "description": "Typhoon threatening production"
  }
}
```

#### GET /api/v1/risks/{risk_id}

Get a specific risk event.

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "RISK-0001",
    "event_type": "Weather",
    "description": "Typhoon affecting Taiwan semiconductor production",
    "location": "Taiwan",
    "severity": "High",
    "confidence": 0.85,
    "detected_at": "2024-01-15T08:00:00Z",
    "source_url": "https://news.example.com",
    "affected_entities": ["TSMC", "UMC"]
  }
}
```

#### DELETE /api/v1/risks/{risk_id}

Delete a risk event.

**Required Role:** `admin`

**Response (204 No Content)**

#### GET /api/v1/risks/query/product/{product_id}

Query risks affecting a specific product.

**Response:**

```json
{
  "success": true,
  "data": {
    "product_id": "PROD-0001",
    "product_name": "Smartphone Pro",
    "risk_count": 2,
    "aggregate_risk_score": 0.75,
    "risks": [
      {
        "risk_id": "RISK-0001",
        "severity": "High",
        "impact_path": ["SUP-001", "COMP-003", "PROD-0001"]
      }
    ]
  }
}
```

---

### Supply Chain

Access supply chain entity data.

#### GET /api/v1/supply-chain/suppliers

List all suppliers.

**Query Parameters:**

| Parameter  | Type    | Description                |
| ---------- | ------- | -------------------------- |
| `location` | string  | Filter by location         |
| `tier`     | integer | Filter by tier level (1-4) |

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "SUP-001",
      "name": "Taiwan Semiconductor Co.",
      "location": "Taiwan",
      "tier": 1,
      "risk_score": 0.35
    }
  ]
}
```

#### GET /api/v1/supply-chain/suppliers/{supplier_id}

Get a specific supplier.

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "SUP-001",
    "name": "Taiwan Semiconductor Co.",
    "location": "Taiwan",
    "tier": 1,
    "risk_score": 0.35,
    "components_supplied": ["COMP-001", "COMP-002"],
    "backup_suppliers": ["SUP-005"]
  }
}
```

#### GET /api/v1/supply-chain/components

List all components.

**Query Parameters:**

| Parameter  | Type    | Description             |
| ---------- | ------- | ----------------------- |
| `category` | string  | Filter by category      |
| `critical` | boolean | Filter by critical flag |

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "COMP-001",
      "name": "CPU Chip A7",
      "category": "Semiconductors",
      "critical": true,
      "lead_time_days": 45
    }
  ]
}
```

#### GET /api/v1/supply-chain/products

List all products.

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "PROD-001",
      "name": "Smartphone Pro",
      "product_line": "Mobile",
      "revenue_impact": 2500000.00
    }
  ]
}
```

#### GET /api/v1/supply-chain/stats

Get supply chain statistics.

**Response:**

```json
{
  "success": true,
  "data": {
    "total_suppliers": 200,
    "total_components": 300,
    "total_products": 100,
    "active_risks": 10,
    "at_risk_products": 40,
    "average_risk_score": 0.42
  }
}
```

---

### Alerts

Manage risk alerts.

#### GET /api/v1/alerts

List all alerts.

**Query Parameters:**

| Parameter      | Type    | Description                     |
| -------------- | ------- | ------------------------------- |
| `acknowledged` | boolean | Filter by acknowledgment status |
| `severity`     | string  | Filter by severity              |

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "ALERT-0001",
      "risk_event_id": "RISK-0001",
      "product_ids": ["PROD-001", "PROD-002"],
      "severity": "High",
      "title": "High Alert: Weather Event",
      "message": "Typhoon threatening Taiwan production",
      "created_at": "2024-01-15T08:15:00Z",
      "acknowledged": false
    }
  ]
}
```

#### GET /api/v1/alerts/{alert_id}

Get a specific alert.

#### POST /api/v1/alerts/{alert_id}/acknowledge

Acknowledge an alert.

**Request Body:**

```json
{
  "acknowledged_by": "user@example.com",
  "notes": "Activated backup supplier"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "ALERT-0001",
    "acknowledged": true,
    "acknowledged_at": "2024-01-15T10:30:00Z",
    "acknowledged_by": "user@example.com"
  }
}
```

---

### Webhooks

Manage webhook subscriptions.

#### GET /api/v1/webhooks

List registered webhooks.

**Required Role:** `admin`

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "WHK-0001",
      "url": "https://example.com/webhook",
      "events": ["alert.created", "risk.detected"],
      "active": true,
      "created_at": "2024-01-10T00:00:00Z"
    }
  ]
}
```

#### POST /api/v1/webhooks

Register a new webhook.

**Required Role:** `admin`

**Request Body:**

```json
{
  "url": "https://example.com/webhook",
  "events": ["alert.created"],
  "active": true
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "WHK-0002",
    "url": "https://example.com/webhook",
    "events": ["alert.created"],
    "secret": "whsec_xxxxxxxxxxxx",
    "active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### PATCH /api/v1/webhooks/{webhook_id}

Update a webhook.

**Request Body:**

```json
{
  "active": false
}
```

#### DELETE /api/v1/webhooks/{webhook_id}

Delete a webhook.

**Required Role:** `admin`

#### POST /api/v1/webhooks/{webhook_id}/test

Send a test webhook.

**Response:**

```json
{
  "success": true,
  "data": {
    "delivered": true,
    "response_status": 200,
    "response_time_ms": 250
  }
}
```

#### GET /api/v1/webhooks/stats/overview

Get webhook delivery statistics.

**Response:**

```json
{
  "success": true,
  "data": {
    "total_webhooks": 5,
    "active_webhooks": 4,
    "total_deliveries": 1250,
    "successful_deliveries": 1230,
    "failed_deliveries": 20,
    "success_rate": 0.984
  }
}
```

---

## API v2 Endpoints

API v2 provides enhanced functionality including resilience metrics, advanced search, and predictive analytics.

### Resilience Metrics

#### GET /api/v2/resilience/{entity_id}

Get resilience score for a specific entity.

**Response:**

```json
{
  "success": true,
  "data": {
    "entity_id": "SUP-001",
    "entity_type": "supplier",
    "overall_score": 0.78,
    "components": {
      "supplier_diversity": 0.82,
      "geographic_distribution": 0.65,
      "backup_availability": 0.85,
      "lead_time_buffer": 0.72,
      "financial_stability": 0.90
    },
    "calculated_at": "2024-01-15T10:30:00Z",
    "trend": "improving"
  }
}
```

#### GET /api/v2/resilience/trend

Get resilience trend analysis.

**Query Parameters:**

| Parameter   | Type   | Description                    |
| ----------- | ------ | ------------------------------ |
| `entity_id` | string | Entity ID (optional)           |
| `period`    | string | Time period (7d, 30d, 90d, 1y) |

**Response:**

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "data_points": [
      {
        "date": "2024-01-01",
        "score": 0.72
      },
      {
        "date": "2024-01-15",
        "score": 0.78
      }
    ],
    "average": 0.75,
    "trend_direction": "up",
    "change_percent": 8.3
  }
}
```

---

### Advanced Search

#### POST /api/v2/search/advanced

Perform an advanced full-text search.

**Request Body:**

```json
{
  "query": "semiconductor shortage",
  "filters": {
    "severity": ["High", "Critical"],
    "location": ["Taiwan", "China"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-31"
    }
  },
  "sort": {
    "field": "severity_score",
    "direction": "desc"
  },
  "limit": 50,
  "offset": 0
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "RISK-0001",
        "event_type": "Supply Shortage",
        "severity": "Critical",
        "location": "Taiwan",
        "relevance_score": 0.95,
        "highlighted_content": "Major <em>semiconductor shortage</em> affecting..."
      }
    ],
    "total_count": 15,
    "facets": {
      "severity": {
        "Critical": 5,
        "High": 10
      },
      "location": {
        "Taiwan": 8,
        "China": 7
      }
    }
  }
}
```

#### GET /api/v2/search/saved

List saved searches.

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "SEARCH-001",
      "name": "Taiwan Semiconductor Risks",
      "query": "semiconductor taiwan",
      "filters": { ... },
      "created_at": "2024-01-10T00:00:00Z"
    }
  ]
}
```

#### POST /api/v2/search/saved

Save a search.

**Request Body:**

```json
{
  "name": "Critical Taiwan Risks",
  "query": "taiwan critical",
  "filters": {
    "severity": ["Critical"]
  }
}
```

---

### Mitigations

#### GET /api/v2/mitigations

List all mitigation plans.

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "MIT-0001",
      "risk_event_id": "RISK-0001",
      "title": "Activate Backup Supplier",
      "status": "in_progress",
      "priority": "high",
      "assignee": "procurement@company.com",
      "created_at": "2024-01-15T09:00:00Z"
    }
  ]
}
```

#### POST /api/v2/mitigations

Create a mitigation plan.

**Request Body:**

```json
{
  "risk_event_id": "RISK-0001",
  "title": "Activate backup supplier",
  "description": "Contact and activate SUP-005 as backup",
  "priority": "high",
  "assignee": "procurement@company.com",
  "due_date": "2024-01-20"
}
```

#### GET /api/v2/mitigations/{id}

Get mitigation details.

#### PUT /api/v2/mitigations/{id}

Update mitigation status.

**Request Body:**

```json
{
  "status": "completed",
  "resolution_notes": "SUP-005 activated successfully"
}
```

---

### Alert Rules

#### GET /api/v2/alerts/rules

List alert rules.

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": "RULE-001",
      "name": "Critical Risk Alert",
      "conditions": {
        "severity": "Critical",
        "confidence_min": 0.8
      },
      "channels": ["email", "slack"],
      "recipients": ["team@company.com"],
      "enabled": true
    }
  ]
}
```

#### POST /api/v2/alerts/rules

Create an alert rule.

**Request Body:**

```json
{
  "name": "High Severity Taiwan Alert",
  "conditions": {
    "severity": ["High", "Critical"],
    "location": "Taiwan"
  },
  "channels": ["email", "slack", "webhook"],
  "recipients": ["alerts@company.com"],
  "webhook_url": "https://slack.company.com/webhook"
}
```

#### DELETE /api/v2/alerts/rules/{id}

Delete an alert rule.

---

### Predictive Analytics

#### GET /api/v2/analytics/predictions

Get risk predictions.

**Query Parameters:**

| Parameter | Type   | Description                  |
| --------- | ------ | ---------------------------- |
| `horizon` | string | Prediction horizon (7d, 30d) |
| `entity`  | string | Entity ID to predict for     |

**Response:**

```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "entity_id": "SUP-001",
        "entity_name": "Taiwan Semiconductor Co.",
        "predicted_risk_score": 0.72,
        "confidence": 0.85,
        "risk_factors": [
          {
            "factor": "Weather patterns",
            "contribution": 0.3
          },
          {
            "factor": "Geopolitical tension",
            "contribution": 0.25
          }
        ],
        "horizon": "30d"
      }
    ],
    "generated_at": "2024-01-15T10:30:00Z"
  }
}
```

#### GET /api/v2/analytics/trends

Get trend analysis.

**Response:**

```json
{
  "success": true,
  "data": {
    "overall_risk_trend": "increasing",
    "risk_by_category": {
      "Natural Disaster": {
        "current": 12,
        "previous": 8,
        "change": 50
      },
      "Geopolitical": {
        "current": 5,
        "previous": 7,
        "change": -28.5
      }
    },
    "top_emerging_risks": [
      {
        "description": "Semiconductor supply constraints",
        "probability": 0.75,
        "potential_impact": "High"
      }
    ]
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code  | Description                             |
| ----- | --------------------------------------- |
| `200` | Success                                 |
| `201` | Created                                 |
| `204` | No Content (successful delete)          |
| `400` | Bad Request (validation error)          |
| `401` | Unauthorized (missing/invalid API key)  |
| `403` | Forbidden (insufficient permissions)    |
| `404` | Not Found                               |
| `422` | Unprocessable Entity (validation error) |
| `429` | Too Many Requests (rate limited)        |
| `500` | Internal Server Error                   |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {
      "severity": ["Must be one of: Low, Medium, High, Critical"]
    }
  }
}
```

---

## Examples

### Python (requests)

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000/api/v1"

headers = {"X-API-Key": API_KEY}

# List risks
response = requests.get(f"{BASE_URL}/risks", headers=headers)
risks = response.json()["data"]

# Create a risk
new_risk = {
    "event_type": "Strike",
    "location": "Germany",
    "severity": "Medium",
    "confidence": 0.8,
    "affected_entities": ["Factory A"],
    "source_url": "https://news.example.com",
    "description": "Worker strike at manufacturing plant"
}
response = requests.post(f"{BASE_URL}/risks", json=new_risk, headers=headers)
created = response.json()["data"]
print(f"Created risk: {created['id']}")

# Advanced search (v2)
search_query = {
    "query": "semiconductor shortage",
    "filters": {"severity": ["Critical", "High"]},
    "limit": 10
}
response = requests.post(
    "http://localhost:8000/api/v2/search/advanced",
    json=search_query,
    headers=headers
)
results = response.json()["data"]["results"]
```

### JavaScript (fetch)

```javascript
const API_KEY = 'your-api-key';
const BASE_URL = 'http://localhost:8000/api/v1';

async function listRisks() {
  const response = await fetch(`${BASE_URL}/risks`, {
    headers: { 'X-API-Key': API_KEY }
  });
  const { data } = await response.json();
  return data;
}

async function acknowledgeAlert(alertId) {
  const response = await fetch(`${BASE_URL}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      acknowledged_by: 'user@example.com'
    })
  });
  return response.json();
}

async function advancedSearch(query, filters) {
  const response = await fetch('http://localhost:8000/api/v2/search/advanced', {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, filters })
  });
  return response.json();
}
```

### cURL

```bash
# List risks
curl -X GET "http://localhost:8000/api/v1/risks" \
  -H "X-API-Key: your-api-key"

# Create risk
curl -X POST "http://localhost:8000/api/v1/risks" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "Weather",
    "location": "Taiwan",
    "severity": "High",
    "confidence": 0.9,
    "affected_entities": ["TSMC"],
    "source_url": "https://example.com",
    "description": "Typhoon warning"
  }'

# Advanced search (v2)
curl -X POST "http://localhost:8000/api/v2/search/advanced" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "semiconductor shortage",
    "filters": {"severity": ["Critical", "High"]},
    "limit": 10
  }'

# Get resilience score (v2)
curl -X GET "http://localhost:8000/api/v2/resilience/SUP-001" \
  -H "X-API-Key: your-api-key"

# Register webhook
curl -X POST "http://localhost:8000/api/v1/webhooks" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://myapp.com/webhook",
    "events": ["alert.created"]
  }'
```
