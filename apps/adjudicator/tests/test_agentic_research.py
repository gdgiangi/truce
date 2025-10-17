"""Tests for the agentic research system."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from truce_adjudicator.models import Claim, Evidence, TimeWindow
from truce_adjudicator.panel.agentic_research import (
    AgenticResearcher,
    SharedEvidencePool,
)


class TestAgenticResearcher:
    """Test the AgenticResearcher class."""

    @pytest.fixture
    def sample_claim(self):
        """Create a sample claim for testing."""
        return Claim(
            id=uuid4(),
            text="Violent crime is increasing in Canada",
            topic="crime_statistics",
            entities=["Canada", "violent crime"],
            evidence=[],
        )

    @pytest.fixture
    def researcher(self):
        """Create a researcher instance for testing."""
        return AgenticResearcher(
            agent_name="test_researcher",
            mcp_server_url="http://localhost:8000/mcp",
            max_search_turns=3,
            max_sources_per_turn=5,
        )

    @pytest.fixture
    def mock_search_result(self):
        """Mock search result from Brave API."""
        return {
            "query": "test query",
            "count": 2,
            "results": [
                {
                    "title": "Test Article 1",
                    "url": "https://example.com/article1",
                    "snippet": "This is a test snippet about the topic.",
                    "publisher": "Test Publisher",
                    "domain": "example.com",
                    "retrieved_at": datetime.now().isoformat(),
                },
                {
                    "title": "Test Article 2",
                    "url": "https://example.com/article2",
                    "snippet": "This is another test snippet with more information.",
                    "publisher": "Another Publisher",
                    "domain": "example.com",
                    "retrieved_at": datetime.now().isoformat(),
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_research_plan_creation(self, researcher, sample_claim):
        """Test research plan creation."""
        with patch("truce_adjudicator.panel.agentic_research.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            plan = await researcher._plan_research(sample_claim, mock_client)

            assert plan["original_claim"] == sample_claim.text
            assert plan["current_strategy"] == "broad_search"
            assert isinstance(plan["search_queries_used"], list)
            assert isinstance(plan["next_actions"], list)

    @pytest.mark.asyncio
    async def test_research_turn_execution(
        self, researcher, sample_claim, mock_search_result
    ):
        """Test execution of a research turn."""
        with patch("truce_adjudicator.panel.agentic_research.Client") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock the result with .data attribute
            mock_result = Mock()
            mock_result.data = mock_search_result
            mock_client.call_tool.return_value = mock_result

            research_plan = await researcher._plan_research(sample_claim, mock_client)

            # Execute first research turn
            sources = await researcher._execute_research_turn(
                sample_claim, mock_client, 0, research_plan, None
            )

            assert len(sources) == 2
            assert sources[0]["title"] == "Test Article 1"
            assert sources[0]["research_turn"] == 0
            assert sources[0]["agent"] == "test_researcher"

            # Verify the client was called
            mock_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_evidence_conversion(self, researcher, sample_claim):
        """Test conversion of sources to Evidence objects."""
        # Add mock sources to the researcher
        researcher.collected_sources = [
            {
                "title": "Test Article",
                "url": "https://example.com/test",
                "snippet": "Test snippet",
                "publisher": "Test Publisher",
                "domain": "example.com",
                "retrieved_at": datetime.now().isoformat(),
                "research_turn": 0,
                "agent": "test_researcher",
            }
        ]

        evidence_list = await researcher._convert_to_evidence(sample_claim)

        assert len(evidence_list) == 1
        assert isinstance(evidence_list[0], Evidence)
        assert evidence_list[0].title == "Test Article"
        assert evidence_list[0].url == "https://example.com/test"
        assert evidence_list[0].provenance == "test_researcher_research"

    @pytest.mark.asyncio
    async def test_time_filter_conversion(self, researcher):
        """Test time window to Brave API filter conversion."""
        # Test recent time window
        recent_window = TimeWindow(start=datetime.now().replace(hour=0))
        filter_result = researcher._get_time_filter(recent_window)
        assert filter_result in ["pd", "pw"]  # past day or week

        # Test no time window
        no_filter = researcher._get_time_filter(None)
        assert no_filter is None

        # Test empty time window
        empty_window = TimeWindow()
        no_filter2 = researcher._get_time_filter(empty_window)
        assert no_filter2 is None


class TestSharedEvidencePool:
    """Test the SharedEvidencePool class."""

    @pytest.fixture
    def evidence_pool(self):
        """Create an evidence pool for testing."""
        return SharedEvidencePool()

    @pytest.fixture
    def sample_evidence(self):
        """Create sample evidence for testing."""
        return [
            Evidence(
                id=uuid4(),
                url="https://example.com/article1",
                publisher="Test Publisher 1",
                published_at=datetime.now(),
                retrieved_at=datetime.now(),
                title="Test Article 1",
                domain="example.com",
                snippet="Test snippet 1",
                provenance="test_agent",
                normalized_url="https://example.com/article1",
                content_hash="hash1",
            ),
            Evidence(
                id=uuid4(),
                url="https://example.com/article2",
                publisher="Test Publisher 2",
                published_at=datetime.now(),
                retrieved_at=datetime.now(),
                title="Test Article 2",
                domain="example.com",
                snippet="Test snippet 2",
                provenance="test_agent",
                normalized_url="https://example.com/article2",
                content_hash="hash2",
            ),
        ]

    @pytest.mark.asyncio
    async def test_evidence_addition(self, evidence_pool, sample_evidence):
        """Test adding evidence to the pool."""
        added_count = await evidence_pool.add_evidence(sample_evidence, "test_agent")

        assert added_count == 2
        assert len(evidence_pool.evidence_pool) == 2
        assert len(evidence_pool.source_hashes) == 2

    @pytest.mark.asyncio
    async def test_evidence_deduplication(self, evidence_pool, sample_evidence):
        """Test deduplication of evidence by URL."""
        # Add evidence first time
        added_count1 = await evidence_pool.add_evidence(sample_evidence, "agent1")
        assert added_count1 == 2

        # Try to add same evidence again (should be deduplicated)
        added_count2 = await evidence_pool.add_evidence(sample_evidence, "agent2")
        assert added_count2 == 0
        assert len(evidence_pool.evidence_pool) == 2  # Still only 2 items

    def test_evidence_summary(self, evidence_pool):
        """Test evidence summary generation."""
        # Add some mock evidence directly
        evidence_pool.evidence_pool = [
            Evidence(
                id=uuid4(),
                url="https://cbc.ca/news",
                publisher="CBC News",
                published_at=datetime.now(),
                retrieved_at=datetime.now(),
                title="News Article",
                domain="cbc.ca",
                snippet="News content",
                provenance="agent1",
                normalized_url="https://cbc.ca/news",
                content_hash="hash1",
            ),
            Evidence(
                id=uuid4(),
                url="https://statcan.gc.ca/data",
                publisher="Statistics Canada",
                published_at=datetime.now(),
                retrieved_at=datetime.now(),
                title="Statistical Data",
                domain="statcan.gc.ca",
                snippet="Statistical content",
                provenance="agent2",
                normalized_url="https://statcan.gc.ca/data",
                content_hash="hash2",
            ),
        ]

        summary = evidence_pool.get_evidence_summary()

        assert summary["total_evidence"] == 2
        assert summary["unique_domains"] == 2
        assert summary["unique_publishers"] == 2
        assert "cbc.ca" in summary["domains"]
        assert "statcan.gc.ca" in summary["domains"]
        assert "CBC News" in summary["publishers"]
        assert "Statistics Canada" in summary["publishers"]


@pytest.mark.asyncio
async def test_full_research_flow_mock():
    """Test the full research flow with mocked dependencies."""
    claim = Claim(
        id=uuid4(),
        text="Test claim for research",
        topic="test_topic",
        entities=["test"],
        evidence=[],
    )

    researcher = AgenticResearcher(
        agent_name="mock_researcher",
        mcp_server_url="http://localhost:8000/mcp",
        max_search_turns=2,
        max_sources_per_turn=3,
    )

    mock_results = [
        {
            "query": "Test claim for research",
            "count": 2,
            "results": [
                {
                    "title": "Research Article 1",
                    "url": "https://research.com/article1",
                    "snippet": "Research findings about the test claim.",
                    "publisher": "Research Institute",
                    "domain": "research.com",
                    "retrieved_at": datetime.now().isoformat(),
                },
                {
                    "title": "Analysis Report",
                    "url": "https://analysis.com/report",
                    "snippet": "Detailed analysis of the test claim data.",
                    "publisher": "Analysis Group",
                    "domain": "analysis.com",
                    "retrieved_at": datetime.now().isoformat(),
                },
            ],
        }
    ]

    with patch("truce_adjudicator.panel.agentic_research.Client") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock the result with .data attribute
        mock_result = Mock()
        mock_result.data = mock_results[0]
        mock_client.call_tool.return_value = mock_result

        # Mock context manager behavior
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        evidence_list = await researcher.conduct_research(claim)

        assert len(evidence_list) >= 2  # Should have some evidence from research
        assert all(isinstance(e, Evidence) for e in evidence_list)
        assert len(researcher.research_log) >= 1  # Should have logged research actions
