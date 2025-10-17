"""Main FastAPI application for Truce Adjudicator"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from . import search_index
from .mcp import ExplorerAgent
from .mcp.explorer import compute_content_hash, normalize_url
from .models import (
    Claim,
    ClaimCreate,
    ClaimResponse,
    ConsensusStatement,
    ConsensusStatementRequest,
    ConsensusSummary,
    ConsensusVoteRequest,
    Evidence,
    EvidenceRequest,
    PanelRequest,
    PanelResult,
    PanelSummary,
    SearchResponse,
    TimeWindow,
    VerificationResponse,
    Vote,
    VoteType,
)
from .panel.run_panel import (
    DEFAULT_PANEL_MODELS,
    panel_result_to_assessments,
    reconcile_complementary_verdicts,
    run_panel_evaluation,
)
from .verification import (
    DEFAULT_PROVIDERS,
    build_cache_key,
    compute_sources_hash,
    create_verification_record,
    filter_evidence_by_time_window,
    get_cached_verification,
    store_verification,
)

explorer_agent = ExplorerAgent()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for demo (replace with proper database)
claims_db: Dict[str, Claim] = {}
statements_db: Dict[str, List[ConsensusStatement]] = {}
votes_db: List[Vote] = []

# Progress tracking for claim creation
progress_streams: Dict[str, asyncio.Queue] = {}
cancelled_sessions: Set[str] = set()

app = FastAPI(
    title="Truce Adjudicator",
    description="Claims, Evidence, and Consensus API",
    version="0.1.0",
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


async def emit_progress(
    session_id: str, stage: str, message: str, details: Optional[Dict] = None
):
    """Emit a progress update to the session's SSE stream"""
    if session_id in progress_streams:
        event_data = {
            "stage": stage,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **(details or {}),
        }
        try:
            await progress_streams[session_id].put(event_data)
            logger.info(
                f"Progress emitted for session {session_id}: {stage} - {message}"
            )
        except Exception as e:
            logger.warning(f"Failed to emit progress for session {session_id}: {e}")
    else:
        logger.warning(f"No progress stream found for session {session_id}")


async def emit_agent_update(
    session_id: str,
    agent_name: str,
    action: str,
    reasoning: str = "",
    search_strategy: str = "",
    sources_found: List[str] = None,
    error: str = None,
):
    """Emit detailed agent activity updates."""
    details = {
        "agent_name": agent_name,
        "reasoning": reasoning,
        "search_strategy": search_strategy,
        "sources_found": sources_found or [],
    }

    if error:
        details["error_message"] = error
        await emit_progress(session_id, "error", action, details)
    else:
        await emit_progress(session_id, "agent_activity", action, details)


