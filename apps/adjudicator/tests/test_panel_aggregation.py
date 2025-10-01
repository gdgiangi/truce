"""Tests for panel prompt normalization, provider stubs, and aggregation."""

from datetime import datetime

import pytest

from truce_adjudicator.models import Claim, Evidence, PanelModelVerdict, PanelVerdict, TimeWindow
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
        ["gpt-5", "grok-beta", "gemini-2.0-flash", "sonnet-stub"],
    )

    assert len(panel.models) == 4
    assert panel.summary.model_count == 4
    assert panel.summary.verdict == PanelVerdict.TRUE
    assert panel.summary.distribution["true"] == 2
    assert any(model.citations for model in panel.models)


def test_aggregate_panel_tie_returns_mixed() -> None:
    models = [
        PanelModelVerdict(
            provider_id="openai:gpt-5",
            model="gpt-5",
            verdict=PanelVerdict.TRUE,
            confidence=0.8,
            rationale="Supports due to recent statistics describing increased incidents over time.",
            citations=[],
        ),
        PanelModelVerdict(
            provider_id="xai:grok-beta",
            model="grok-beta",
            verdict=PanelVerdict.FALSE,
            confidence=0.8,
            rationale="Refutes because broader dataset shows long-term decline across regions.",
            citations=[],
        ),
    ]

    summary = aggregate_panel(models)
    assert summary.verdict == PanelVerdict.MIXED
    assert summary.confidence == 0.0


@pytest.mark.asyncio
async def test_panel_result_to_assessments_maps_verdicts(claim_with_evidence: Claim) -> None:
    panel = await run_panel_evaluation(claim_with_evidence, ["gpt-5", "sonnet-stub"])
    assessments = panel_result_to_assessments(panel)

    assert len(assessments) == 2
    assert all(assessment.rationale for assessment in assessments)
    verdicts = {assessment.verdict.value for assessment in assessments}
    assert "supports" in verdicts


def test_ensure_payload_dict_extracts_json_block() -> None:
    content = "Provider output -> {\"verdict\":\"true\",\"confidence\":0.66,\"citations\":[]}"
    payload = _ensure_payload_dict(content)
    assert payload["verdict"] == "true"
    assert payload["confidence"] == 0.66
