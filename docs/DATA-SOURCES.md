# Data Sources

## Statistics Canada

### Primary Data Source

**Table 35-10-0026-01: Crime severity index and weighted clearance rates, Canada, provinces, territories and Census Metropolitan Areas**

- **URL**: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510002601
- **API**: https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownload/3510002601/en
- **Coverage**: 1998-2024 (annual data)
- **Geography**: Canada, provinces, territories, CMAs
- **Metrics**: Total CSI, Violent CSI, Non-violent CSI

### Methodology

The Crime Severity Index (CSI):
- Measures both volume and severity of police-reported crime
- Standardized to 2006=100 baseline
- Weights crimes by average sentence length
- More serious crimes have greater impact on the index
- Calculated using Uniform Crime Reporting Survey data

### Data Processing

1. **Extraction**: REST API call to StatCan WDS
2. **Filtering**: Canada-level data, recent years (2019-2024)
3. **Caching**: Raw CSV stored in `data/statcan/35-10-0026-01.csv`
4. **Transformation**: Convert to Evidence objects with citations

### Known Limitations

#### Under-reporting
- Based on police-reported incidents only
- Actual crime rates may be higher
- Reporting rates vary by:
  - Crime type (violent vs. property vs. victimless)
  - Demographics (age, gender, income, ethnicity)
  - Geography (urban vs. rural)
  - Time period (social attitudes change)

#### Methodological Changes
- CSI methodology updated periodically
- Changes in police practices affect reporting
- Legal definitions of crimes evolve
- New crime categories added over time

#### Data Quality Issues
- Administrative data, not survey data
- Dependent on police record-keeping
- Inconsistent practices across jurisdictions
- Missing data for some small areas

## Secondary Sources

### Table 35-10-0177-01: Incident-based crime statistics

- **Purpose**: Detailed crime incident data
- **Usage**: Context and drill-down analysis
- **Coverage**: 2009-present
- **Granularity**: Individual incident characteristics

## Wikidata Integration

### Entity Linking

- **Canada**: `Q16`
- **Crime**: `Q83267`
- **Statistics Canada**: `Q1155740`

### Usage
- Link claims to structured knowledge
- Enable cross-language support
- Connect to related concepts
- Support semantic web standards

## Caching Strategy

### Local Files
```
data/statcan/
├── 35-10-0026-01.csv     # Raw CSI data
├── 35-10-0026-01.json    # Processed metadata
└── cache_metadata.json   # Last updated timestamps
```

### Cache Invalidation
- Daily API check for updates
- StatCan typically releases annually in July
- Manual refresh available via API
- Fallback to cached data if API unavailable

## API Endpoints

### Statistics Canada WDS

```bash
# Table metadata
GET https://www150.statcan.gc.ca/t1/wds/rest/getDatasetMetadata/{table_id}/en

# Full table download (CSV)
GET https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownload/{table_id}/en

# Filtered data (JSON)
POST https://www150.statcan.gc.ca/t1/wds/rest/getFilteredTableData
```

### Rate Limits
- No documented limits
- Respectful usage: 1 request/second
- Cache responses locally
- Use CSV format for bulk downloads

## Data Citation

### Format
```
Statistics Canada. Table 35-10-0026-01 Crime severity index and weighted 
clearance rates, Canada, provinces, territories and Census Metropolitan Areas. 
https://doi.org/10.25318/3510002601-eng (accessed January 1, 2024).
```

### Provenance Chain
1. **Origin**: Uniform Crime Reporting Survey
2. **Processor**: Statistics Canada
3. **Access**: WDS REST API
4. **Cache**: Local CSV file
5. **Transform**: Evidence objects in Truce
6. **Display**: Web interface with citations

## Quality Assurance

### Validation Checks
- Compare against official StatCan Daily releases
- Cross-reference with provincial data
- Verify against previous year's data
- Check for missing or anomalous values

### Error Handling
- API failure → Use cached data + warning
- Parse error → Log error, exclude problematic records
- Missing data → Note gaps in evidence
- Stale data → Show last update timestamp

## Future Data Sources

### Planned
- Provincial crime data (more granular)
- Victimization surveys (capture unreported crime)
- Court data (sentencing outcomes)
- International comparisons (OECD, UN)

### Potential
- Social media sentiment analysis
- News coverage analysis
- Academic research papers
- Policy documents

## Access Logs

All data access is logged with:
- Timestamp
- Source URL
- Response size
- Processing time
- Cache hit/miss
- Error conditions

This ensures full transparency and reproducibility.
