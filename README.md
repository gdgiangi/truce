# Truce

A transparent system for de-escalating dialogue around contentious claims through evidence, multi-model evaluation, and consensus-building.

<img width="1728" height="2544" alt="screencapture-localhost-3000-2025-09-11-09_28_39" src="https://github.com/user-attachments/assets/7f63ffb6-359e-45b2-967e-5699c57d206f" />

## Quick Start

```bash
# Clone and start the demo
git clone https://github.com/your-org/truce
cd truce
cp env.example .env  # Edit with your API keys
make demo
```

Visit:
- **Claim Card**: http://localhost:3000/claim/violent-crime-in-canada-is-rising
- **Consensus Board**: http://localhost:3000/consensus/canada-crime  
- **API**: http://localhost:8000

## What is Truce?

Truce helps people have better conversations about controversial topics by providing:

🔍 **Provenance**: Every claim shows exactly where information came from  
🤖 **Multi-Model Analysis**: Independent AI evaluations with uncertainty  
🤝 **Consensus Finding**: Discover common ground through structured dialogue  

### Demo Topic: "Violent crime in Canada is rising"

Our live demo examines this claim using:
- Statistics Canada official crime data
- Multiple AI model evaluations  
- Pol.is-inspired consensus mechanism
- Downloadable reproducibility bundles

## Architecture

```
truce/
├── apps/
│   ├── web/              # Next.js frontend
│   └── adjudicator/      # FastAPI backend
├── docs/                 # Documentation
└── docker-compose.yml    # Container setup
```

## Features

### Claim Cards
- **Evidence Integration**: Automatic StatCan data fetching
- **Model Panel**: 5, Claude-4 Sonnet independent evaluations
- **Provenance Pills**: W3C Verifiable Credentials
- **Replay Bundles**: Complete reproducibility packages

### Consensus Boards
- **Anonymous Voting**: Session-based, no tracking
- **Smart Clustering**: Find opinion groups automatically  
- **NVC Integration**: Nonviolent communication helpers
- **Bridge Finding**: Surface statements that unite

## Commands

```bash
make build      # Build Docker images
make up         # Start services
make seed       # Load demo data
make panel      # Run model evaluations
make consensus  # Add consensus statements
make publish    # Create replay bundles
make test       # Run tests
make clean      # Clean up
```

## Configuration

Copy `env.example` to `.env` and configure:

```bash
# Required for model panel
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Optional: W3C Verifiable Credentials
VC_ISSUER_DID=did:key:...
VC_PRIVATE_KEY_BASE58=...

# Optional: RDF storage
FUSEKI_URL=http://localhost:3030
```

## API Endpoints

### Claims
- `POST /claims` - Create claim
- `GET /claims/{id}` - Get claim with evaluations
- `POST /claims/{id}/evidence:statcan` - Fetch StatCan data  
- `POST /claims/{id}/panel/run` - Run model panel

### Consensus  
- `POST /consensus/{topic}/statements` - Add statement
- `POST /consensus/{topic}/votes` - Vote on statement
- `GET /consensus/{topic}/summary` - Get consensus summary

## Data Sources

- **Statistics Canada**: Crime Severity Index (Table 35-10-0026-01)
- **Wikidata**: Entity linking (Q16 = Canada)
- **Model APIs**: OpenAI GPT-5, Anthropic Claude Sonnet 4

## Limitations

⚠️ **For demonstration only**
- AI models may hallucinate
- Based on limited evidence sources
- Police-reported crime data has known gaps
- Not suitable for policy decisions

## Development

```bash
# Local development
npm install         # In apps/web/
pip install -e .    # In apps/adjudicator/

# With Docker
make dev            # Start with hot reload
make logs           # View logs
make test           # Run test suite
```

## Documentation

- [Architecture Decision Records](docs/)
- [API Reference](docs/API.md)
- [Data Sources](docs/DATA-SOURCES.md)
- [Transparency Report](docs/TRANSPARENCY.md)
- [NVC Guide](docs/NVC-GUIDE.md)

## Inspiration

- **Pol.is**: Consensus-finding methodology
- **Schema.org**: ClaimReview structured data
- **C2PA**: Content authenticity standards
- **W3C**: Verifiable Credentials for provenance

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new functionality  
4. Ensure all tests pass
5. Submit a pull request

## Transparency

All model evaluations, data sources, and processing steps are logged and available for audit. Download replay bundles to independently verify any claim evaluation.

---

**Built for transparency, designed for dialogue.**
