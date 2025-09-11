# ADR-0001: MVP Scope - Canadian Crime Statistics

**Status**: Accepted  
**Date**: 2024-01-01  
**Deciders**: Truce Team  

## Context

For the Truce MVP, we need to choose a single contentious topic that demonstrates the system's core capabilities: transparent evidence evaluation, multi-model analysis, and consensus building.

## Decision

We will implement "Violent crime in Canada is rising" as our demo topic because:

### Evidence Availability
- Statistics Canada provides high-quality, accessible data via REST API
- Crime Severity Index offers both volume and severity metrics
- Historical data (1998-2024) enables trend analysis
- Multiple related datasets available for cross-reference

### Model Evaluation Complexity
- Temporal claims require nuanced interpretation
- Statistical literacy challenges for AI models
- Multiple valid interpretations based on time windows
- Clear caveats about data limitations (under-reporting, etc.)

### Consensus Building Potential
- Policy-relevant topic with diverse viewpoints
- Evidence-based statements possible
- Bridges between different perspectives discoverable
- Demonstrates non-partisan, fact-focused dialogue

### Technical Implementation
- Single API integration (StatCan WDS)
- Clear data provenance chain
- Reproducible via cached CSV files
- JSON-LD mapping to established vocabularies

## Alternatives Considered

1. **Climate Change Claims**: Too politically polarized, less clear data sources
2. **Economic Indicators**: Less engaging for general public
3. **Health Statistics**: Privacy concerns, more complex data relationships

## Consequences

### Positive
- Demonstrates full pipeline with real government data
- Shows both supporting and contradicting evidence
- Enables meaningful consensus exploration
- Clear methodology for extension to other topics

### Negative
- Limited to Canadian context
- Single domain expertise required
- May not represent all types of contentious claims
- Police-reported data limitations affect conclusions

## Implementation Notes

- Use StatCan Table 35-10-0026-01 (Crime Severity Index)
- Focus on 2021-2024 period for recent trends
- Include methodology caveats prominently
- Seed ~10 evidence-based consensus statements
- Enable download of complete replay bundles

## Success Criteria

1. Claim card shows StatCan data with clear citations
2. Multiple AI models provide different interpretations
3. Consensus board identifies areas of agreement
4. All data sources and methods are transparent
5. Results are independently reproducible
