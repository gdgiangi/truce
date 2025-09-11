# API Reference

Base URL: `http://localhost:8000`

## Authentication

No authentication required for MVP demo. All endpoints are publicly accessible.

## Claims API

### Create Claim

```http
POST /claims
Content-Type: application/json

{
  "text": "Violent crime in Canada is rising.",
  "topic": "canada-crime",
  "entities": ["Q16"],
  "seed_sources": []
}
```

**Response:**
```json
{
  "claim": {
    "id": "uuid",
    "text": "Violent crime in Canada is rising.",
    "topic": "canada-crime",
    "entities": ["Q16"],
    "evidence": [],
    "model_assessments": [],
    "human_reviews": [],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "consensus_score": null,
  "provenance_verified": false,
  "replay_bundle_url": null
}
```

### Get Claim

```http
GET /claims/{claim_id}
```

**Response:** Same as create claim response, but populated with evidence and assessments.

### Add StatCan Evidence

```http
POST /claims/{claim_id}/evidence:statcan
Content-Type: application/json

{
  "source_type": "statcan",
  "params": {}
}
```

**Response:**
```json
{
  "status": "success",
  "evidence_count": 3
}
```

### Run Model Panel

```http
POST /claims/{claim_id}/panel/run
Content-Type: application/json

{
  "models": ["gpt-5", "claude-3"],
  "temperature": 0.1
}
```

**Response:**
```json
{
  "status": "success",
  "assessments": [
    {
      "id": "uuid",
      "model_name": "gpt-5",
      "verdict": "mixed",
      "confidence": 0.75,
      "citations": ["evidence-uuid"],
      "rationale": "The claim requires temporal context...",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "consensus_score": 0.5
}
```

## Consensus API

### Create Statement

```http
POST /consensus/{topic}/statements
Content-Type: application/json

{
  "text": "Crime statistics should be interpreted with caution due to under-reporting",
  "evidence_links": []
}
```

**Response:**
```json
{
  "id": "uuid",
  "text": "Crime statistics should be interpreted with caution due to under-reporting",
  "topic": "canada-crime",
  "agree_count": 0,
  "disagree_count": 0,
  "pass_count": 0,
  "agree_rate": 0.0,
  "cluster_id": null,
  "evidence_links": [],
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Vote on Statement

```http
POST /consensus/{topic}/votes
Content-Type: application/json

{
  "statement_id": "uuid",
  "vote": "agree",
  "session_id": "session123"
}
```

**Response:**
```json
{
  "status": "success",
  "vote": {
    "id": "uuid",
    "statement_id": "uuid",
    "user_id": null,
    "session_id": "session123",
    "vote": "agree",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Get Consensus Summary

```http
GET /consensus/{topic}/summary
```

**Response:**
```json
{
  "topic": "canada-crime",
  "statement_count": 10,
  "vote_count": 45,
  "overall_consensus": [
    {
      "id": "uuid",
      "text": "Crime data should be publicly accessible and transparent",
      "agree_count": 12,
      "disagree_count": 2,
      "agree_rate": 0.86,
      "cluster_id": null,
      "evidence_links": [],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "divisive": [
    {
      "id": "uuid",
      "text": "Police budgets should be increased to reduce crime",
      "agree_count": 5,
      "disagree_count": 7,
      "agree_rate": 0.42,
      "cluster_id": 1,
      "evidence_links": [],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "clusters": [
    {
      "id": 1,
      "statements": ["uuid1", "uuid2"],
      "user_count": 8,
      "avg_agreement": 0.72,
      "description": "Cluster 1: 8 users with 72% avg agreement"
    }
  ],
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Replay Bundles

### Download Replay Bundle

```http
GET /replay/{claim_id}.jsonl
```

**Response:** JSONL file containing:
- Bundle metadata
- Input data (claim, evidence)
- Model prompts and responses
- Final JSON-LD graph

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error description",
  "detail": "Additional details if available"
}
```

Common status codes:
- `404` - Resource not found
- `422` - Validation error
- `500` - Internal server error

## Rate Limits

No rate limits in MVP. In production:
- 100 requests/minute per IP
- 10 votes/minute per session
- Model panel limited to 5 runs/hour

## Next.js Proxy Routes

The web app proxies some requests:

- `GET /api/claims/{slug}` → `GET /claims/{slug}`
- `GET /api/consensus/{topic}` → `GET /consensus/{topic}/summary`

Direct API access is also available at port 8000.
