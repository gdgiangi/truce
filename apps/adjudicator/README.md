# Truce Adjudicator

FastAPI-based service for claim evaluation, evidence collection, and consensus building.

## Features

- **Claims Management**: Create and evaluate contentious claims
- **Evidence Integration**: Automatic StatCan data fetching via REST API
- **Multi-Model Panel**: Independent evaluations from GPT-5, Claude-4 Sonnet, etc.
- **Consensus Building**: Pol.is-inspired voting and clustering
- **Reproducibility**: Complete replay bundles for transparency
- **RDF/JSON-LD**: Semantic web integration with custom vocabulary

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set environment variables
cp ../../env.example .env
# Edit .env with your API keys

# Run development server
uvicorn truce_adjudicator.main:app --reload --host 0.0.0.0 --port 8000

# Seed demo data
python -m truce_adjudicator.scripts.seed
```

## API Endpoints

### Claims
- `POST /claims` - Create new claim
- `GET /claims/{id}` - Get claim with evaluations
- `POST /claims/{id}/evidence:statcan` - Fetch Statistics Canada data
- `POST /claims/{id}/panel/run` - Run multi-model evaluation

### Consensus
- `POST /consensus/{topic}/statements` - Create consensus statement
- `POST /consensus/{topic}/votes` - Vote on statement  
- `GET /consensus/{topic}/summary` - Get consensus summary with clusters

### Reproducibility
- `GET /replay/{claim_id}.jsonl` - Download replay bundle

## Architecture

```
truce_adjudicator/
├── main.py              # FastAPI app
├── models.py            # Pydantic data models
├── statcan/            
│   └── fetch_csi.py     # Statistics Canada integration
├── panel/
│   └── run_panel.py     # Multi-model evaluation
├── consensus/
│   ├── vote.py          # Voting logic
│   └── cluster.py       # Opinion clustering  
├── rdf/
│   ├── vocab.ttl        # RDF vocabulary
│   └── context.jsonld   # JSON-LD context
├── replay/
│   └── bundle.py        # Reproducibility bundles
└── scripts/
    └── seed.py          # Demo data seeding
```

## Configuration

### Required Environment Variables

```bash
# AI Model APIs (at least one required)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Statistics Canada (optional, has fallback)
STATCAN_WDS_BASE=https://www150.statcan.gc.ca/t1/wds/rest
```

### Optional Variables

```bash
# W3C Verifiable Credentials
VC_ISSUER_DID=did:key:...
VC_PRIVATE_KEY_BASE58=...

# Apache Jena Fuseki RDF store
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=truce
```

## Data Models

### Core Types
- **Claim**: Contentious statement to evaluate
- **Evidence**: Supporting/refuting information with provenance
- **ModelAssessment**: AI model evaluation with verdict and confidence
- **ConsensusStatement**: Statement for consensus building
- **Vote**: User vote on consensus statement

### Verdicts
- `supports`: Evidence clearly supports the claim
- `refutes`: Evidence clearly contradicts the claim
- `mixed`: Evidence both supports and contradicts
- `uncertain`: Evidence insufficient or unclear

## Statistics Canada Integration

### Data Sources
- Table 35-10-0026-01: Crime Severity Index
- Table 35-10-0177-01: Incident-based crime statistics

### Features
- REST API integration via WDS
- Automatic CSV caching
- Structured evidence creation
- Provenance tracking
- Fallback to mock data if API unavailable

### Example Usage
```python
from truce_adjudicator.statcan.fetch_csi import fetch_crime_severity_data

evidence_list = await fetch_crime_severity_data()
# Returns list of Evidence objects with StatCan data
```

## Multi-Model Panel

### Supported Models
- OpenAI: GPT-5, GPT-3.5-turbo
- Anthropic: Claude-3 Sonnet, Claude-3 Haiku

### Process
1. Prepare identical evidence context for all models
2. Send structured evaluation prompt
3. Require JSON response with verdict, confidence, citations
4. Store complete prompt/response for reproducibility
5. Aggregate results for consensus scoring

### Example Usage
```python
from truce_adjudicator.panel.run_panel import run_panel_evaluation

assessments = await run_panel_evaluation(claim, ["gpt-5", "claude-3"])
# Returns list of ModelAssessment objects
```

## Consensus System

### Voting
- Three options: Agree / Disagree / Pass
- Anonymous sessions (no login required)
- Duplicate vote prevention per session
- Real-time aggregation

### Clustering
- K-means clustering on vote vectors
- Identifies opinion groups automatically
- Calculates internal agreement rates
- Surfaces bridge statements across clusters

### Example Usage
```python
from truce_adjudicator.consensus.vote import aggregate_votes, cluster_users_by_votes

aggregate_votes(statements, votes)
clusters = cluster_users_by_votes(statements, votes)
```

## Reproducibility

### Replay Bundles
Every claim evaluation creates a downloadable bundle containing:
- Original inputs (claim text, evidence URLs)
- Complete model prompts and parameters
- Full model responses and timestamps
- Processing logs and error conditions
- Final JSON-LD graph representation

### JSONL Format
```jsonl
{"type": "bundle_metadata", "id": "...", "created_at": "..."}
{"type": "inputs", "data": {...}}
{"type": "model_prompt", "sequence": 0, "data": {...}}
{"type": "model_response", "sequence": 0, "data": {...}}
{"type": "final_graph", "data": {...}}
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_claim_flow.py -v

# Run with coverage
pip install pytest-cov
python -m pytest --cov=truce_adjudicator tests/
```

## Development

### Code Style
```bash
# Format code
black .
isort .

# Type checking
mypy truce_adjudicator/
```

### Adding New Data Sources
1. Create module in appropriate subdirectory
2. Implement async function returning `List[Evidence]`
3. Add API endpoint in `main.py`
4. Update documentation and tests

### Adding New Models
1. Add API client setup in `panel/run_panel.py`
2. Implement `_evaluate_with_[provider]` function
3. Add model name to default models list
4. Test with mock responses

## Deployment

### Docker
```bash
docker build -t truce-adjudicator .
docker run -p 8000:8000 -e OPENAI_API_KEY=... truce-adjudicator
```

### Environment
- Python 3.11+
- FastAPI + Uvicorn
- Async HTTP clients
- Scientific Python stack (pandas, numpy, scikit-learn)

## Limitations

- Demo system - not production ready
- Limited to English language
- Simple clustering algorithm
- No persistent database (in-memory storage)
- Rate limiting not implemented
- Authentication not required

## Contributing

1. Install development dependencies: `pip install -e .[dev]`
2. Run tests: `python -m pytest`
3. Follow code style: `black . && isort .`
4. Add tests for new features
5. Update documentation

## License

MIT License - see [LICENSE](../../LICENSE) for details.
