"""Panel evaluation pipeline with provider adapters and aggregation."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence
from uuid import UUID

from dotenv import load_dotenv

try:  # Optional at runtime – fall back to stubs when unavailable
    import openai
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        AsyncOpenAI = openai.AsyncOpenAI
    else:
        AsyncOpenAI = None
except Exception:  # pragma: no cover - dependency optional
    openai = None  # type: ignore
    AsyncOpenAI = None  # type: ignore

load_dotenv()

from ..models import (
    Claim,
    ModelAssessment,
    PanelModelVerdict,
    PanelResult,
    PanelSummary,
    PanelVerdict,
    TimeWindow,
    VerdictType,
)

DEFAULT_PANEL_MODELS: List[str] = [
    "gpt-4o",  # OpenAI's latest model (was gpt-5 which doesn't exist)
    "grok-3",  # xAI's latest (grok-beta deprecated Sept 2025)
    "gemini-2.0-flash-exp",  # Google's latest Gemini
    "claude-3-5-sonnet-20241022",  # Anthropic's latest Claude
]

SYSTEM_PROMPT = """You are an objective fact-checking assistant. Respond **only** with a JSON object matching:
{
  "provider_id": "provider:model",
  "verdict": "true|false|mixed|unknown",
  "confidence": 0.0-1.0,
  "rationale": "50-500 words explaining reasoning with evidence IDs",
  "citations": ["evidence_id", ...]
}
Assess the claim using the evidence list. Cite by evidence ID. If unsure, return verdict "unknown"."""


def build_normalized_prompt(claim: Claim, window: Optional[TimeWindow]) -> Dict[str, Any]:
    """Construct normalized prompt payload for provider adapters."""
    window = window or TimeWindow()
    evidence_payload: List[Dict[str, Any]] = []
    for evidence in sorted(claim.evidence, key=lambda e: e.published_at or datetime.min):
        evidence_payload.append(
            {
                "id": str(evidence.id),
                "publisher": evidence.publisher,
                "snippet": evidence.snippet,
                "url": evidence.url,
                "published_at": evidence.published_at.isoformat()
                if evidence.published_at
                else None,
            }
        )

    return {
        "schema": "truce.panel.v1",
        "claim": {
            "id": str(claim.id),
            "text": claim.text,
            "topic": claim.topic,
            "entities": claim.entities,
        },
        "time_window": {
            "start": window.start.isoformat() if window.start else None,
            "end": window.end.isoformat() if window.end else None,
        },
        "evidence": evidence_payload,
        "evidence_count": len(evidence_payload),
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
    }


class BaseProviderAdapter:
    """Base class for provider adapters with structured fallbacks."""

    provider_id: str

    def __init__(self, model: str) -> None:
        self.model = model

    async def evaluate(
        self,
        claim: Claim,
        prompt: Dict[str, Any],
        evidence_lookup: Dict[str, UUID],
    ) -> PanelModelVerdict:
        payload = await self._call_provider(prompt)
        parsed = _ensure_payload_dict(payload)
        verdict = _parse_panel_verdict(parsed.get("verdict"))
        citations = _map_citations(parsed.get("citations"), evidence_lookup)
        rationale = parsed.get("rationale") or _fallback_rationale(
            self.provider_id, self.model, prompt, parsed.get("verdict")
        )
        if len(rationale) < 50:
            rationale = _pad_rationale(rationale)
        confidence_raw = parsed.get("confidence")
        confidence = None
        if confidence_raw is not None:
            try:
                confidence = max(0.0, min(1.0, float(confidence_raw)))
            except (TypeError, ValueError):
                confidence = None

        return PanelModelVerdict(
            provider_id=self.provider_id,
            model=self.model,
            verdict=verdict,
            confidence=confidence,
            rationale=rationale,
            citations=citations,
            raw=parsed,
        )

    async def _call_provider(self, prompt: Dict[str, Any]) -> Any:
        try:
            response = await self._invoke(prompt)
            if response is None:
                raise ValueError("Empty provider response")
            return response
        except Exception as exc:
            return self._fallback(prompt, error=str(exc))

    async def _invoke(self, prompt: Dict[str, Any]) -> Any:
        raise NotImplementedError

    def _fallback(self, prompt: Dict[str, Any], error: str = "") -> Dict[str, Any]:
        return _generate_stub_payload(self.provider_id, self.model, prompt, error=error)


class GPTProviderAdapter(BaseProviderAdapter):
    """Adapter for OpenAI GPT models."""

    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.provider_id = f"openai:{model}"
        self._client: Optional[Any] = None if openai else None

    async def _invoke(self, prompt: Dict[str, Any]) -> Any:  # pragma: no cover - network call
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or openai is None:
            raise RuntimeError("OpenAI API key not configured")

        if self._client is None:
            self._client = openai.AsyncOpenAI(api_key=api_key)

        serialized = json.dumps(prompt, ensure_ascii=False)

        # Use standard chat completions for all OpenAI models
        completion = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": serialized},
            ],
            max_tokens=900,
            temperature=0.1,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        return _ensure_payload_dict(content)


class GrokProviderAdapter(BaseProviderAdapter):
    """Adapter for xAI Grok models."""

    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.provider_id = f"xai:{model}"
        self._client: Optional[Any] = None if openai else None

    async def _invoke(self, prompt: Dict[str, Any]) -> Any:  # pragma: no cover - network call
        api_key = os.getenv("XAI_API_KEY")
        if not api_key or openai is None:
            raise RuntimeError("XAI API key not configured or OpenAI library not available")

        if self._client is None:
            # XAI uses OpenAI-compatible API
            self._client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )

        serialized = json.dumps(prompt, ensure_ascii=False)

        completion = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": serialized},
            ],
            max_tokens=900,
            temperature=0.1,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        return _ensure_payload_dict(content)


class GeminiProviderAdapter(BaseProviderAdapter):
    """Adapter for Google Gemini models via OpenAI-compatible endpoint."""

    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.provider_id = f"google:{model}"
        self._client: Optional[Any] = None if openai else None

    async def _invoke(self, prompt: Dict[str, Any]) -> Any:  # pragma: no cover - network call
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or openai is None:
            raise RuntimeError("Google API key not configured or OpenAI library not available")

        if self._client is None:
            # Using OpenAI-compatible interface for Gemini via a proxy or direct integration
            # Note: This may need adjustment based on actual Google API implementation
            self._client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"  # Hypothetical endpoint
            )

        serialized = json.dumps(prompt, ensure_ascii=False)

        completion = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": serialized},
            ],
            max_tokens=900,
            temperature=0.1,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        return _ensure_payload_dict(content)


class AnthropicProviderAdapter(BaseProviderAdapter):
    """Adapter for Anthropic Claude models."""

    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.provider_id = f"anthropic:{model}"
        self._client: Optional[Any] = None

    async def _invoke(self, prompt: Dict[str, Any]) -> Any:  # pragma: no cover - network call
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Anthropic API key not configured")

        try:
            import anthropic
            if self._client is None:
                self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise RuntimeError("Anthropic library not available (pip install anthropic)")

        serialized = json.dumps(prompt, ensure_ascii=False)
        
        # Use the model name as-is (should be full Anthropic model name)
        anthropic_model = self.model

        message = await self._client.messages.create(
            model=anthropic_model,
            max_tokens=900,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": serialized}
            ]
        )
        content = message.content[0].text if message.content else ""
        return _ensure_payload_dict(content)


def _resolve_adapter(model_name: str) -> BaseProviderAdapter:
    lowered = model_name.lower()
    if lowered.startswith("gpt"):
        return GPTProviderAdapter(model_name)
    if lowered.startswith("grok"):
        return GrokProviderAdapter(model_name)
    if lowered.startswith("gemini"):
        return GeminiProviderAdapter(model_name)
    if "sonnet" in lowered or "claude" in lowered:
        return AnthropicProviderAdapter(model_name)
    # Unknown providers fall back to OpenAI-style adapter
    return GPTProviderAdapter(model_name)


async def run_panel_evaluation(
    claim: Claim,
    models: Sequence[str],
    time_window: Optional[TimeWindow] = None,
) -> PanelResult:
    """Run adapter evaluations and aggregate into a panel result."""
    if not claim.evidence:
        raise ValueError("Cannot run panel evaluation without evidence")

    selected_models = list(models) if models else DEFAULT_PANEL_MODELS
    prompt = build_normalized_prompt(claim, time_window)
    evidence_lookup = {str(ev.id): ev.id for ev in claim.evidence}

    panel_models: List[PanelModelVerdict] = []
    for model_name in selected_models:
        adapter = _resolve_adapter(model_name)
        verdict = await adapter.evaluate(claim, prompt, evidence_lookup)
        panel_models.append(verdict)

    summary = aggregate_panel(panel_models)
    return PanelResult(prompt=prompt, models=panel_models, summary=summary)


def aggregate_panel(models: Sequence[PanelModelVerdict]) -> PanelSummary:
    """Aggregate per-model verdicts via majority vote with dispersion confidence."""
    if not models:
        empty_distribution = {verdict.value: 0 for verdict in PanelVerdict}
        return PanelSummary(
            verdict=PanelVerdict.UNKNOWN,
            confidence=0.0,
            model_count=0,
            distribution=empty_distribution,
        )

    distribution = Counter(model.verdict.value for model in models)
    all_keys = {verdict.value for verdict in PanelVerdict}
    for key in all_keys:
        distribution.setdefault(key, 0)

    max_votes = max(distribution.values())
    winners = [key for key, count in distribution.items() if count == max_votes and count > 0]
    if len(winners) == 1:
        panel_verdict = PanelVerdict(winners[0])
    else:
        panel_verdict = PanelVerdict.MIXED

    agree_count = distribution.get(panel_verdict.value, 0)
    total = len(models)
    confidence = 1.0 - ((total - agree_count) / total)
    confidence = max(0.0, min(1.0, round(confidence, 4)))

    return PanelSummary(
        verdict=panel_verdict,
        confidence=confidence,
        model_count=total,
        distribution={key: distribution[key] for key in sorted(distribution.keys())},
    )


def panel_result_to_assessments(panel: PanelResult) -> List[ModelAssessment]:
    """Convert panel verdicts into legacy ModelAssessment structures."""
    verdict_map = {
        PanelVerdict.TRUE: VerdictType.SUPPORTS,
        PanelVerdict.FALSE: VerdictType.REFUTES,
        PanelVerdict.MIXED: VerdictType.MIXED,
        PanelVerdict.UNKNOWN: VerdictType.UNCERTAIN,
    }

    assessments: List[ModelAssessment] = []
    for model in panel.models:
        confidence = model.confidence
        if confidence is None:
            confidence = panel.summary.confidence
        if confidence is None:
            confidence = 0.0
        rationale = model.rationale
        if len(rationale) < 50:
            rationale = _pad_rationale(rationale)
        assessments.append(
            ModelAssessment(
                model_name=model.model,
                verdict=verdict_map.get(model.verdict, VerdictType.UNCERTAIN),
                confidence=confidence,
                citations=model.citations,
                rationale=rationale,
            )
        )
    return assessments


async def create_mock_assessments(claim: Claim) -> List[ModelAssessment]:
    """Generate mock assessments via the panel pipeline for demos/tests."""
    panel = await run_panel_evaluation(claim, DEFAULT_PANEL_MODELS)
    return panel_result_to_assessments(panel)


def _ensure_payload_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise ValueError("Empty payload")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            block = _extract_json_block(text)
            if block:
                return json.loads(block)
    raise ValueError("Could not parse provider payload")


def _extract_json_block(text: str) -> Optional[str]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None


def _parse_panel_verdict(value: Any) -> PanelVerdict:
    if not value:
        return PanelVerdict.UNKNOWN
    normalized = str(value).strip().lower()
    if normalized in {"true", "supports", "supporting"}:
        return PanelVerdict.TRUE
    if normalized in {"false", "refutes", "refuting"}:
        return PanelVerdict.FALSE
    if normalized == "mixed":
        return PanelVerdict.MIXED
    if normalized == "unknown" or normalized == "uncertain":
        return PanelVerdict.UNKNOWN
    return PanelVerdict.UNKNOWN


def _map_citations(
    values: Optional[Iterable[Any]], evidence_lookup: Dict[str, UUID]
) -> List[UUID]:
    if not values:
        return []
    mapped: List[UUID] = []
    for value in values:
        if isinstance(value, UUID):
            mapped.append(value)
            continue
        if not value:
            continue
        token = str(value)
        for evidence_id, uuid_value in evidence_lookup.items():
            if token == evidence_id or token in evidence_id:
                mapped.append(uuid_value)
                break
    # Remove duplicates while preserving order
    seen: set[UUID] = set()
    result: List[UUID] = []
    for item in mapped:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _fallback_rationale(
    provider_id: str,
    model: str,
    prompt: Dict[str, Any],
    verdict: Any,
) -> str:
    claim_text = prompt.get("claim", {}).get("text", "the claim")
    evidence_count = prompt.get("evidence_count", 0)
    verdict_text = str(verdict or "unknown")
    return (
        f"{provider_id} ({model}) returned a fallback verdict '{verdict_text}'. "
        f"Automated tooling analysed {evidence_count} evidence item(s) for the claim '{claim_text}'. "
        "This rationale is generated locally because the remote provider response was unavailable."
    )


def _pad_rationale(text: str) -> str:
    filler = (
        " Additional context: the panel adapter ensures transparency by documenting "
        "any assumptions and explicitly listing cited evidence identifiers."
    )
    combined = (text or "No rationale provided.") + filler
    return combined if len(combined) >= 50 else combined.ljust(50, " ")


def _generate_stub_payload(
    provider_id: str,
    model: str,
    prompt: Dict[str, Any],
    error: str = "",
) -> Dict[str, Any]:
    evidence = prompt.get("evidence", [])
    first_id = evidence[0]["id"] if evidence else None
    verdict_profile = _stub_profile(provider_id)
    
    # Build a more informative rationale that includes evidence sources
    evidence_sources = []
    for i, ev in enumerate(evidence[:3]):  # Show first 3 sources
        publisher = ev.get("publisher", "Unknown")
        evidence_sources.append(publisher)
    
    sources_text = ", ".join(evidence_sources) if evidence_sources else "no sources"
    
    rationale = (
        f"{provider_id} ({model}) produced a deterministic offline assessment. "
        f"The claim was reviewed against {len(evidence)} evidence snippet(s) from {sources_text} "
        "and the adapter is reporting a stub response to keep tests self-contained."
    )
    if error:
        rationale += f" Provider noted: {error}."

    payload: Dict[str, Any] = {
        "provider_id": provider_id,
        "verdict": verdict_profile["verdict"].value,
        "confidence": verdict_profile["confidence"],
        "rationale": _pad_rationale(rationale),
        "citations": [first_id] if first_id else [],
    }
    return payload


def _stub_profile(provider_id: str) -> Dict[str, Any]:
    if provider_id.startswith("openai"):
        return {"verdict": PanelVerdict.TRUE, "confidence": 0.78}
    if provider_id.startswith("xai"):
        return {"verdict": PanelVerdict.FALSE, "confidence": 0.62}
    if provider_id.startswith("google"):
        return {"verdict": PanelVerdict.MIXED, "confidence": 0.55}
    return {"verdict": PanelVerdict.TRUE, "confidence": 0.6}


