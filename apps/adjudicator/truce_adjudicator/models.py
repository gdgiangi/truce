"""Pydantic models for Truce data structures"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class VerdictType(str, Enum):
    """Model verdict types"""

    SUPPORTS = "supports"
    REFUTES = "refutes"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class PanelVerdict(str, Enum):
    """Panel-level verdict values for provider outputs."""

    TRUE = "true"
    FALSE = "false"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class VoteType(str, Enum):
    """Vote types for consensus"""

    AGREE = "agree"  # +1
    DISAGREE = "disagree"  # -1
    PASS = "pass"  # 0


class ClaimCreate(BaseModel):
    """Request to create a new claim"""

    text: str = Field(..., min_length=10, max_length=500)
    topic: str = Field(..., min_length=3, max_length=100)
    entities: List[str] = Field(default_factory=list, description="Wikidata QIDs")
    seed_sources: List[str] = Field(
        default_factory=list, description="Optional initial sources"
    )


class Evidence(BaseModel):
    """Evidence supporting or refuting a claim"""

    id: UUID = Field(default_factory=uuid4)
    url: str
    publisher: str
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    domain: Optional[str] = None
    snippet: str = Field(..., max_length=1000)
    provenance: str = Field(..., description="How this evidence was obtained")
    normalized_url: Optional[str] = None
    content_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def model_post_init(self, _context: Any) -> None:
        """
        Pydantic v2 lifecycle hook called after model initialization.

        This method automatically computes the `normalized_url` and `content_hash` fields
        if they are not provided during instantiation. It is invoked after the model's
        fields have been populated, allowing for post-processing or validation.

        Args:
            _context (Any): Context information provided by Pydantic (unused).
        """
        if not self.normalized_url and self.url:
            from .mcp.explorer import normalize_url

            self.normalized_url = normalize_url(self.url)

        if not self.content_hash:
            from .mcp.explorer import compute_content_hash

            title = self.title or ""
            snippet = self.snippet or ""
            self.content_hash = compute_content_hash(title, snippet)


class ModelAssessment(BaseModel):
    """Assessment of a claim by an AI model"""

    id: UUID = Field(default_factory=uuid4)
    model_name: str
    verdict: VerdictType
    confidence: float = Field(..., ge=0.0, le=1.0)
    citations: List[UUID] = Field(..., description="Evidence IDs cited")
    rationale: str = Field(..., min_length=50, max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HumanReview(BaseModel):
    """Human review of a claim"""

    id: UUID = Field(default_factory=uuid4)
    author: str
    verdict: VerdictType
    notes: str = Field(..., max_length=2000)
    signature_vc: Optional[str] = Field(None, description="W3C Verifiable Credential")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Claim(BaseModel):
    """A claim to be evaluated"""

    id: UUID = Field(default_factory=uuid4)
    text: str
    entities: List[str] = Field(default_factory=list, description="Wikidata QIDs")
    topic: str
    evidence: List[Evidence] = Field(default_factory=list)
    model_assessments: List[ModelAssessment] = Field(default_factory=list)
    human_reviews: List[HumanReview] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    panel_results: List["PanelResult"] = Field(default_factory=list)


class ConsensusStatement(BaseModel):
    """A statement for consensus building"""

    id: UUID = Field(default_factory=uuid4)
    text: str = Field(..., min_length=10, max_length=140)
    topic: str
    agree_count: int = Field(default=0)
    disagree_count: int = Field(default=0)
    pass_count: int = Field(default=0)
    agree_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    cluster_id: Optional[int] = None
    evidence_links: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Vote(BaseModel):
    """A vote on a consensus statement"""

    id: UUID = Field(default_factory=uuid4)
    statement_id: UUID
    user_id: Optional[str] = None  # Authenticated user ID
    session_id: Optional[str] = None  # Anonymous session ID
    vote: VoteType
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("session_id", mode="after")
    @classmethod
    def validate_identity(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Ensure either user_id or session_id is provided"""
        user_id = info.data.get("user_id")
        session_id = v
        if user_id is None and session_id is None:
            raise ValueError("Either user_id or session_id must be provided")
        return v


class ConsensusCluster(BaseModel):
    """A cluster of users with similar voting patterns"""

    id: int
    statements: List[UUID]
    user_count: int
    avg_agreement: float = Field(..., ge=0.0, le=1.0)
    description: str


class ConsensusSummary(BaseModel):
    """Summary of consensus for a topic"""

    topic: str
    statement_count: int
    vote_count: int
    overall_consensus: List[ConsensusStatement] = Field(
        ..., description="High agreement statements"
    )
    divisive: List[ConsensusStatement] = Field(
        ..., description="High disagreement statements"
    )
    unvoted: List[ConsensusStatement] = Field(
        default_factory=list, description="Statements with insufficient votes"
    )
    clusters: List[ConsensusCluster] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TimeWindow(BaseModel):
    """Optional time window for evidence filtering."""

    start: Optional[datetime] = None
    end: Optional[datetime] = None


class ClaimSearchHit(BaseModel):
    """Search hit for a claim."""

    slug: str
    text: str
    score: float


