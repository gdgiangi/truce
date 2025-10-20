# Truce

**A transparent system for verifying contentious claims through multi-model AI analysis**

<img width="1920" height="987" alt="Screenshot 2025-10-20 at 11 54 18 AM" src="https://github.com/user-attachments/assets/a2f0028c-1493-46e1-bf79-05cd5cbf5e8b" />

> (Let's try and get this to 100%!)

## Quick Start

```bash
# Clone and start
git clone https://github.com/your-org/truce
cd truce
cp env.example .env  # Edit with your API keys

# Set your Brave API key for agentic research (free tier available)
export BRAVE_SEARCH_API_KEY=your_brave_api_key_here

# Start all services (API, MCP server, Web UI)
make dev
```

Visit **http://localhost:3000** and enter any claim to analyze.

## What is Truce?

Truce is a claim verification system that helps evaluate contentious statements through:

🔍 **Agentic Research**: Each AI agent independently researches claims using multi-turn search strategies  
🤖 **Multi-Model Analysis**: Independent evaluations from multiple AI models (GPT-4, Claude, Gemini, Grok)  
📊 **Consensus Metrics**: Aggregate verdicts showing agreement levels and confidence  
🔗 **Full Provenance**: Every piece of evidence tracked with timestamps and citations  
⚡ **FastMCP Integration**: Structured web search via Brave API exposed as MCP tools

## How to help

Truce is open to contributions of all sorts — from bug reports to new features, from documentation improvements to testing.  
If you’d like to help, we recommend the following steps:

1. Check out our [CONTRIBUTING.md](CONTRIBUTING.md) for a guide on how to get started.  
2. Browse issues tagged **good-first-issue**, **help-wanted**, or **enhancement** for tasks that are great for contributors.  
3. Found a bug? Report it with a clear description of what you expected, what happened, versions and environment.  
4. Have an idea for a new feature? Open a discussion or issue and tell us your use-case, proposed interface and impact.  
5. Ready to code? Fork the repo, create a branch, make your change, run tests/documentation updates, and open a pull request referencing the issue.  

We’re grateful for your help—every contribution makes Truce stronger and more useful.

> **Tip:** If you’re new to contributing, pick a small doc fix or a “good-first-issue” labelled task to get started. Welcome aboard!

## How It Works

### Agentic Research Mode (Default)
1. **Enter a claim** via the search interface
2. **Independent research**: Each AI agent conducts 5 turns of multi-strategy research via Brave API
   - Turn 1: Broad search on the claim
   - Turn 2: Multiple perspectives (research, government, fact-check, academic)
   - Turn 3: Targeted authoritative sources
   - Turn 4-5: Gap-filling based on analysis
3. **Evidence pooling**: All sources deduplicated and shared across agents
4. **Independent verdicts**: Each model analyzes ALL collected evidence
5. **Consensus aggregation**: Majority vote with confidence scoring

## Architecture

```
┌─────────────────┐
│   Web UI        │  (Next.js, port 3000)
│   localhost:3000│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Adjudicator    │◄───►│   MCP Server     │  (FastMCP, port 8888)
│   API Server    │     │  Brave Search    │
│  localhost:8000 │     │  localhost:8888  │
└─────────────────┘     └────────┬─────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │  Brave Search    │
         │              │      API         │
         │              └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Panel Agents   │
│  GPT-4, Claude  │  (4+ independent researchers)
│  Grok, Gemini   │
└─────────────────┘
```

## Features

### 🤖 Agentic Research (New!)
- **Independent Researchers**: Each AI agent conducts its own multi-turn research
- **Multi-Strategy Search**: Broad, perspective-based, targeted, and gap-filling searches
- **Evidence Pooling**: Automatic deduplication and sharing across all agents
- **Real-Time Progress**: Live SSE updates showing each research action
- **FastMCP Integration**: Structured Brave API access via MCP protocol

### 🔍 Core Capabilities
- **Dynamic Claim Analysis**: Enter any claim for real-time verification
- **Multi-Model Panel**: GPT-4, Claude Sonnet 4, Gemini 2.0, Grok 3
- **Evidence Provenance**: W3C Verifiable Credentials for all sources
- **Consensus Metrics**: Aggregate verdicts with confidence scores
- **Transparent Process**: Full visibility into model reasoning and data sources
- **Reproducible Results**: Export verification bundles for independent audit

## Commands

```bash
make dev        # Start all services (API, MCP server, Web UI)
make up         # Start services in background
make down       # Stop all services
make logs       # View all logs
make logs-mcp   # View MCP server logs only
make logs-api   # View API logs only
make logs-web   # View web UI logs only
make test       # Run test suite
make demo       # Full demo setup with seed data
make clean      # Clean up containers and data
```

## Configuration

⚠️ **API keys required**: Without API keys, the system will show stub responses.

### Required Setup

1. **Brave Search API** (for evidence gathering): https://brave.com/search/api/
2. **At least one AI API key**:
   - OpenAI (GPT-5): https://platform.openai.com/api-keys
   - Anthropic (Claude): https://console.anthropic.com/
   - Google (Gemini): https://makersuite.google.com/app/apikey
   - xAI (Grok): https://console.x.ai/

3. **Configure environment**:
```bash
cp env.example apps/adjudicator/.env
# Edit apps/adjudicator/.env with your keys
make up
```
### Environment Variables

```bash
# Required
BRAVE_SEARCH_API_KEY=your_brave_key

# At least one AI provider required
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
XAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Optional
VC_ISSUER_DID=did:key:...              # W3C Verifiable Credentials
VC_PRIVATE_KEY_BASE58=...
FUSEKI_URL=http://localhost:3030       # RDF triple store
```

## Limitations

⚠️ **Important Considerations**
- AI models can produce inaccurate or biased results
- Evidence quality depends on available data sources
- Not suitable for making critical decisions without human review
- System is designed for research and dialogue facilitation

## Development

### Local Setup
```bash
# Backend
cd apps/adjudicator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn truce_adjudicator.main:app --reload

# Frontend
cd apps/web
npm install
npm run dev
```

### Docker Setup
```bash
make up         # Start all services
make logs       # View logs
make test       # Run test suite
make clean      # Clean up
```

### Running Tests
```bash
# Backend tests
cd apps/adjudicator
pytest tests/

# Frontend tests
cd apps/web
npm test
```

## Technical Foundation

- **W3C Verifiable Credentials**: Provenance tracking
- **Schema.org ClaimReview**: Structured claim data
- **MCP (Model Context Protocol)**: Agent orchestration
- **Pol.is-inspired**: Consensus mechanisms

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built for transparency, designed for evidence-based dialogue.**
