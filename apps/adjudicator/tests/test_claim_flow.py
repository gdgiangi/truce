"""End-to-end tests for claim evaluation flow"""

import pytest
from unittest.mock import AsyncMock, patch
from truce_adjudicator.models import Claim, Evidence, ModelAssessment, VerdictType
from truce_adjudicator.statcan.fetch_csi import fetch_crime_severity_data
from truce_adjudicator.panel.run_panel import create_mock_assessments


@pytest.fixture
def sample_claim():
    """Create a sample claim for testing"""
    return Claim(
        text="Violent crime in Canada is rising.",
        topic="canada-crime",
        entities=["Q16"]
    )


@pytest.fixture
def sample_evidence():
    """Create sample evidence"""
    return Evidence(
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3510002601",
        publisher="Statistics Canada",
        snippet="Canada's violent crime severity index in 2024 was 73.8",
        provenance="Fetched from StatCan WDS API table 35-10-0026-01"
    )


class TestClaimCreation:
    """Test claim creation and validation"""
    
    def test_claim_creation(self, sample_claim):
        """Test basic claim creation"""
        assert sample_claim.text == "Violent crime in Canada is rising."
        assert sample_claim.topic == "canada-crime"
        assert "Q16" in sample_claim.entities
        assert len(sample_claim.evidence) == 0
        assert len(sample_claim.model_assessments) == 0


class TestEvidenceFetching:
    """Test evidence fetching from StatCan"""
    
    @pytest.mark.asyncio
    async def test_fetch_crime_data_structure(self):
        """Test that StatCan fetching returns proper evidence structure"""
        evidence_list = await fetch_crime_severity_data()
        
        assert isinstance(evidence_list, list)
        assert len(evidence_list) > 0
        
        for evidence in evidence_list:
            assert isinstance(evidence, Evidence)
            assert evidence.url is not None
            assert evidence.publisher == "Statistics Canada"
            assert evidence.snippet is not None
            assert evidence.provenance is not None
    
    @pytest.mark.asyncio
    async def test_evidence_content_quality(self):
        """Test that evidence contains expected content"""
        evidence_list = await fetch_crime_severity_data()
        
        # Should have evidence about violent crime specifically
        violent_evidence = [e for e in evidence_list if "violent" in e.snippet.lower()]
        assert len(violent_evidence) > 0
        
        # Should have methodology information
        method_evidence = [e for e in evidence_list if "crime severity index" in e.snippet.lower()]
        assert len(method_evidence) > 0


class TestModelEvaluation:
    """Test AI model evaluation system"""
    
    @pytest.mark.asyncio
    async def test_mock_assessment_creation(self, sample_claim):
        """Test mock assessment creation"""
        # Add some evidence first
        evidence = Evidence(
            url="https://example.com/data",
            publisher="Test Publisher", 
            snippet="Test evidence snippet",
            provenance="Test provenance"
        )
        sample_claim.evidence.append(evidence)
        
        assessments = await create_mock_assessments(sample_claim)
        
        assert isinstance(assessments, list)
        assert len(assessments) >= 2  # Should have multiple mock models
        
        for assessment in assessments:
            assert isinstance(assessment, ModelAssessment)
            assert assessment.model_name is not None
            assert assessment.verdict in [v.value for v in VerdictType]
            assert 0.0 <= assessment.confidence <= 1.0
            assert assessment.rationale is not None
            assert len(assessment.rationale) >= 50  # Minimum rationale length


class TestDataIntegration:
    """Test integration between different components"""
    
    @pytest.mark.asyncio
    async def test_full_claim_pipeline(self, sample_claim):
        """Test complete pipeline: claim → evidence → assessment"""
        
        # Step 1: Add evidence
        evidence_list = await fetch_crime_severity_data()
        sample_claim.evidence.extend(evidence_list)
        
        assert len(sample_claim.evidence) > 0
        
        # Step 2: Create assessments
        assessments = await create_mock_assessments(sample_claim)
        sample_claim.model_assessments.extend(assessments)
        
        assert len(sample_claim.model_assessments) > 0
        
        # Step 3: Validate complete claim structure
        assert sample_claim.text is not None
        assert len(sample_claim.evidence) > 0
        assert len(sample_claim.model_assessments) > 0
        
        # Verify assessments reference evidence
        for assessment in sample_claim.model_assessments:
            if assessment.citations:
                for citation_id in assessment.citations:
                    # Should be able to find referenced evidence
                    evidence_found = any(e.id == citation_id for e in sample_claim.evidence)
                    assert evidence_found, f"Citation {citation_id} not found in evidence"


class TestDataQuality:
    """Test data quality and consistency"""
    
    @pytest.mark.asyncio
    async def test_evidence_consistency(self):
        """Test evidence data consistency"""
        evidence_list = await fetch_crime_severity_data()
        
        for evidence in evidence_list:
            # URLs should be valid format
            assert evidence.url.startswith("http")
            
            # Publisher should be consistent
            assert "Statistics Canada" in evidence.publisher
            
            # Snippets should be informative
            assert len(evidence.snippet) > 20
            
            # Provenance should explain source
            assert "StatCan" in evidence.provenance or "Statistics Canada" in evidence.provenance
    
    def test_model_assessment_consistency(self, sample_claim):
        """Test model assessment data consistency"""
        assessment = ModelAssessment(
            model_name="test-model",
            verdict=VerdictType.MIXED,
            confidence=0.75,
            citations=[],
            rationale="Test rationale that meets minimum length requirements for assessments"
        )
        
        # Confidence should be valid probability
        assert 0.0 <= assessment.confidence <= 1.0
        
        # Verdict should be valid enum value
        assert assessment.verdict in VerdictType
        
        # Rationale should be substantial
        assert len(assessment.rationale) >= 50


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_claim_flow.py -v
    pytest.main([__file__, "-v"])