class EvidenceSearchHit(BaseModel):
    """Search hit for evidence associated with a claim."""

    claim_slug: str
    evidence_id: UUID
    snippet: str
    publisher: str
    url: str
    score: float


class SearchResponse(BaseModel):
    """Combined search response across claims and evidence."""

    query: str
    claims: List[ClaimSearchHit] = Field(default_factory=list)
    evidence: List[EvidenceSearchHit] = Field(default_factory=list)
    suggestion_slug: Optional[str] = None  # Auto-created claim slug if no results found


class VerificationRecord(BaseModel):
    """Persistent record of a verification run."""

    id: UUID = Field(default_factory=uuid4)
    claim_slug: str
    verdict: VerdictType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    providers: List[str]
    evidence_ids: List[UUID] = Field(default_factory=list)
    sources_hash: str
    time_window: TimeWindow = Field(default_factory=TimeWindow)


class VerificationResponse(BaseModel):
    """API response payload for verification requests."""

    verification_id: UUID
    cached: bool
    verdict: VerdictType
    created_at: datetime
    providers: List[str]
    evidence_ids: List[UUID]
    assessment_ids: List[UUID] = Field(default_factory=list)
    time_window: TimeWindow


class StatCanData(BaseModel):
    """Statistics Canada data response"""

    table_id: str
    title: str
    data: List[Dict[str, Any]]
    last_updated: datetime
    source_url: str
    notes: Optional[str] = None


class ReplayBundle(BaseModel):
    """Reproducibility bundle for a claim evaluation"""

    id: UUID = Field(default_factory=uuid4)
    claim_id: UUID
    inputs: Dict[str, Any]
    model_prompts: List[Dict[str, Any]]
    model_responses: List[Dict[str, Any]]
    final_graph: Dict[str, Any]  # JSON-LD representation
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClaimResponse(BaseModel):
    """API response for a claim"""

    claim: Claim
    slug: Optional[str] = None
    consensus_score: Optional[float] = None
    provenance_verified: bool = False
    replay_bundle_url: Optional[str] = None
    panel: Optional["PanelResult"] = None


# API Request/Response models
class EvidenceRequest(BaseModel):
    """Request to add evidence to a claim"""

    source_type: str = Field(..., description="e.g., 'statcan', 'manual'")
    params: Dict[str, Any] = Field(default_factory=dict)


class PanelRequest(BaseModel):
    """Request to run model panel evaluation"""

    models: List[str] = Field(
        default_factory=list, description="Specific models to use"
    )
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None

    @field_validator("time_end")
    @classmethod
    def validate_time_window(
        cls, value: Optional[datetime], info: ValidationInfo
    ) -> Optional[datetime]:
        """Ensure the provided time window is consistent."""
        start = info.data.get("time_start")
        if value and start and value < start:
            raise ValueError("time_end must be greater than or equal to time_start")
        return value

    def to_time_window(self) -> "TimeWindow":
        """Convert request parameters into a TimeWindow instance."""
        return TimeWindow(start=self.time_start, end=self.time_end)


class ConsensusVoteRequest(BaseModel):
    """Request to vote on a consensus statement"""

    statement_id: UUID
    vote: VoteType
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ConsensusStatementRequest(BaseModel):
    """Request to create a new consensus statement"""

    text: str = Field(..., min_length=10, max_length=140)
    evidence_links: List[UUID] = Field(default_factory=list)


class CitationLink(BaseModel):
    """Links a text span to evidence source."""

    start: int = Field(..., description="Start character position in argument text")
    end: int = Field(..., description="End character position in argument text")
    evidence_id: UUID = Field(..., description="ID of the evidence source")
    text: str = Field(..., description="The cited text span")


class ArgumentWithEvidence(BaseModel):
    """An argument with supporting evidence and confidence level."""

    argument: str = Field(..., min_length=20, max_length=2000)
    evidence_ids: List[UUID] = Field(default_factory=list)
    citation_links: List[CitationLink] = Field(
        default_factory=list,
        description="Links between text spans and evidence sources",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


class PanelModelVerdict(BaseModel):
    """Structured verdict returned by an individual provider."""

    provider_id: str
    model: str
    approval_argument: ArgumentWithEvidence
    refusal_argument: ArgumentWithEvidence
    raw: Optional[Dict[str, Any]] = None
    failed: bool = Field(
        default=False, description="Whether this model evaluation failed"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_details: Optional[str] = Field(
        default=None, description="Detailed error information for debugging"
    )


class PanelSummary(BaseModel):
    """Aggregated summary across provider verdicts."""

    support_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregate confidence for approval"
    )
    refute_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregate confidence for refusal"
    )
    model_count: int = Field(..., ge=0)
    verdict: Optional[PanelVerdict] = Field(
        default=None, description="Derived verdict based on confidence scores"
    )


class PanelResult(BaseModel):
    """Complete panel evaluation payload."""

    prompt: Dict[str, Any]
    models: List[PanelModelVerdict] = Field(default_factory=list)
    summary: PanelSummary
    generated_at: datetime = Field(default_factory=datetime.utcnow)


Claim.model_rebuild()
ClaimResponse.model_rebuild()
