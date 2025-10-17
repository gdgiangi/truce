"""Tests for Pydantic model validation and data integrity"""

from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from truce_adjudicator.models import (
    Claim,
    ClaimCreate,
    ConsensusStatement,
    Evidence,
    HumanReview,
    ModelAssessment,
    TimeWindow,
    VerdictType,
    Vote,
    VoteType,
)


class TestVerdictType:
    """Test VerdictType enum"""

    @pytest.mark.unit
    def test_verdict_type_values(self):
        """Test all verdict type values are valid"""
        assert VerdictType.SUPPORTS == "supports"
        assert VerdictType.REFUTES == "refutes"
        assert VerdictType.MIXED == "mixed"
        assert VerdictType.UNCERTAIN == "uncertain"

    @pytest.mark.unit
    def test_verdict_type_validation(self):
        """Test verdict type validation in models"""
        # Valid verdict type
        assessment = ModelAssessment(
            model_name="test-model",
            verdict=VerdictType.SUPPORTS,
            confidence=0.8,
            citations=[],
            rationale="Valid rationale with sufficient length to meet requirements",
        )
        assert assessment.verdict == VerdictType.SUPPORTS

        # Invalid verdict type should raise validation error
        with pytest.raises(ValidationError):
            # Using dict to bypass type checking
            ModelAssessment.model_validate(
                {
                    "model_name": "test-model",
                    "verdict": "invalid_verdict",
                    "confidence": 0.8,
                    "citations": [],
                    "rationale": "Valid rationale with sufficient length to meet requirements",
                }
            )


class TestVoteType:
    """Test VoteType enum"""

    @pytest.mark.unit
    def test_vote_type_values(self):
        """Test all vote type values are valid"""
        assert VoteType.AGREE == "agree"
        assert VoteType.DISAGREE == "disagree"
        assert VoteType.PASS == "pass"


class TestClaimCreate:
    """Test ClaimCreate model validation"""

    @pytest.mark.unit
    def test_valid_claim_create(self):
        """Test creating valid ClaimCreate instance"""
        claim_data = ClaimCreate(
            text="This is a valid claim statement",
            topic="test-topic",
            entities=["Q1", "Q2"],
            seed_sources=["https://example.com"],
        )

        assert claim_data.text == "This is a valid claim statement"
        assert claim_data.topic == "test-topic"
        assert claim_data.entities == ["Q1", "Q2"]
        assert claim_data.seed_sources == ["https://example.com"]

    @pytest.mark.unit
    def test_claim_create_text_validation(self):
        """Test text field validation"""
        # Text too short
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text="short", topic="test", entities=[])
        assert "at least 10 characters" in str(exc_info.value)

        # Text too long
        with pytest.raises(ValidationError) as exc_info:
            ClaimCreate(text="x" * 501, topic="test", entities=[])
        assert "at most 500 characters" in str(exc_info.value)

        # Valid length
        claim = ClaimCreate(text="x" * 50, topic="test", entities=[])
        assert len(claim.text) == 50

    @pytest.mark.unit
    def test_claim_create_topic_validation(self):
        """Test topic field validation"""
        # Topic too short
        with pytest.raises(ValidationError):
            ClaimCreate(text="Valid claim text", topic="ab", entities=[])

        # Topic too long
        with pytest.raises(ValidationError):
            ClaimCreate(text="Valid claim text", topic="x" * 101, entities=[])

        # Valid topic
        claim = ClaimCreate(text="Valid claim text", topic="valid-topic", entities=[])
        assert claim.topic == "valid-topic"

    @pytest.mark.unit
    def test_claim_create_defaults(self):
        """Test default values"""
        claim = ClaimCreate(text="Valid claim text", topic="test")
        assert claim.entities == []
        assert claim.seed_sources == []


