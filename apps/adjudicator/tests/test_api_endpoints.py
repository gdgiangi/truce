"""Comprehensive API endpoint tests for Truce adjudicator"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from truce_adjudicator import search_index
from truce_adjudicator.main import app, claims_db, statements_db, votes_db
from truce_adjudicator.models import (
    Claim,
    ClaimCreate,
    ConsensusStatement,
    Evidence,
    ModelAssessment,
    TimeWindow,
    VerdictType,
    VoteType,
)
from truce_adjudicator.verification import reset_cache


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state between tests"""
    claims_db.clear()
    statements_db.clear()
    votes_db.clear()
    search_index.reset()
    reset_cache()
    yield
    claims_db.clear()
    statements_db.clear()
    votes_db.clear()
    search_index.reset()
    reset_cache()


@pytest.fixture
def sample_claim_data():
    """Sample claim creation data"""
    return {
        "text": "Violent crime in Canada is rising significantly",
        "topic": "canada-crime",
        "entities": ["Q16"],
        "seed_sources": ["https://example.com/source1"],
    }


@pytest.fixture
def sample_evidence():
    """Sample evidence for testing"""
    return Evidence(
        url="https://statcan.gc.ca/test",
        publisher="Statistics Canada",
        snippet="Crime statistics show...",
        provenance="test-fixture",
    )