async def generate_progress_stream(session_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for claim creation progress"""
    try:
        # Use existing queue or create a new one
        if session_id not in progress_streams:
            progress_streams[session_id] = asyncio.Queue()

        logger.info(f"Starting SSE stream for session {session_id}")

        while True:
            try:
                # Wait for progress updates with timeout
                event_data = await asyncio.wait_for(
                    progress_streams[session_id].get(), timeout=30.0
                )

                # Format as SSE event
                yield f"data: {json.dumps(event_data)}\n\n"
                logger.info(
                    f"SSE sent for session {session_id}: {event_data.get('stage')}"
                )

                # Check if this is the completion event
                if event_data.get("stage") in ["complete", "error", "cancelled"]:
                    break

            except asyncio.TimeoutError:
                # Send keepalive
                yield f"data: {json.dumps({'stage': 'keepalive', 'message': 'Connection active'})}\n\n"

    except Exception as e:
        logger.error(f"Error in progress stream for session {session_id}: {e}")
        yield f"data: {json.dumps({'stage': 'error', 'message': 'Stream error occurred'})}\n\n"
    finally:
        # Clean up the session
        if session_id in progress_streams:
            del progress_streams[session_id]
            logger.info(f"Cleaned up session {session_id}")


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
    claim_slug: str, claim: Claim, window: TimeWindow, session_id: Optional[str] = None
) -> List[Evidence]:
    """Gather explorer sources, deduplicate them, and persist as evidence."""

    if session_id:
        await emit_progress(
            session_id, "gathering_sources", "Contacting data sources..."
        )

    logger.info(f"Starting evidence gathering for claim: {claim.text}")

    try:
        # Comprehensive evidence gathering without timeout - let it take the time needed
        gathered_sources = await explorer_agent.gather_sources(
            claim.text, window, session_id
        )
        logger.info(
            f"Evidence gathering completed. Found {len(gathered_sources)} sources"
        )

        if session_id and gathered_sources:
            await emit_progress(
                session_id,
                "processing_sources",
                f"Processing {len(gathered_sources)} sources...",
                {"raw_sources": len(gathered_sources)},
            )
    except Exception as e:
        logger.error(f"Error during evidence gathering: {e}")
        if session_id:
            await emit_progress(
                session_id,
                "api_error",
                "Some data sources unavailable, continuing with partial results...",
            )
        gathered_sources = []

    if not gathered_sources:
        return []
    # Build deduplication sets from all existing evidence, not just those with snippets
    existing_urls = {
        evidence.normalized_url
        for evidence in claim.evidence
        if evidence.normalized_url
    }
    existing_hashes = {
        evidence.content_hash for evidence in claim.evidence if evidence.content_hash
    }

    new_evidence: List[Evidence] = []
    total_sources = len(gathered_sources)
    processed_count = 0

    for i, source in enumerate(gathered_sources):
        normalized_url = source.normalized_url or normalize_url(source.url)
        content_hash = source.content_hash

        if normalized_url and normalized_url in existing_urls:
            continue
        if content_hash and content_hash in existing_hashes:
            continue

        evidence = source.to_evidence(provenance="mcp-explorer")

        claim.evidence.append(evidence)
        new_evidence.append(evidence)

        # Update deduplication sets to catch duplicates within the current batch
        if evidence.normalized_url:
            existing_urls.add(evidence.normalized_url)
        if evidence.content_hash:
            existing_hashes.add(evidence.content_hash)

        processed_count += 1

        # Check for cancellation during processing
        check_cancellation(session_id)

        # Emit granular progress every 5 sources or at milestones
        if session_id and (
            processed_count % 5 == 0 or processed_count == total_sources
        ):
            progress_pct = int((i + 1) / total_sources * 100)
            await emit_progress(
                session_id,
                "processing_evidence",
                f"Processed {processed_count} unique sources ({progress_pct}% complete)",
                {
                    "processed": processed_count,
                    "total": total_sources,
                    "unique_evidence": len(new_evidence),
                    "progress_pct": progress_pct,
                },
            )

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

    # Emit progress about evidence found
    if session_id:
        if new_evidence:
            await emit_progress(
                session_id,
                "evidence_found",
                f"Found and processed {len(new_evidence)} evidence sources",
                {"evidence_count": len(new_evidence)},
            )
        else:
            await emit_progress(
                session_id,
                "sources_limited",
                "Limited evidence sources found, continuing with analysis...",
            )

    return new_evidence


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "truce-adjudicator",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/claims/progress/{session_id}")
async def claim_progress_stream(session_id: str):
    """Server-Sent Events stream for claim creation progress"""
    return StreamingResponse(
        generate_progress_stream(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.delete("/claims/progress/{session_id}")
async def cancel_claim_creation(session_id: str):
    """Cancel an ongoing claim creation process"""
    if session_id in progress_streams:
        cancelled_sessions.add(session_id)
        await emit_progress(session_id, "cancelled", "Claim creation cancelled by user")
        return {"status": "cancelled", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


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
    timestamp_suffix = (
        int(datetime.utcnow().timestamp()) % 10000
    )  # Last 4 digits of timestamp
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
        support_count = sum(
            1 for ma in claim.model_assessments if ma.verdict.value == "supports"
        )
        total_assessments = len(claim.model_assessments)
        consensus_score = support_count / total_assessments

    return ClaimResponse(
        claim=claim,
        slug=claim_id,  # Include the claim_id as slug in response
        consensus_score=consensus_score,
        provenance_verified=len(claim.evidence) > 0,
        replay_bundle_url=f"/replay/{claim_id}.jsonl",
        panel=claim.panel_results[-1] if claim.panel_results else None,
    )


@app.post("/claims/{claim_id}/evidence:statcan")
async def add_statcan_evidence(
    claim_id: str, request: Optional[EvidenceRequest] = None
):
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
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch StatCan data: {str(e)}"
        )


@app.get("/search", response_model=SearchResponse)
async def search_claims(
    q: str = Query(..., min_length=1), auto_create: bool = Query(False)
):
    """Search claims and evidence via SQLite FTS, with optional auto-creation."""
    from .models import ClaimSearchHit, EvidenceSearchHit

    claim_rows, evidence_rows = search_index.search(q)

    claim_hits = [
        ClaimSearchHit(
            slug=row["slug"],
            text=row["text"],
            score=float(row["score"]),
        )
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
            EvidenceSearchHit(
                claim_slug=row["claim_slug"],
                evidence_id=evidence_uuid,
                snippet=row["snippet"],
                publisher=row["publisher"],
                url=row["url"],
                score=float(row["score"]),
            )
        )

    # If no relevant claims found and auto_create is enabled, create a new claim
    suggestion_slug = None
    if len(claim_hits) == 0 and auto_create and len(q.strip()) > 10:
        suggestion_slug = await _create_claim_from_query(q.strip())

    return SearchResponse(
        query=q,
        claims=claim_hits,
        evidence=evidence_hits,
        suggestion_slug=suggestion_slug,
    )


@app.post("/claims/create-async")
async def create_claim_async(request: Dict[str, str]):
    """Start async claim creation and return session ID for progress tracking"""
    query = request.get("query", "").strip()
    if len(query) < 10:
        raise HTTPException(
            status_code=400, detail="Query must be at least 10 characters"
        )

    # Generate session ID
    session_id = str(uuid4())

    # Pre-create the progress stream to avoid race condition
    progress_streams[session_id] = asyncio.Queue()

    # Start claim creation in background
    asyncio.create_task(_create_claim_from_query_background(query, session_id))

    return {"session_id": session_id}


async def _create_claim_from_query_background(query: str, session_id: str):
    """Background task wrapper for claim creation with error handling"""
    try:
        slug = await _create_claim_from_query(query, session_id)
        # Final completion event is sent from within _create_claim_from_query
    except asyncio.CancelledError:
        logger.info(f"Claim creation cancelled for session {session_id}")
        if session_id in progress_streams:
            await emit_progress(session_id, "cancelled", "Claim creation was cancelled")
    except Exception as e:
        logger.error(f"Background claim creation failed for session {session_id}: {e}")
        if session_id in progress_streams:
            await emit_progress(
                session_id, "error", f"Failed to create claim: {str(e)}"
            )
    finally:
        # Clean up cancellation tracking
        if session_id in cancelled_sessions:
            cancelled_sessions.remove(session_id)


def check_cancellation(session_id: Optional[str]):
    """Check if the session has been cancelled"""
    if session_id and session_id in cancelled_sessions:
        raise asyncio.CancelledError(f"Session {session_id} was cancelled by user")


async def _create_claim_from_query(query: str, session_id: Optional[str] = None) -> str:
    """Create a new claim from a search query and populate it with evidence."""
    try:
        # Check cancellation before starting
        check_cancellation(session_id)

        # Emit progress: Initializing
        if session_id:
            await emit_progress(
                session_id, "initializing", "Setting up claim analysis..."
            )

        # Create the claim
        claim = Claim(
            text=query,
            topic="auto-generated",
            entities=[],
        )

        # Generate slug
        base_slug = generate_slug(query)
        timestamp_suffix = int(datetime.utcnow().timestamp()) % 10000
        random_suffix = uuid4().hex[:4]
        slug = f"{base_slug}-{timestamp_suffix}-{random_suffix}"

        claims_db[slug] = claim
        search_index.index_claim(slug, claim.text)

        # Check cancellation before evidence gathering
        check_cancellation(session_id)

        # Emit progress: Searching for evidence
        if session_id:
            await emit_progress(
                session_id, "searching", "Searching for evidence sources..."
            )

        # Skip traditional evidence gathering - agentic research will handle it
        window = TimeWindow()  # No time constraints for new claims
        logger.info(
            f"Created claim '{slug}' - agentic research will gather evidence during panel evaluation"
        )

        # Check cancellation before AI evaluation
        check_cancellation(session_id)

        # Run agentic research panel evaluation (will gather evidence during research)
        if session_id:
            await emit_progress(
                session_id,
                "evaluating",
                "Starting agentic research and AI evaluation...",
            )

        try:
            # Add timeout for panel evaluation (180 seconds for agentic research)
            server_url = os.getenv("MCP_BRAVE_SERVER_URL", "http://mcp-server:8888/mcp")
            panel_result = await asyncio.wait_for(
                run_panel_evaluation(
                    claim,
                    DEFAULT_PANEL_MODELS,
                    window,
                    session_id=session_id,
                    enable_agentic_research=True,
                    mcp_server_url=server_url,
                ),
                timeout=180.0,  # Longer timeout for agentic research
            )
            claim.panel_results.append(panel_result)
            claim.model_assessments = panel_result_to_assessments(panel_result)
            claim.updated_at = datetime.utcnow()
            logger.info(f"Completed panel evaluation for new claim '{slug}'")

            if session_id:
                model_count = len(panel_result.models) if panel_result else 0
                await emit_progress(
                    session_id,
                    "evaluation_complete",
                    f"Analysis complete: {model_count} AI models evaluated the claim",
                    {"model_count": model_count, "slug": slug},
                )
        except asyncio.TimeoutError:
            logger.warning(f"Panel evaluation timed out for new claim '{slug}'")
            if session_id:
                await emit_progress(
                    session_id,
                    "evaluation_timeout",
                    "AI evaluation taking longer than expected, claim saved with evidence only",
                )
        except Exception as e:
            logger.warning(
                f"Failed to run panel evaluation for new claim '{slug}': {e}"
            )
            if session_id:
                await emit_progress(
                    session_id,
                    "evaluation_error",
                    "AI evaluation failed, but claim created successfully with evidence",
                )

        # Emit completion
        if session_id:
            await emit_progress(
                session_id,
                "complete",
                "Claim analysis complete! Redirecting...",
                {"slug": slug},
            )

        return slug

    except Exception as e:
        logger.error(f"Failed to create claim from query '{query}': {e}")
        if session_id:
            await emit_progress(
                session_id, "error", f"Failed to create claim: {str(e)}"
            )
        raise


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
        raise HTTPException(
            status_code=400, detail="time_start must be before time_end"
        )

    selected_providers = providers or DEFAULT_PROVIDERS
    window = TimeWindow(start=start_dt, end=end_dt)

    # Compute cache key with existing evidence before gathering new sources
    evidence_in_range = filter_evidence_by_time_window(claim.evidence, start_dt, end_dt)
    existing_sources_hash = compute_sources_hash(evidence_in_range)
    existing_cache_key = build_cache_key(
        claim.text, window, selected_providers, existing_sources_hash
    )

    # Check cache with existing evidence first (unless force refresh requested)
    cached_record = None
    if not force:
        cached_record = get_cached_verification(existing_cache_key)

    # Always attempt to gather new evidence to keep claims up-to-date
    new_evidence = []
    try:
        new_evidence = await _gather_and_persist_sources(claim_id, claim, window)
        if new_evidence:
            claim.updated_at = datetime.utcnow()
    except Exception as e:
        logger.warning(
            f"Explorer agent failed to gather sources for claim {claim_id}: {e}"
        )
        # Continue with existing evidence if explorer fails

    # If new evidence was found, we need a fresh verification that includes it
    if new_evidence:
        # Recompute evidence and cache key with new evidence included
        evidence_in_range = filter_evidence_by_time_window(
            claim.evidence, start_dt, end_dt
        )
        sources_hash = compute_sources_hash(evidence_in_range)
        cache_key = build_cache_key(
            claim.text, window, selected_providers, sources_hash
        )
    else:
        # No new evidence, use existing values and return cached result if available
        cache_key = existing_cache_key
        sources_hash = existing_sources_hash
        if cached_record:
            return VerificationResponse(
                verification_id=cached_record.id,
                cached=True,
                verdict=cached_record.verdict,
                created_at=cached_record.created_at,
                providers=cached_record.providers,
                evidence_ids=cached_record.evidence_ids,
                assessment_ids=[a.id for a in claim.model_assessments],
                time_window=cached_record.time_window,
            )

    # Create new verification record since no cached version exists
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
        assessment_ids=[a.id for a in claim.model_assessments],
        time_window=new_record.time_window,
    )


@app.post("/claims/{claim_id}/panel/run")
async def run_model_panel(
    claim_id: str,
    request: PanelRequest,
    agentic: bool = Query(True, description="Enable agentic research mode"),
    mcp_server_url: Optional[str] = Query(
        None, description="FastMCP Brave Search server URL"
    ),
):
    """Run multi-model evaluation panel with optional agentic research"""
    claim = get_claim_by_id(claim_id)

    try:
        # Determine MCP server URL
        server_url = mcp_server_url or os.getenv(
            "MCP_BRAVE_SERVER_URL", "http://localhost:8000/mcp"
        )

        panel_result = await run_panel_evaluation(
            claim,
            request.models or DEFAULT_PANEL_MODELS,
            request.to_time_window(),
            session_id=None,  # Could add session support for progress tracking
            enable_agentic_research=agentic,
            mcp_server_url=server_url,
        )

        claim.panel_results.append(panel_result)
        if len(claim.panel_results) > 5:
            claim.panel_results = claim.panel_results[-5:]

        claim.model_assessments = panel_result_to_assessments(panel_result)
        claim.updated_at = datetime.utcnow()

        # Apply complementary claim reconciliation if needed
        panel_result = await _apply_complementary_reconciliation(claim, panel_result)

        # If agentic research was used, update the claim's evidence
        if agentic and panel_result.models:
            # Extract evidence from the enriched claim used in panel evaluation
            # The evidence would have been collected during the agentic research phase
            pass  # Evidence is already updated in the agentic research flow

        return {
            "status": "success",
            "panel": panel_result,
            "agentic_research": agentic,
            "evidence_count": len(claim.evidence) if claim.evidence else 0,
        }
    except Exception as e:
        logger.error(f"Panel evaluation failed for claim {claim_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Panel evaluation failed: {str(e)}"
        )


@app.post("/claims/{claim_id}/panel/agentic")
async def run_agentic_panel_with_progress(claim_id: str, request: PanelRequest):
    """Run agentic panel evaluation with real-time progress updates via SSE"""
    claim = get_claim_by_id(claim_id)
    session_id = str(uuid4())

    # Create progress queue for this session
    progress_streams[session_id] = asyncio.Queue()

    async def generate_progress():
        """Generate SSE stream with progress updates"""
        try:
            # Start the agentic research process
            server_url = os.getenv("MCP_BRAVE_SERVER_URL", "http://localhost:8000/mcp")

            # Run agentic panel evaluation with progress tracking
            panel_task = asyncio.create_task(
                run_panel_evaluation(
                    claim,
                    request.models or DEFAULT_PANEL_MODELS,
                    request.to_time_window(),
                    session_id=session_id,
                    enable_agentic_research=True,
                    mcp_server_url=server_url,
                )
            )

            # Stream progress updates
            while not panel_task.done():
                try:
                    # Wait for progress update with timeout
                    progress_data = await asyncio.wait_for(
                        progress_streams[session_id].get(), timeout=1.0
                    )

                    # Send progress update
                    yield f"data: {json.dumps(progress_data)}\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                except Exception as e:
                    logger.error(f"Progress stream error: {e}")
                    break

            # Get final result
            try:
                panel_result = await panel_task

                # Update claim with results
                claim.panel_results.append(panel_result)
                if len(claim.panel_results) > 5:
                    claim.panel_results = claim.panel_results[-5:]

                claim.model_assessments = panel_result_to_assessments(panel_result)
                claim.updated_at = datetime.utcnow()

                # Apply complementary claim reconciliation if needed
                panel_result = await _apply_complementary_reconciliation(
                    claim, panel_result
                )

                # Send completion event
                completion_data = {
                    "type": "completion",
                    "status": "success",
                    "panel": {
                        "verdict": (
                            panel_result.summary.verdict.value
                            if panel_result.summary.verdict
                            else "unknown"
                        ),
                        "support_confidence": panel_result.summary.support_confidence,
                        "refute_confidence": panel_result.summary.refute_confidence,
                        "model_count": panel_result.summary.model_count,
                        "evidence_count": len(claim.evidence) if claim.evidence else 0,
                    },
                }
                yield f"data: {json.dumps(completion_data)}\n\n"

            except Exception as e:
                logger.error(f"Agentic panel evaluation failed: {e}")
                error_data = {
                    "type": "error",
                    "message": f"Panel evaluation failed: {str(e)}",
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        finally:
            # Cleanup
            if session_id in progress_streams:
                del progress_streams[session_id]

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/consensus/{topic}/statements")
async def create_consensus_statement(topic: str, request: ConsensusStatementRequest):
    """Create a new consensus statement"""
    statement = ConsensusStatement(
        text=request.text, topic=topic, evidence_links=request.evidence_links
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
        vote=request.vote,
    )

    votes_db.append(vote)

    # Update statement counts
    statement_votes = [v for v in votes_db if v.statement_id == statement.id]
    statement.agree_count = sum(1 for v in statement_votes if v.vote == VoteType.AGREE)
    statement.disagree_count = sum(
        1 for v in statement_votes if v.vote == VoteType.DISAGREE
    )
    statement.pass_count = sum(1 for v in statement_votes if v.vote == VoteType.PASS)

    total_votes = statement.agree_count + statement.disagree_count
    statement.agree_rate = (
        statement.agree_count / total_votes if total_votes > 0 else 0.0
    )

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
            unvoted=[],
        )

    # Get votes for this topic
    topic_votes = [
        v for v in votes_db if any(s.id == v.statement_id for s in topic_statements)
    ]

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
            clusters = cluster_users_by_votes(
                topic_statements, topic_votes, n_clusters=3
            )
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
        clusters=clusters,
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
            content=bundle.model_dump(mode="json"),
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create replay bundle: {str(e)}"
        )


async def _apply_complementary_reconciliation(
    claim: Claim, panel_result: PanelResult
) -> PanelResult:
    """
    Apply complementary claim reconciliation within the same topic.

    Checks for other claims in the same topic that might be complementary
    and reconciles their verdicts to ensure logical consistency.
    """

    # Find other claims in the same topic
    topic_claims = [
        c for c in claims_db.values() if c.topic == claim.topic and c.id != claim.id
    ]

    # Check each claim for complementarity
    for other_claim in topic_claims:
        if not other_claim.panel_results:
            continue

        other_panel = other_claim.panel_results[-1]  # Most recent panel result

        # Apply reconciliation
        reconciled_current, reconciled_other = reconcile_complementary_verdicts(
            claim.text, panel_result.summary, other_claim.text, other_panel.summary
        )

        # If reconciliation changed the current claim's summary, update it
        if (
            reconciled_current.support_confidence
            != panel_result.summary.support_confidence
            or reconciled_current.refute_confidence
            != panel_result.summary.refute_confidence
        ):

            # Create new panel result with reconciled summary
            panel_result = PanelResult(
                prompt=panel_result.prompt,
                models=panel_result.models,
                summary=reconciled_current,
            )

            # Also update the other claim if it was reconciled
            if (
                reconciled_other.support_confidence
                != other_panel.summary.support_confidence
                or reconciled_other.refute_confidence
                != other_panel.summary.refute_confidence
            ):

                other_reconciled_panel = PanelResult(
                    prompt=other_panel.prompt,
                    models=other_panel.models,
                    summary=reconciled_other,
                )

                # Update the other claim's most recent panel result
                other_claim.panel_results[-1] = other_reconciled_panel
                other_claim.model_assessments = panel_result_to_assessments(
                    other_reconciled_panel
                )
                other_claim.updated_at = datetime.utcnow()

            break  # Only reconcile with the first complementary claim found

    return panel_result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