class TestEvidence:
    """Test Evidence model validation"""

    @pytest.mark.unit
    def test_valid_evidence(self):
        """Test creating valid Evidence instance"""
        evidence = Evidence(
            url="https://example.com/article",
            publisher="Example Publisher",
            snippet="This is evidence snippet",
            provenance="manual-entry",
        )

        assert evidence.url == "https://example.com/article"
        assert evidence.publisher == "Example Publisher"
        assert evidence.snippet == "This is evidence snippet"
        assert evidence.provenance == "manual-entry"
        assert isinstance(evidence.id, UUID)
        assert isinstance(evidence.retrieved_at, datetime)
        assert isinstance(evidence.created_at, datetime)

    @pytest.mark.unit
    def test_evidence_snippet_validation(self):
        """Test snippet length validation"""
        # Snippet too long
        with pytest.raises(ValidationError):
            Evidence(
                url="https://example.com",
                publisher="Test",
                snippet="x" * 1001,  # Exceeds 1000 char limit
                provenance="test",
            )

        # Valid snippet
        evidence = Evidence(
            url="https://example.com",
            publisher="Test",
            snippet="x" * 500,
            provenance="test",
        )
        assert len(evidence.snippet) == 500

    @pytest.mark.unit
    def test_evidence_auto_fields(self):
        """Test auto-computed fields"""
        evidence = Evidence(
            url="https://EXAMPLE.COM/path/?z=2&a=1",  # URL that will be normalized
            publisher="Test",
            snippet="Test snippet",
            provenance="test",
            title="Test Title",
        )

        # Should auto-compute normalized_url and content_hash
        assert evidence.normalized_url is not None
        assert evidence.content_hash is not None
        assert evidence.normalized_url != evidence.url  # Should be normalized
        # Normalization should lowercase domain and sort query params
        assert (
            urlparse(evidence.normalized_url).hostname == "example.com"
        )  # lowercase domain
        assert "a=1&z=2" in evidence.normalized_url  # sorted params

    @pytest.mark.unit
    def test_evidence_optional_fields(self):
        """Test optional fields"""
        evidence = Evidence(
            url="https://example.com",
            publisher="Test",
            snippet="Test",
            provenance="test",
            published_at=datetime.now(timezone.utc),
            title="Test Title",
            domain="example.com",
        )

        assert evidence.published_at is not None
        assert evidence.title == "Test Title"
        assert evidence.domain == "example.com"


class TestModelAssessment:
    """Test ModelAssessment model validation"""

    @pytest.mark.unit
    def test_valid_model_assessment(self):
        """Test creating valid ModelAssessment"""
        assessment = ModelAssessment(
            model_name="gpt-4",
            verdict=VerdictType.SUPPORTS,
            confidence=0.85,
            citations=[uuid4()],
            rationale="This is a detailed rationale explaining the assessment with sufficient length",
        )

        assert assessment.model_name == "gpt-4"
        assert assessment.verdict == VerdictType.SUPPORTS
        assert assessment.confidence == 0.85
        assert len(assessment.citations) == 1
        assert isinstance(assessment.id, UUID)
        assert isinstance(assessment.created_at, datetime)

    @pytest.mark.unit
    def test_confidence_validation(self):
        """Test confidence value validation"""
        # Confidence too low
        with pytest.raises(ValidationError):
            ModelAssessment(
                model_name="test",
                verdict=VerdictType.SUPPORTS,
                confidence=-0.1,
                citations=[],
                rationale="Valid rationale with sufficient length for validation",
            )

        # Confidence too high
        with pytest.raises(ValidationError):
            ModelAssessment(
                model_name="test",
                verdict=VerdictType.SUPPORTS,
                confidence=1.1,
                citations=[],
                rationale="Valid rationale with sufficient length for validation",
            )

        # Valid confidence values
        for confidence in [0.0, 0.5, 1.0]:
            assessment = ModelAssessment(
                model_name="test",
                verdict=VerdictType.SUPPORTS,
                confidence=confidence,
                citations=[],
                rationale="Valid rationale with sufficient length for validation",
            )
            assert assessment.confidence == confidence

    @pytest.mark.unit
    def test_rationale_validation(self):
        """Test rationale length validation"""
        # Rationale too short
        with pytest.raises(ValidationError):
            ModelAssessment(
                model_name="test",
                verdict=VerdictType.SUPPORTS,
                confidence=0.8,
                citations=[],
                rationale="short",
            )

        # Rationale too long
        with pytest.raises(ValidationError):
            ModelAssessment(
                model_name="test",
                verdict=VerdictType.SUPPORTS,
                confidence=0.8,
                citations=[],
                rationale="x" * 2001,
            )

        # Valid rationale
        assessment = ModelAssessment(
            model_name="test",
            verdict=VerdictType.SUPPORTS,
            confidence=0.8,
            citations=[],
            rationale="x" * 100,  # Valid length
        )
        assert len(assessment.rationale) == 100