class TestRootEndpoint:
    """Test the root endpoint"""

    @pytest.mark.api
    def test_root_endpoint(self, client):
        """Test root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert "timestamp" in data


class TestClaimsEndpoints:
    """Test claim-related endpoints"""

    @pytest.mark.api
    def test_create_claim_success(self, client, sample_claim_data):
        """Test successful claim creation"""
        response = client.post("/claims", json=sample_claim_data)
        assert response.status_code == 200

        data = response.json()
        assert "slug" in data
        assert "claim" in data
        claim_data = data["claim"]
        assert claim_data["text"] == sample_claim_data["text"]
        assert claim_data["topic"] == sample_claim_data["topic"]
        assert claim_data["entities"] == sample_claim_data["entities"]

        # Verify claim is stored
        slug = data["slug"]
        assert slug in claims_db

    @pytest.mark.api
    def test_create_claim_validation_errors(self, client):
        """Test claim creation validation"""
        # Test missing required fields
        response = client.post("/claims", json={})
        assert response.status_code == 422

        # Test text too short
        response = client.post(
            "/claims", json={"text": "short", "topic": "test", "entities": []}
        )
        assert response.status_code == 422

        # Test text too long
        response = client.post(
            "/claims",
            json={
                "text": "x" * 501,  # Exceeds 500 char limit
                "topic": "test",
                "entities": [],
            },
        )
        assert response.status_code == 422

    @pytest.mark.api
    def test_get_claim_success(self, client, sample_claim_data):
        """Test getting an existing claim"""
        # First create a claim
        create_response = client.post("/claims", json=sample_claim_data)
        slug = create_response.json()["slug"]

        # Then get it
        response = client.get(f"/claims/{slug}")
        assert response.status_code == 200

        data = response.json()
        assert data["slug"] == slug
        claim_data = data["claim"]
        assert claim_data["text"] == sample_claim_data["text"]
        assert claim_data["topic"] == sample_claim_data["topic"]

    @pytest.mark.api
    def test_get_claim_not_found(self, client):
        """Test getting a non-existent claim"""
        response = client.get("/claims/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.api
    def test_add_statcan_evidence(self, client, sample_claim_data):
        """Test adding StatCan evidence to a claim"""
        # Create claim first
        create_response = client.post("/claims", json=sample_claim_data)
        slug = create_response.json()["slug"]

        # Mock the StatCan API
        with patch(
            "truce_adjudicator.statcan.fetch_csi.fetch_crime_severity_data"
        ) as mock_fetch:
            mock_evidence = Evidence(
                url="https://statcan.gc.ca/test",
                publisher="Statistics Canada",
                snippet="Test evidence snippet",
                provenance="statcan-api",
            )
            mock_fetch.return_value = [mock_evidence]

            response = client.post(f"/claims/{slug}/evidence:statcan")
            assert response.status_code == 200

            # Verify evidence was added
            claim_response = client.get(f"/claims/{slug}")
            claim_data = claim_response.json()["claim"]
            assert len(claim_data["evidence"]) > 0
            assert any(
                "Statistics Canada" in e["publisher"] for e in claim_data["evidence"]
            )


class TestSearchEndpoint:
    """Test search functionality"""

    @pytest.mark.api
    def test_search_empty_database(self, client):
        """Test search with no claims in database"""
        response = client.get("/search?q=test")
        assert response.status_code == 200

        data = response.json()
        assert "claims" in data
        assert "evidence" in data
        assert len(data["claims"]) == 0
        assert len(data["evidence"]) == 0

    @pytest.mark.api
    def test_search_with_results(self, client, sample_claim_data):
        """Test search returning results"""
        # Create a claim first
        client.post("/claims", json=sample_claim_data)

        # Search for it
        response = client.get("/search?q=violent crime canada")
        assert response.status_code == 200

        data = response.json()
        assert len(data["claims"]) > 0

        # Check result structure
        result = data["claims"][0]
        assert "slug" in result
        assert "text" in result
        assert "score" in result

    @pytest.mark.api
    def test_search_no_query(self, client):
        """Test search without query parameter"""
        response = client.get("/search")
        assert response.status_code == 422


class TestVerificationEndpoint:
    """Test claim verification functionality"""

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_verify_claim_success(self, client, sample_claim_data):
        """Test successful claim verification"""
        # Create claim with evidence
        create_response = client.post("/claims", json=sample_claim_data)
        slug = create_response.json()["slug"]

        # Add some evidence first
        claim = claims_db[slug]
        evidence = Evidence(
            url="https://test.com/evidence",
            publisher="Test Publisher",
            snippet="Test evidence supporting the claim",
            provenance="test-setup",
        )
        claim.evidence.append(evidence)

        # Mock the panel assessment
        with patch(
            "truce_adjudicator.panel.run_panel.create_mock_assessments"
        ) as mock_panel:
            mock_assessment = ModelAssessment(
                model_name="test-model",
                verdict=VerdictType.SUPPORTS,
                confidence=0.85,
                citations=[evidence.id],
                rationale="Test rationale with sufficient length to pass validation checks",
            )
            mock_panel.return_value = [mock_assessment]

            response = client.post(f"/claims/{slug}/verify")
            assert response.status_code == 200

            data = response.json()
            assert "verification_id" in data
            assert "evidence_ids" in data
            assert "assessment_ids" in data
            assert data["cached"] is False

    @pytest.mark.api
    def test_verify_claim_not_found(self, client):
        """Test verifying non-existent claim"""
        response = client.post("/claims/nonexistent/verify")
        assert response.status_code == 404

    @pytest.mark.api
    def test_verify_claim_with_time_window(self, client, sample_claim_data):
        """Test verification with time window filter"""
        create_response = client.post("/claims", json=sample_claim_data)
        slug = create_response.json()["slug"]

        # Add evidence with different timestamps
        claim = claims_db[slug]
        now = datetime.now()

        recent_evidence = Evidence(
            url="https://recent.com",
            publisher="Recent Publisher",
            published_at=now - timedelta(days=1),
            snippet="Recent evidence",
            provenance="test",
        )
        old_evidence = Evidence(
            url="https://old.com",
            publisher="Old Publisher",
            published_at=now - timedelta(days=365),
            snippet="Old evidence",
            provenance="test",
        )
        claim.evidence.extend([recent_evidence, old_evidence])

        # Verify with time window that should only include recent evidence
        time_start = (now - timedelta(days=7)).isoformat()
        time_end = now.isoformat()

        response = client.post(
            f"/claims/{slug}/verify",
            params={"time_start": time_start, "time_end": time_end},
        )
        assert response.status_code == 200

        data = response.json()
        # Should only have recent evidence
        assert str(recent_evidence.id) in data["evidence_ids"]
        assert str(old_evidence.id) not in data["evidence_ids"]


class TestConsensusEndpoints:
    """Test consensus-related endpoints"""

    @pytest.mark.api
    def test_create_consensus_statement(self, client):
        """Test creating consensus statements"""
        statement_data = {
            "text": "Crime statistics methodology is important for accurate interpretation",
            "topic": "canada-crime",
        }

        response = client.post(
            "/consensus/canada-crime/statements", json=statement_data
        )
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["text"] == statement_data["text"]
        assert data["topic"] == statement_data["topic"]
        assert data["agree_count"] == 0
        assert data["disagree_count"] == 0
        assert data["pass_count"] == 0

    @pytest.mark.api
    def test_vote_on_statement(self, client):
        """Test voting on consensus statements"""
        # Create statement first
        statement_data = {
            "text": "Statistical methodology matters",
            "topic": "canada-crime",
        }
        create_response = client.post(
            "/consensus/canada-crime/statements", json=statement_data
        )
        statement_id = create_response.json()["id"]

        # Vote on it
        vote_data = {
            "statement_id": statement_id,
            "vote": "agree",
            "participant_id": "test-user-1",
        }

        response = client.post("/consensus/canada-crime/votes", json=vote_data)
        assert response.status_code == 200

        data = response.json()
        assert data["vote"] == "agree"
        assert data["statement_id"] == statement_id

    @pytest.mark.api
    def test_get_consensus_summary(self, client):
        """Test getting consensus summary"""
        # Create some statements and votes
        for i in range(3):
            statement_data = {"text": f"Test statement {i}", "topic": "test-topic"}
            create_response = client.post(
                "/consensus/test-topic/statements", json=statement_data
            )
            statement_id = create_response.json()["id"]

            # Add some votes
            vote_data = {
                "statement_id": statement_id,
                "vote": "agree" if i % 2 == 0 else "disagree",
                "participant_id": f"user-{i}",
            }
            client.post("/consensus/test-topic/votes", json=vote_data)

        response = client.get("/consensus/test-topic/summary")
        assert response.status_code == 200

        data = response.json()
        assert "topic" in data
        assert "statements" in data
        assert "total_votes" in data
        assert len(data["statements"]) == 3


class TestReplayEndpoint:
    """Test replay functionality"""

    @pytest.mark.api
    def test_get_replay_data(self, client, sample_claim_data):
        """Test getting replay data for a claim"""
        # Create and verify a claim to generate replay data
        create_response = client.post("/claims", json=sample_claim_data)
        slug = create_response.json()["slug"]

        # Add evidence and verify to create replay data
        claim = claims_db[slug]
        evidence = Evidence(
            url="https://test.com",
            publisher="Test",
            snippet="Test evidence",
            provenance="test",
        )
        claim.evidence.append(evidence)

        # Verify the claim
        with patch(
            "truce_adjudicator.panel.run_panel.create_mock_assessments"
        ) as mock_panel:
            mock_assessment = ModelAssessment(
                model_name="test-model",
                verdict=VerdictType.SUPPORTS,
                confidence=0.8,
                citations=[evidence.id],
                rationale="Test rationale with sufficient length for validation requirements",
            )
            mock_panel.return_value = [mock_assessment]
            client.post(f"/claims/{slug}/verify")

        # Get replay data
        response = client.get(f"/replay/{slug}.jsonl")
        assert response.status_code == 200

        # Should return JSONL format
        content = response.content.decode()
        lines = content.strip().split("\n")
        assert len(lines) > 0

        # Each line should be valid JSON
        for line in lines:
            json.loads(line)  # Should not raise exception

    @pytest.mark.api
    def test_get_replay_data_not_found(self, client):
        """Test getting replay data for non-existent claim"""
        response = client.get("/replay/nonexistent.jsonl")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling across endpoints"""

    @pytest.mark.api
    def test_invalid_json_body(self, client):
        """Test sending invalid JSON"""
        response = client.post(
            "/claims", data="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    @pytest.mark.api
    def test_method_not_allowed(self, client):
        """Test using wrong HTTP method"""
        response = client.put("/claims")
        assert response.status_code == 405

    @pytest.mark.api
    def test_large_request_body(self, client):
        """Test very large request body"""
        large_data = {
            "text": "x" * 1000,  # Very large text
            "topic": "y" * 200,  # Very large topic
            "entities": ["Q" + str(i) for i in range(1000)],  # Many entities
        }

        response = client.post("/claims", json=large_data)
        # Should fail validation
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
