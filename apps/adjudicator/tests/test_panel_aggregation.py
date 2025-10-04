"""Tests for panel prompt normalization, provider stubs, and aggregation."""

from datetime import datetime

import pytest

from truce_adjudicator.models import ArgumentWithEvidence, Claim, Evidence, PanelModelVerdict, PanelVerdict, TimeWindow
from truce_adjudicator.panel.run_panel import (
    _ensure_payload_dict,
    aggregate_panel,
    build_normalized_prompt,
    panel_result_to_assessments,
    run_panel_evaluation,
)


@pytest.fixture
def claim_with_evidence() -> Claim:
    claim = Claim(
        text="Test claim about crime statistics",
        topic="crime",
        entities=[],
    )
    claim.evidence.append(
        Evidence(
            url="https://example.com/article",
            publisher="Example Publisher",
            snippet="Violent crime increased by 10% last year according to the national report.",
            provenance="unit-test",
            published_at=datetime(2024, 1, 15),
        )
    )
    claim.evidence.append(
        Evidence(
            url="https://example.com/analysis",
            publisher="Another Publisher",
            snippet="Independent analysis shows mixed results across regions for violent crime trends.",
            provenance="unit-test",
            published_at=datetime(2023, 8, 2),
        )
    )
    return claim


def test_build_normalized_prompt_contains_expected_fields(claim_with_evidence: Claim) -> None:
    window = TimeWindow(start=datetime(2023, 1, 1), end=datetime(2024, 12, 31))
    prompt = build_normalized_prompt(claim_with_evidence, window)

    assert prompt["schema"] == "truce.panel.v1"
    assert prompt["claim"]["text"] == claim_with_evidence.text
    assert prompt["time_window"]["start"].startswith("2023-01-01")
    assert prompt["time_window"]["end"].startswith("2024-12-31")
    assert len(prompt["evidence"]) == 2
    assert prompt["evidence"][0]["id"] == str(claim_with_evidence.evidence[1].id)


@pytest.mark.asyncio
async def test_run_panel_evaluation_stub_majority(claim_with_evidence: Claim) -> None:
    panel = await run_panel_evaluation(
        claim_with_evidence,
        ["gpt-4o", "grok-3", "gemini-2.0-flash-exp", "claude-sonnet-4-20250514"],
        enable_agentic_research=False,
    )

    assert len(panel.models) == 4
    assert panel.summary.model_count == 4
    # Check that we have both approval and refusal arguments
    for model in panel.models:
        assert model.approval_argument is not None
        assert model.refusal_argument is not None
        assert 0.0 <= model.approval_argument.confidence <= 1.0
        assert 0.0 <= model.refusal_argument.confidence <= 1.0
    # Check aggregate confidence scores
    assert 0.0 <= panel.summary.support_confidence <= 1.0
    assert 0.0 <= panel.summary.refute_confidence <= 1.0


def test_aggregate_panel_balanced_returns_mixed() -> None:
    models = [
        PanelModelVerdict(
            provider_id="openai:gpt-4o",
            model="gpt-4o",
            approval_argument=ArgumentWithEvidence(
                argument="Supports due to recent statistics describing increased incidents over time.",
                evidence_ids=[],
                confidence=0.5,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument="Refutes because of methodology concerns in data collection.",
                evidence_ids=[],
                confidence=0.5,
            ),
        ),
        PanelModelVerdict(
            provider_id="xai:grok-3",
            model="grok-3",
            approval_argument=ArgumentWithEvidence(
                argument="Some evidence points to increases in specific categories.",
                evidence_ids=[],
                confidence=0.5,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument="Overall trends show decline across multiple regions.",
                evidence_ids=[],
                confidence=0.5,
            ),
        ),
    ]

    summary = aggregate_panel(models)
    assert summary.model_count == 2
    # When balanced, should be MIXED
    assert summary.support_confidence == 0.5
    assert summary.refute_confidence == 0.5
    assert summary.verdict == PanelVerdict.MIXED


@pytest.mark.asyncio
async def test_panel_result_to_assessments_maps_verdicts(claim_with_evidence: Claim) -> None:
    panel = await run_panel_evaluation(
        claim_with_evidence, 
        ["gpt-4o", "claude-sonnet-4-20250514"],
        enable_agentic_research=False,
    )
    assessments = panel_result_to_assessments(panel)

    assert len(assessments) == 2
    assert all(assessment.rationale for assessment in assessments)
    # Check that verdicts are derived from the stronger argument
    for assessment in assessments:
        assert assessment.verdict.value in ["supports", "refutes", "mixed", "uncertain"]


def test_aggregate_panel_strong_support() -> None:
    """Test that strong approval confidence leads to TRUE verdict."""
    models = [
        PanelModelVerdict(
            provider_id="openai:gpt-4o",
            model="gpt-4o",
            approval_argument=ArgumentWithEvidence(
                argument="Strong evidence supports the claim based on comprehensive data analysis.",
                evidence_ids=[],
                confidence=0.85,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument="Some concerns exist but are minor compared to supporting evidence.",
                evidence_ids=[],
                confidence=0.15,
            ),
        ),
        PanelModelVerdict(
            provider_id="anthropic:claude",
            model="claude-sonnet-4",
            approval_argument=ArgumentWithEvidence(
                argument="Multiple independent sources confirm the claim's accuracy.",
                evidence_ids=[],
                confidence=0.90,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument="Limited counter-evidence found during analysis.",
                evidence_ids=[],
                confidence=0.10,
            ),
        ),
    ]

    summary = aggregate_panel(models)
    assert summary.model_count == 2
    assert summary.support_confidence > 0.8  # Average of 0.85 and 0.90
    assert summary.refute_confidence < 0.2
    assert summary.verdict == PanelVerdict.TRUE


def test_aggregate_panel_strong_refute() -> None:
    """Test that strong refusal confidence leads to FALSE verdict."""
    models = [
        PanelModelVerdict(
            provider_id="xai:grok-3",
            model="grok-3",
            approval_argument=ArgumentWithEvidence(
                argument="Limited supporting evidence found.",
                evidence_ids=[],
                confidence=0.20,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument="Comprehensive evidence refutes the claim across multiple sources.",
                evidence_ids=[],
                confidence=0.80,
            ),
        ),
        PanelModelVerdict(
            provider_id="google:gemini",
            model="gemini-2.0",
            approval_argument=ArgumentWithEvidence(
                argument="Some weak indicators might support but are inconclusive.",
                evidence_ids=[],
                confidence=0.15,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument="Strong evidence contradicts the claim's central assertions.",
                evidence_ids=[],
                confidence=0.85,
            ),
        ),
    ]

    summary = aggregate_panel(models)
    assert summary.model_count == 2
    assert summary.support_confidence < 0.2
    assert summary.refute_confidence > 0.8  # Average of 0.80 and 0.85
    assert summary.verdict == PanelVerdict.FALSE


def test_ensure_payload_dict_extracts_json_block() -> None:
    content = """Provider output -> {
        "provider_id": "test:model",
        "approval_argument": {
            "argument": "Test approval argument with sufficient length to pass validation.",
            "evidence_ids": [],
            "confidence": 0.66
        },
        "refusal_argument": {
            "argument": "Test refusal argument with sufficient length to pass validation.",
            "evidence_ids": [],
            "confidence": 0.34
        }
    }"""
    payload = _ensure_payload_dict(content)
    assert payload["approval_argument"]["confidence"] == 0.66
    assert payload["refusal_argument"]["confidence"] == 0.34
