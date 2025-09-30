"""Main FastAPI application for Truce Adjudicator"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

from .models import (
    Claim,
    ClaimCreate,
    ClaimResponse,
    Evidence,
    ConsensusStatement,
    ConsensusStatementRequest,
    ConsensusSummary,
    ConsensusVoteRequest,
    EvidenceRequest,
    PanelRequest,
    SearchResponse,
    TimeWindow,
    VerificationResponse,
    Vote,
    VoteType,
)
from . import search_index
from .verification import (
    DEFAULT_PROVIDERS,
    build_cache_key,
    compute_sources_hash,
    create_verification_record,
    filter_evidence_by_time_window,
    get_cached_verification,
    store_verification,
)
from .mcp import ExplorerAgent
from .mcp.explorer import compute_content_hash, normalize_url

explorer_agent = ExplorerAgent()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for demo (replace with proper database)
claims_db: Dict[str, Claim] = {}
statements_db: Dict[str, List[ConsensusStatement]] = {}
votes_db: List[Vote] = []

app = FastAPI(
    title="Truce Adjudicator",
    description="Claims, Evidence, and Consensus API",
    version="0.1.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_claim_by_id(claim_id: str) -> Claim:
    """Get claim by ID, raise 404 if not found"""
    if claim_id not in claims_db:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claims_db[claim_id]


def generate_slug(text: str) -> str:
    """Create URL-safe slug from claim text."""
    slug = text.lower().replace(" ", "-").replace(".", "")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug[:80]


def parse_datetime_param(value: Optional[str], field_name: str) -> Optional[datetime]:
    """Parse ISO8601 query parameters into datetime objects.

    Returns timezone-naive UTC datetimes to match Evidence.published_at format.
    """
    if value in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(value)
        # Convert timezone-aware datetimes to naive UTC to match Evidence timestamps
        if dt.tzinfo is not None:
            utc_tuple = dt.utctimetuple()
            dt = datetime(*utc_tuple[:6])  # Convert to naive UTC datetime
        return dt
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: must be ISO 8601 format",
        ) from exc


async def _gather_and_persist_sources(
    claim_slug: str, claim: Claim, window: TimeWindow
) -> List[Evidence]:
    """Gather explorer sources, deduplicate them, and persist as evidence."""

    gathered_sources = await explorer_agent.gather_sources(claim.text, window)
    if not gathered_sources:
        return []

    existing_urls = {
        evidence.normalized_url or normalize_url(evidence.url)
        for evidence in claim.evidence
        if evidence.url
    }
    existing_hashes = {
        evidence.content_hash or compute_content_hash(evidence.title or "", evidence.snippet)
        for evidence in claim.evidence
        if evidence.snippet
    }

    new_evidence: List[Evidence] = []

    for source in gathered_sources:
        normalized_url = source.normalized_url or normalize_url(source.url)
        content_hash = source.content_hash

        if normalized_url and normalized_url in existing_urls:
            continue
        if content_hash and content_hash in existing_hashes:
            continue

        evidence = source.to_evidence(provenance="mcp-explorer")
        claim.evidence.append(evidence)
        new_evidence.append(evidence)

        if evidence.normalized_url:
            existing_urls.add(evidence.normalized_url)
        if evidence.content_hash:
            existing_hashes.add(evidence.content_hash)

    if new_evidence:
        search_index.index_evidence_batch(
            claim_slug,
            [
                {
                    "evidence_id": str(evidence.id),
                    "snippet": evidence.snippet,
                    "publisher": evidence.publisher,
                    "url": evidence.url,
                }
                for evidence in new_evidence
            ],
        )

    return new_evidence


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "truce-adjudicator",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/claims", response_model=ClaimResponse)
async def create_claim(claim_request: ClaimCreate):
    """Create a new claim"""
    claim = Claim(
        text=claim_request.text,
        topic=claim_request.topic,
        entities=claim_request.entities,
    )
    
    # Generate slug from text for URL-friendly ID with timestamp and random suffix
    base_slug = generate_slug(claim_request.text)
    timestamp_suffix = int(datetime.utcnow().timestamp()) % 10000  # Last 4 digits of timestamp
    random_suffix = uuid4().hex[:4]  # Short random string
    slug = f"{base_slug}-{timestamp_suffix}-{random_suffix}"

    claims_db[slug] = claim
    search_index.index_claim(slug, claim.text)
    
    return ClaimResponse(claim=claim, slug=slug)


@app.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(claim_id: str):
    """Get a claim by ID"""
    claim = get_claim_by_id(claim_id)
    
    # Calculate consensus score from model assessments
    consensus_score = None
    if claim.model_assessments:
        support_count = sum(1 for ma in claim.model_assessments if ma.verdict.value == "supports")
        total_assessments = len(claim.model_assessments)
        consensus_score = support_count / total_assessments
    
    return ClaimResponse(
        claim=claim,
        consensus_score=consensus_score,
        provenance_verified=len(claim.evidence) > 0,
        replay_bundle_url=f"/replay/{claim_id}.jsonl"
    )


@app.post("/claims/{claim_id}/evidence:statcan")
async def add_statcan_evidence(claim_id: str, request: EvidenceRequest):
    """Add Statistics Canada evidence to a claim"""
    claim = get_claim_by_id(claim_id)
    
    # Import here to avoid circular imports
    from .statcan.fetch_csi import fetch_crime_severity_data
    
    try:
        evidence_list = await fetch_crime_severity_data()
        claim.evidence.extend(evidence_list)
        claim.updated_at = datetime.utcnow()

        search_index.index_evidence_batch(
            claim_id,
            [
                {
                    "evidence_id": str(evidence.id),
                    "snippet": evidence.snippet,
                    "publisher": evidence.publisher,
                    "url": evidence.url,
                }
                for evidence in evidence_list
            ],
        )
        
        return {"status": "success", "evidence_count": len(evidence_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch StatCan data: {str(e)}")


@app.get("/search", response_model=SearchResponse)
async def search_claims(q: str = Query(..., min_length=1)):
    """Search claims and evidence via SQLite FTS."""
    claim_rows, evidence_rows = search_index.search(q)

    claim_hits = [
        {
            "slug": row["slug"],
            "text": row["text"],
            "score": float(row["score"]),
        }
        for row in claim_rows
    ]

    evidence_hits = []
    for row in evidence_rows:
        evidence_id = row["evidence_id"]
        try:
            evidence_uuid = UUID(evidence_id) if evidence_id else None
        except ValueError:
            logger.warning("Invalid UUID format for evidence_id: %s", evidence_id)
            evidence_uuid = None

        if evidence_uuid is None:
            continue

        evidence_hits.append(
            {
                "claim_slug": row["claim_slug"],
                "evidence_id": evidence_uuid,
                "snippet": row["snippet"],
                "publisher": row["publisher"],
                "url": row["url"],
                "score": float(row["score"]),
            }
        )

    return SearchResponse(query=q, claims=claim_hits, evidence=evidence_hits)


@app.post("/claims/{claim_id}/verify", response_model=VerificationResponse)
async def verify_claim(
    claim_id: str,
    time_start: Optional[str] = Query(None),
    time_end: Optional[str] = Query(None),
    providers: Optional[List[str]] = Query(None, alias="providers[]"),
    force: bool = Query(False),
):
    """Verify a claim within an optional time window using deterministic cache."""

    claim = get_claim_by_id(claim_id)

    start_dt = parse_datetime_param(time_start, "time_start")
    end_dt = parse_datetime_param(time_end, "time_end")

    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="time_start must be before time_end")

    selected_providers = providers or DEFAULT_PROVIDERS
    window = TimeWindow(start=start_dt, end=end_dt)

    new_evidence = await _gather_and_persist_sources(claim_id, claim, window)

    if new_evidence:
        claim.updated_at = datetime.utcnow()

    evidence_in_range = filter_evidence_by_time_window(claim.evidence, start_dt, end_dt)
    sources_hash = compute_sources_hash(evidence_in_range)
    cache_key = build_cache_key(claim.text, window, selected_providers, sources_hash)

    if not force:
        cached_record = get_cached_verification(cache_key)
        if cached_record:
            return VerificationResponse(
                verification_id=cached_record.id,
                cached=True,
                verdict=cached_record.verdict,
                created_at=cached_record.created_at,
                providers=cached_record.providers,
                evidence_ids=cached_record.evidence_ids,
                time_window=cached_record.time_window,
            )

    new_record = create_verification_record(
        claim=claim,
        claim_slug=claim_id,
        evidence=evidence_in_range,
        providers=selected_providers,
        time_window=window,
        sources_hash=sources_hash,
    )

    store_verification(cache_key, new_record)
    claim.updated_at = datetime.utcnow()

    return VerificationResponse(
        verification_id=new_record.id,
        cached=False,
        verdict=new_record.verdict,
        created_at=new_record.created_at,
        providers=new_record.providers,
        evidence_ids=new_record.evidence_ids,
        time_window=new_record.time_window,
    )


@app.post("/claims/{claim_id}/panel/run")
async def run_model_panel(claim_id: str, request: PanelRequest):
    """Run multi-model evaluation panel"""
    claim = get_claim_by_id(claim_id)
    
    # Import here to avoid circular imports
    from .panel.run_panel import run_panel_evaluation
    
    try:
        assessments = await run_panel_evaluation(claim, request.models or ["gpt-5", "claude-sonnet-4-20250514"])
        claim.model_assessments.extend(assessments)
        claim.updated_at = datetime.utcnow()
        
        return {
            "status": "success",
            "assessments": assessments,
            "consensus_score": sum(1 for a in assessments if a.verdict.value == "supports") / len(assessments) if assessments else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Panel evaluation failed: {str(e)}")


@app.post("/consensus/{topic}/statements")
async def create_consensus_statement(topic: str, request: ConsensusStatementRequest):
    """Create a new consensus statement"""
    statement = ConsensusStatement(
        text=request.text,
        topic=topic,
        evidence_links=request.evidence_links
    )
    
    if topic not in statements_db:
        statements_db[topic] = []
    
    statements_db[topic].append(statement)
    
    return statement


@app.post("/consensus/{topic}/votes")
async def vote_on_statement(topic: str, request: ConsensusVoteRequest):
    """Vote on a consensus statement"""
    # Check if statement exists
    topic_statements = statements_db.get(topic, [])
    statement = None
    for s in topic_statements:
        if s.id == request.statement_id:
            statement = s
            break
    
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    
    # Create vote
    vote = Vote(
        statement_id=request.statement_id,
        user_id=request.user_id,
        session_id=request.session_id,
        vote=request.vote
    )
    
    votes_db.append(vote)
    
    # Update statement counts
    statement_votes = [v for v in votes_db if v.statement_id == statement.id]
    statement.agree_count = sum(1 for v in statement_votes if v.vote == VoteType.AGREE)
    statement.disagree_count = sum(1 for v in statement_votes if v.vote == VoteType.DISAGREE)
    statement.pass_count = sum(1 for v in statement_votes if v.vote == VoteType.PASS)
    
    total_votes = statement.agree_count + statement.disagree_count
    statement.agree_rate = statement.agree_count / total_votes if total_votes > 0 else 0.0
    
    return {"status": "success", "vote": vote}


@app.get("/consensus/{topic}/summary", response_model=ConsensusSummary)
async def get_consensus_summary(topic: str):
    """Get consensus summary for a topic"""
    topic_statements = statements_db.get(topic, [])
    
    if not topic_statements:
        return ConsensusSummary(
            topic=topic,
            statement_count=0,
            vote_count=0,
            overall_consensus=[],
            divisive=[],
            unvoted=[]
        )
    
    # Get votes for this topic
    topic_votes = [v for v in votes_db if any(s.id == v.statement_id for s in topic_statements)]
    
    # Categorize statements based on vote counts and agreement rates
    consensus_statements = []
    divisive_statements = []
    unvoted_statements = []
    
    for statement in topic_statements:
        total_votes = statement.agree_count + statement.disagree_count
        
        if total_votes < 3:  # Insufficient votes for meaningful categorization
            unvoted_statements.append(statement)
        elif statement.agree_rate >= 0.7:  # High agreement
            consensus_statements.append(statement)
        elif 0.3 <= statement.agree_rate <= 0.7:  # Mixed/divisive
            divisive_statements.append(statement)
        else:  # Low agreement (also a form of consensus - disagreement)
            consensus_statements.append(statement)
    
    # Sort each category
    consensus_statements.sort(key=lambda x: x.agree_rate, reverse=True)
    divisive_statements.sort(key=lambda x: abs(0.5 - x.agree_rate), reverse=True)
    unvoted_statements.sort(key=lambda x: x.created_at, reverse=True)
    
    # Generate opinion clusters using the clustering algorithm
    clusters = []
    if topic_votes and topic_statements:
        from .consensus.vote import cluster_users_by_votes
        try:
            clusters = cluster_users_by_votes(topic_statements, topic_votes, n_clusters=3)
        except Exception as e:
            print(f"Clustering failed: {e}")
            # Continue without clusters rather than failing entirely
    
    total_votes = len(topic_votes)
    
    return ConsensusSummary(
        topic=topic,
        statement_count=len(topic_statements),
        vote_count=total_votes,
        overall_consensus=consensus_statements[:5],
        divisive=divisive_statements[:5],
        unvoted=unvoted_statements[:10],  # Show up to 10 unvoted statements
        clusters=clusters
    )


@app.get("/replay/{claim_id}.jsonl")
async def get_replay_bundle(claim_id: str):
    """Get replay bundle for reproducibility"""
    claim = get_claim_by_id(claim_id)
    
    # Create replay bundle
    from .replay.bundle import create_replay_bundle
    
    try:
        bundle = await create_replay_bundle(claim)
        return JSONResponse(
            content=bundle.dict(),
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create replay bundle: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