class TestHumanReview:
    """Test HumanReview model validation"""

    @pytest.mark.unit
    def test_valid_human_review(self):
        """Test creating valid HumanReview"""
        review = HumanReview(
            author="expert@example.com",
            verdict=VerdictType.MIXED,
            notes="Detailed expert analysis of the claim",
            signature_vc="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        )

        assert review.author == "expert@example.com"
        assert review.verdict == VerdictType.MIXED
        assert review.notes == "Detailed expert analysis of the claim"
        assert review.signature_vc is not None
        assert isinstance(review.id, UUID)
        assert isinstance(review.created_at, datetime)

    @pytest.mark.unit
    def test_human_review_notes_validation(self):
        """Test notes field validation"""
        # Notes too long
        with pytest.raises(ValidationError):
            HumanReview(
                author="expert",
                verdict=VerdictType.SUPPORTS,
                notes="x" * 2001,
                signature_vc=None,
            )

        # Valid notes
        review = HumanReview(
            author="expert",
            verdict=VerdictType.SUPPORTS,
            notes="Valid notes",
            signature_vc=None,
        )
        assert review.notes == "Valid notes"


class TestClaim:
    """Test Claim model validation"""

    @pytest.mark.unit
    def test_valid_claim(self):
        """Test creating valid Claim"""
        claim = Claim(
            text="This is a test claim", topic="test-topic", entities=["Q1", "Q2"]
        )

        assert claim.text == "This is a test claim"
        assert claim.topic == "test-topic"
        assert claim.entities == ["Q1", "Q2"]
        assert claim.evidence == []
        assert claim.model_assessments == []
        assert claim.human_reviews == []
        assert isinstance(claim.id, UUID)
        assert isinstance(claim.created_at, datetime)
        assert isinstance(claim.updated_at, datetime)

    @pytest.mark.unit
    def test_claim_with_evidence(self):
        """Test claim with evidence"""
        evidence = Evidence(
            url="https://example.com",
            publisher="Test",
            snippet="Test evidence",
            provenance="test",
        )

        claim = Claim(text="Test claim", topic="test", entities=[], evidence=[evidence])

        assert len(claim.evidence) == 1
        assert claim.evidence[0] == evidence

    @pytest.mark.unit
    def test_claim_with_assessments(self):
        """Test claim with model assessments"""
        assessment = ModelAssessment(
            model_name="test-model",
            verdict=VerdictType.SUPPORTS,
            confidence=0.8,
            citations=[],
            rationale="Test assessment with sufficient length for validation",
        )

        claim = Claim(
            text="Test claim", topic="test", entities=[], model_assessments=[assessment]
        )

        assert len(claim.model_assessments) == 1
        assert claim.model_assessments[0] == assessment


class TestConsensusStatement:
    """Test ConsensusStatement model validation"""

    @pytest.mark.unit
    def test_valid_consensus_statement(self):
        """Test creating valid ConsensusStatement"""
        statement = ConsensusStatement(
            text="Statistical methodology is important",
            topic="statistics",
            agree_count=5,
            disagree_count=2,
            pass_count=1,
        )

        assert statement.text == "Statistical methodology is important"
        assert statement.topic == "statistics"
        assert statement.agree_count == 5
        assert statement.disagree_count == 2
        assert statement.pass_count == 1
        assert isinstance(statement.id, UUID)

    @pytest.mark.unit
    def test_consensus_statement_text_validation(self):
        """Test consensus statement text validation"""
        # Text too short
        with pytest.raises(ValidationError):
            ConsensusStatement(text="short", topic="test")

        # Text too long
        with pytest.raises(ValidationError):
            ConsensusStatement(text="x" * 141, topic="test")

        # Valid text
        statement = ConsensusStatement(text="Valid statement text", topic="test")
        assert statement.text == "Valid statement text"


class TestVote:
    """Test Vote model validation"""

    @pytest.mark.unit
    def test_valid_vote(self):
        """Test creating valid Vote"""
        statement_id = uuid4()
        
        # Test with user_id
        vote1 = Vote(statement_id=statement_id, user_id="user123", vote=VoteType.AGREE)
        assert vote1.statement_id == statement_id
        assert vote1.user_id == "user123"
        assert vote1.session_id is None
        assert vote1.vote == VoteType.AGREE
        assert isinstance(vote1.id, UUID)
        assert isinstance(vote1.created_at, datetime)
        
        # Test with session_id
        vote2 = Vote(statement_id=statement_id, session_id="session456", vote=VoteType.DISAGREE)
        assert vote2.statement_id == statement_id
        assert vote2.user_id is None
        assert vote2.session_id == "session456"
        assert vote2.vote == VoteType.DISAGREE


class TestTimeWindow:
    """Test TimeWindow model validation"""

    @pytest.mark.unit
    def test_valid_time_window(self):
        """Test creating valid TimeWindow"""
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_time = datetime(2024, 12, 31, tzinfo=timezone.utc)

        window = TimeWindow(start=start_time, end=end_time)
        assert window.start == start_time
        assert window.end == end_time

    @pytest.mark.unit
    def test_time_window_defaults(self):
        """Test TimeWindow with defaults"""
        window = TimeWindow()
        assert window.start is None
        assert window.end is None


class TestModelIntegration:
    """Test integration between models"""

    @pytest.mark.unit
    def test_claim_evidence_citation_integrity(self):
        """Test that citations reference valid evidence"""
        # Create evidence
        evidence = Evidence(
            url="https://example.com",
            publisher="Test",
            snippet="Test evidence",
            provenance="test",
        )

        # Create assessment that cites the evidence
        assessment = ModelAssessment(
            model_name="test-model",
            verdict=VerdictType.SUPPORTS,
            confidence=0.8,
            citations=[evidence.id],
            rationale="Assessment citing the evidence with sufficient length for validation",
        )

        # Create claim with both
        claim = Claim(
            text="Test claim",
            topic="test",
            entities=[],
            evidence=[evidence],
            model_assessments=[assessment],
        )

        # Verify citation integrity
        cited_evidence_ids = set()
        for assessment in claim.model_assessments:
            cited_evidence_ids.update(assessment.citations)

        available_evidence_ids = {e.id for e in claim.evidence}

        # All citations should reference available evidence
        assert cited_evidence_ids.issubset(available_evidence_ids)

    @pytest.mark.unit
    def test_uuid_consistency(self):
        """Test that UUIDs are consistently generated and unique"""
        # Create multiple instances
        claims = [
            Claim(text="Test claim " + str(i), topic="test", entities=[])
            for i in range(10)
        ]

        # All should have unique UUIDs
        ids = [claim.id for claim in claims]
        assert len(set(ids)) == len(ids)  # All unique

        # All should be valid UUIDs
        for claim_id in ids:
            assert isinstance(claim_id, UUID)

    @pytest.mark.unit
    def test_datetime_consistency(self):
        """Test that datetime fields are consistently set"""
        claim = Claim(text="Test claim", topic="test", entities=[])

        # Should have creation and update times
        assert claim.created_at is not None
        assert claim.updated_at is not None
        assert isinstance(claim.created_at, datetime)
        assert isinstance(claim.updated_at, datetime)

        # Update time should be >= creation time
        assert claim.updated_at >= claim.created_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
