"""Pydantic models for Truce data structures"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class VerdictType(str, Enum):
    """Model verdict types"""
    SUPPORTS = "supports"
    REFUTES = "refutes"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


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
    seed_sources: List[str] = Field(default_factory=list, description="Optional initial sources")


class Evidence(BaseModel):
    """Evidence supporting or refuting a claim"""
    id: UUID = Field(default_factory=uuid4)
    url: str
    publisher: str
    published_at: Optional[datetime] = None
    snippet: str = Field(..., max_length=1000)
    provenance: str = Field(..., description="How this evidence was obtained")
    created_at: datetime = Field(default_factory=datetime.utcnow)


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

    @validator('user_id', 'session_id')
    def validate_identity(cls, v, values, field):
        """Ensure either user_id or session_id is provided"""
        if field.name == 'session_id' and v is None and values.get('user_id') is None:
            raise ValueError('Either user_id or session_id must be provided')
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
    overall_consensus: List[ConsensusStatement] = Field(..., description="High agreement statements")
    divisive: List[ConsensusStatement] = Field(..., description="High disagreement statements")
    clusters: List[ConsensusCluster] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    consensus_score: Optional[float] = None
    provenance_verified: bool = False
    replay_bundle_url: Optional[str] = None


# API Request/Response models
class EvidenceRequest(BaseModel):
    """Request to add evidence to a claim"""
    source_type: str = Field(..., description="e.g., 'statcan', 'manual'")
    params: Dict[str, Any] = Field(default_factory=dict)


class PanelRequest(BaseModel):
    """Request to run model panel evaluation"""
    models: List[str] = Field(default_factory=list, description="Specific models to use")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)


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
