# Agentic Research Implementation Plan

## Overview
This document outlines the implementation of a deep agentic research system for the Truce Adjudicator, transforming the deterministic evidence gathering approach into a multi-agent research flow where each panel model conducts independent research using FastMCP and the Brave Search API.

## Architecture Changes

### 1. FastMCP Brave Search Server
**File**: `apps/adjudicator/truce_adjudicator/mcp/brave_search_server.py`

- Created a dedicated FastMCP server that exposes Brave Search API as MCP tools
- Supports three main tools:
  - `web_search`: General web search with time filters
  - `search_multiple_perspectives`: Multi-angle research with different viewpoints
  - `targeted_source_search`: Search specific authoritative sources
- Includes rate limiting and proper error handling
- Maps domain names to friendly publisher names

### 2. Agentic Research System
**File**: `apps/adjudicator/truce_adjudicator/panel/agentic_research.py`

#### AgenticResearcher Class
- Conducts independent multi-turn research for each panel agent
- **Research Turns**:
  - Turn 0: Broad search on the claim
  - Turn 1: Multiple perspectives search (research, government, fact-check, academic)
  - Turn 2: Targeted source search (official sites)
  - Turn 3+: Gap-filling searches based on analysis
- **Research Planning**: Adaptive research strategy based on collected evidence
- **Progress Tracking**: Real-time updates via session-based progress system

#### SharedEvidencePool Class
- Deduplicates evidence across all research agents by URL hash
- Provides summary statistics (domains, publishers, counts)
- Ensures no duplicate sources while preserving provenance

### 3. Enhanced Panel System
**File**: `apps/adjudicator/truce_adjudicator/panel/run_panel.py`

#### New Agentic Flow
1. **Independent Research Phase**: Each panel agent conducts separate research
2. **Evidence Sharing**: All collected evidence is pooled and deduplicated
3. **Verdict Formation**: Each agent analyzes ALL collected evidence independently
4. **Aggregation**: Traditional majority vote aggregation on independent verdicts

#### Dual-Mode Support
- `enable_agentic_research=True`: Full agentic research mode
- `enable_agentic_research=False`: Traditional mode with pre-gathered evidence

### 4. API Integration
**File**: `apps/adjudicator/truce_adjudicator/main.py`

#### New Endpoints
- `POST /claims/{claim_id}/panel/run?agentic=true`: Agentic panel evaluation
- `POST /claims/{claim_id}/panel/agentic`: Agentic evaluation with SSE progress

#### Updated Endpoints
- Enhanced existing panel endpoint to support agentic mode via query parameter
- Added MCP server URL configuration via environment variable

### 5. Startup Infrastructure
**File**: `apps/adjudicator/truce_adjudicator/scripts/start_brave_server.py`

- Standalone script to start the FastMCP Brave Search server
- Environment variable validation
- Clear setup instructions

## Key Benefits

### 1. Independent Agent Research
- Each panel agent (GPT-4, Claude, Grok, Gemini) conducts its own research
- No bias from shared initial evidence gathering
- Agents can focus on different aspects and sources

### 2. Multi-Turn Agentic Behavior
- Agents adapt their search strategy based on findings
- Progressive refinement of research questions
- Gap identification and targeted follow-up searches

### 3. Comprehensive Evidence Collection
- Multiple search strategies per agent (broad, perspective, targeted, gap-filling)
- Diverse source types (academic, government, news, expert analysis)
- Intelligent deduplication while preserving provenance

### 4. Real-Time Progress Tracking
- Server-Sent Events for live research progress
- Detailed logging of each agent's research actions
- Transparent multi-phase evaluation process

## Configuration

### Environment Variables
```bash
# Required for Brave Search API
BRAVE_SEARCH_API_KEY=your_brave_api_key

# Optional MCP server URL (defaults to http://localhost:8000/mcp)
MCP_BRAVE_SERVER_URL=http://localhost:8000/mcp
```

### Dependencies
- Added `fastmcp>=2.0.0` to requirements.txt
- Existing dependencies (aiohttp, beautifulsoup4) support the implementation

## Testing

### Automated Tests
**File**: `apps/adjudicator/tests/test_agentic_research.py`

- Unit tests for AgenticResearcher class
- SharedEvidencePool functionality tests
- Mock-based integration tests for the full research flow
- Evidence conversion and deduplication validation

### Manual Verification
- Updated `HOW_TO_VERIFY.md` with comprehensive testing procedures
- Separate test flows for traditional and agentic modes
- Direct MCP server testing endpoints
- Progress tracking verification with SSE

## Migration Strategy

### Backward Compatibility
- Original panel evaluation system remains fully functional
- Agentic research is opt-in via API parameters
- No breaking changes to existing API contracts

### Gradual Adoption
- Users can test agentic mode alongside traditional mode
- Evidence quality can be compared between approaches
- Performance characteristics can be evaluated

## Future Enhancements

### Potential Improvements
1. **Agent Specialization**: Different research strategies per agent type
2. **Source Quality Scoring**: Prioritize higher-quality sources
3. **Collaborative Research**: Agents could share research strategies
4. **Cost Optimization**: Intelligent search budget management
5. **Evidence Ranking**: ML-based relevance scoring

### Integration Opportunities
1. **Custom MCP Tools**: Domain-specific research tools
2. **Multi-API Sources**: Integration with additional search APIs
3. **Expert Knowledge**: Integration with academic databases
4. **Fact-Checking APIs**: Specialized verification services

## Implementation Status

All core components have been implemented and tested:

✅ **FastMCP Brave Search Server**: Complete with all three search tools
✅ **Agentic Research System**: Multi-turn research with evidence pooling
✅ **Enhanced Panel System**: Dual-mode support with independent agent research
✅ **API Integration**: New endpoints and progress tracking
✅ **Testing Infrastructure**: Comprehensive test suite and verification procedures
✅ **Documentation**: Complete setup and verification guide

The system is ready for deployment and testing with real research scenarios.
