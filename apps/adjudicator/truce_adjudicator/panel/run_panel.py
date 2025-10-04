"""Panel evaluation pipeline with provider adapters and aggregation."""

from __future__ import annotations

import asyncio
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
    Evidence,
    ModelAssessment,
    PanelModelVerdict,
    PanelResult,
    PanelSummary,
    PanelVerdict,
    TimeWindow,
    VerdictType,
)
from .agentic_research import AgenticResearcher, SharedEvidencePool

DEFAULT_PANEL_MODELS: List[str] = [
    "gpt-4o",  # OpenAI's latest model (was gpt-5 which doesn't exist)
    "grok-3",  # xAI's latest (grok-beta deprecated Sept 2025)
    "gemini-2.0-flash-exp",  # Google's latest Gemini
    "claude-sonnet-4-20250514",  # Anthropic's latest Claude Sonnet 4
]

SYSTEM_PROMPT = """You are an objective fact-checking assistant. For each claim, you must provide BOTH an approval argument and a refusal argument with evidence and confidence.

CRITICAL: Respond with ONLY valid JSON. No markdown, no code fences, no comments. Just the JSON object.

Required JSON structure:
{
  "provider_id": "provider:model",
  "approval_argument": {
    "argument": "50-500 words explaining why the claim might be true, with evidence IDs",
    "evidence_ids": ["evidence_id"],
    "confidence": 0.7
  },
  "refusal_argument": {
    "argument": "50-500 words explaining why the claim might be false, with evidence IDs",
    "evidence_ids": ["evidence_id"],
    "confidence": 0.3
  }
}

Rules:
- Use only valid JSON (no trailing commas, no comments)
- confidence must be a number between 0.0 and 1.0
- evidence_ids must be an array of strings
- Provide balanced analysis with evidence citations for both perspectives"""


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
        from ..models import ArgumentWithEvidence
        
        payload = await self._call_provider(prompt)
        parsed = _ensure_payload_dict(payload)
        
        # Parse approval argument
        approval_data = parsed.get("approval_argument", {})
        approval_arg = approval_data.get("argument", "") or _fallback_argument(
            self.provider_id, self.model, prompt, "approval"
        )
        # Ensure argument meets length requirements (50-1000 chars)
        if len(approval_arg) > 1000:
            approval_arg = approval_arg[:1000]
        elif len(approval_arg) < 50:
            approval_arg = _pad_argument(approval_arg, "approval")
        approval_evidence = _map_citations(approval_data.get("evidence_ids", []), evidence_lookup)
        approval_confidence = _parse_confidence(approval_data.get("confidence"), default=0.5)
        
        # Parse refusal argument
        refusal_data = parsed.get("refusal_argument", {})
        refusal_arg = refusal_data.get("argument", "") or _fallback_argument(
            self.provider_id, self.model, prompt, "refusal"
        )
        # Ensure argument meets length requirements (50-1000 chars)
        if len(refusal_arg) > 1000:
            refusal_arg = refusal_arg[:1000]
        elif len(refusal_arg) < 50:
            refusal_arg = _pad_argument(refusal_arg, "refusal")
        refusal_evidence = _map_citations(refusal_data.get("evidence_ids", []), evidence_lookup)
        refusal_confidence = _parse_confidence(refusal_data.get("confidence"), default=0.5)

        return PanelModelVerdict(
            provider_id=self.provider_id,
            model=self.model,
            approval_argument=ArgumentWithEvidence(
                argument=approval_arg,
                evidence_ids=approval_evidence,
                confidence=approval_confidence,
            ),
            refusal_argument=ArgumentWithEvidence(
                argument=refusal_arg,
                evidence_ids=refusal_evidence,
                confidence=refusal_confidence,
            ),
            raw=parsed,
        )

    async def _call_provider(self, prompt: Dict[str, Any]) -> Any:
        try:
            response = await self._invoke(prompt)
            if response is None:
                raise ValueError("Empty provider response")
            return response
        except Exception as exc:
            # Check if this is a "fatal" error that should cause the model to fail
            # rather than fall back to stub responses
            if self._should_fail_on_error(exc):
                raise exc  # Let the outer evaluation loop handle this as a failure
            else:
                return self._fallback(prompt, error=str(exc))
    
    def _should_fail_on_error(self, exc: Exception) -> bool:
        """
        Determine if an error should cause the model to fail completely
        rather than fall back to stub responses.
        
        JSON parsing errors and response format errors should cause failure,
        while missing API keys should fall back to stubs.
        """
        error_msg = str(exc).lower()
        
        # These errors should cause model failure (not stubs)
        fatal_patterns = [
            "could not parse provider payload",
            "expecting ',' delimiter",
            "expecting value:",
            "json decode",
            "invalid json",
            "unterminated string",
        ]
        
        return any(pattern in error_msg for pattern in fatal_patterns)

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
            max_tokens=1200,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content if completion.choices else ""
        
        print(f"OpenAI ({self.model}) response preview: {content[:200]}")
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
            max_tokens=1200,
            temperature=0.1,
        )
        content = completion.choices[0].message.content if completion.choices else ""
        
        print(f"Grok ({self.model}) response preview: {content[:200]}")
        return _ensure_payload_dict(content)


class GeminiProviderAdapter(BaseProviderAdapter):
    """Adapter for Google Gemini models using the official Google GenAI SDK."""

    def __init__(self, model: str) -> None:
        super().__init__(model)
        self.provider_id = f"google:{model}"
        self._client: Optional[Any] = None

    async def _invoke(self, prompt: Dict[str, Any]) -> Any:  # pragma: no cover - network call
        # Support both env var names; prefer GEMINI_API_KEY per latest docs
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini API key not configured (set GEMINI_API_KEY)")

        # Try the new google-genai SDK first
        try:
            from google import genai as genai_v2
            from google.genai import types as genai_types

            if self._client is None:
                # The client reads GEMINI_API_KEY from env automatically
                self._client = genai_v2.Client()

            serialized = json.dumps(prompt, ensure_ascii=False)

            structured_prompt = f"""{SYSTEM_PROMPT}

CRITICAL: Your response MUST be valid JSON that exactly matches this structure:
{{
  "provider_id": "{self.provider_id}",
  "approval_argument": {{
    "argument": "your approval argument text here",
    "evidence_ids": ["evidence_id1", "evidence_id2"],
    "confidence": 0.7
  }},
  "refusal_argument": {{
    "argument": "your refusal argument text here", 
    "evidence_ids": ["evidence_id1", "evidence_id2"],
    "confidence": 0.3
  }}
}}

User input: {serialized}

Respond with ONLY the JSON object. No markdown, no explanations, no code blocks."""

            # Disable thinking for speed/cost; rely on prompt to produce JSON
            config = genai_types.GenerateContentConfig(
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
            )

            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self.model,
                contents=structured_prompt,
                config=config,
            )

            content = getattr(response, "text", "").strip()
            if not content:
                raise ValueError("Empty response from Gemini")

            print(f"Gemini raw response preview: {content[:200]}")
            # Let _ensure_payload_dict handle fences and minor repairs
            return _ensure_payload_dict(content)

        except ImportError:
            # Fallback 1: legacy google-generativeai SDK if installed
            try:
                import google.generativeai as genai_v1

                if self._client is None:
                    genai_v1.configure(api_key=api_key)
                    self._client = genai_v1.GenerativeModel(
                        self.model,
                        generation_config=genai_v1.types.GenerationConfig(
                            max_output_tokens=1200,
                            temperature=0.1,
                        ),
                    )

                serialized = json.dumps(prompt, ensure_ascii=False)
                structured_prompt = f"""{SYSTEM_PROMPT}\n\nUser input: {serialized}\n\nRespond with ONLY the JSON object. No markdown, no explanations, no code blocks."""

                response = await asyncio.to_thread(
                    self._client.generate_content,
                    structured_prompt,
                )

                content = getattr(response, "text", "").strip()
                if not content:
                    raise ValueError("Empty response from Gemini")
                # Let _ensure_payload_dict handle fences and minor repairs
                return _ensure_payload_dict(content)

            except ImportError:
                # Fallback 2: OpenAI-compatible endpoint if neither SDK available
                if openai is None:
                    raise RuntimeError(
                        "Gemini SDKs not available and OpenAI client missing"
                    )
                return await self._invoke_via_openai(prompt, api_key)
        except Exception as e:
            print(f"Gemini API error: {e}")
            print(f"Model: {self.model}, Provider ID: {self.provider_id}")
            raise

    async def _invoke_via_openai(self, prompt: Dict[str, Any], api_key: str) -> Any:
        """Fallback to OpenAI-compatible interface."""
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
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


async def run_agentic_panel_evaluation(
    claim: Claim,
    models: Sequence[str],
    time_window: Optional[TimeWindow] = None,
    session_id: Optional[str] = None,
    mcp_server_url: Optional[str] = None,
) -> PanelResult:
    """
    Run agentic panel evaluation where each agent conducts independent research.
    
    Args:
        claim: The claim to evaluate (may have minimal or no initial evidence)
        models: List of model names to use as panel agents
        time_window: Optional time window for research
        session_id: Optional session ID for progress updates
        mcp_server_url: URL of the FastMCP Brave Search server
    
    Returns:
        PanelResult with independently researched evidence and verdicts
    """
    selected_models = list(models) if models else DEFAULT_PANEL_MODELS
    evidence_pool = SharedEvidencePool()
    
    # Phase 1: Independent Agentic Research
    if session_id:
        from ..main import emit_agent_update
        await emit_agent_update(
            session_id, 
            "Agentic Panel Coordinator", 
            "Starting independent research phase", 
            f"Each of {len(selected_models)} agents will conduct independent research on: {claim.text}",
            "research_phase",
            []
        )
    
    # Create researchers for each model/agent
    researchers = []
    research_tasks = []
    
    for model_name in selected_models:
        researcher = AgenticResearcher(
            agent_name=f"{model_name}_researcher",
            mcp_server_url=mcp_server_url,
            max_search_turns=5,
            max_sources_per_turn=8
        )
        researchers.append((model_name, researcher))
        
        # Start research task
        task = researcher.conduct_research(claim, time_window, session_id)
        research_tasks.append(task)
    
    # Wait for all research to complete
    research_results = await asyncio.gather(*research_tasks, return_exceptions=True)
    
    # Collect all evidence in shared pool
    total_evidence_collected = 0
    for i, (model_name, researcher) in enumerate(researchers):
        evidence_list = research_results[i]
        if isinstance(evidence_list, Exception):
            print(f"Research failed for {model_name}: {evidence_list}")
            evidence_list = []
        
        added_count = await evidence_pool.add_evidence(evidence_list, model_name)
        total_evidence_collected += added_count
    
    if session_id:
        evidence_summary = evidence_pool.get_evidence_summary()
        await emit_agent_update(
            session_id,
            "Agentic Panel Coordinator",
            f"Research phase complete: {total_evidence_collected} evidence items collected",
            f"Collected evidence from {evidence_summary['unique_domains']} domains and {evidence_summary['unique_publishers']} publishers",
            "research_complete",
            list(evidence_summary['publishers'][:5])
        )
    
    # Phase 2: Create enriched claim with all collected evidence
    all_evidence = evidence_pool.get_all_evidence()
    enriched_claim = Claim(
        id=claim.id,
        text=claim.text,
        topic=claim.topic,
        entities=claim.entities,
        evidence=all_evidence,  # Use all researched evidence
    )
    
    # Phase 3: Independent Verdict Formation
    if session_id:
        await emit_agent_update(
            session_id,
            "Agentic Panel Coordinator",
            "Starting verdict formation phase",
            f"Each agent will independently analyze all {len(all_evidence)} evidence items to form their verdict",
            "verdict_phase",
            []
        )
    
    # Build prompt with all collected evidence
    prompt = build_normalized_prompt(enriched_claim, time_window)
    evidence_lookup = {str(ev.id): ev.id for ev in all_evidence}
    
    # Get verdicts from each model independently
    panel_models: List[PanelModelVerdict] = []
    for model_name in selected_models:
        if session_id:
            await emit_agent_update(
                session_id,
                f"{model_name} Agent",
                f"Analyzing evidence for independent verdict",
                f"Evaluating {len(all_evidence)} evidence sources to determine claim veracity",
                "verdict_analysis",
                []
            )
        
        try:
            adapter = _resolve_adapter(model_name)
            verdict = await adapter.evaluate(enriched_claim, prompt, evidence_lookup)
            panel_models.append(verdict)
        except Exception as e:
            # Create a failed verdict instead of crashing
            print(f"Model {model_name} failed: {e}")
            failed_verdict = _create_failed_verdict(model_name, str(e), prompt)
            panel_models.append(failed_verdict)
            
            if session_id:
                await emit_agent_update(
                    session_id,
                    f"{model_name} Agent",
                    f"Evaluation failed",
                    f"Error: {str(e)}",
                    "error",
                    []
                )
    
    # Phase 4: Update original claim with collected evidence
    claim.evidence.extend(all_evidence)
    # Remove duplicates based on URL while preserving order
    seen_urls = set()
    unique_evidence = []
    for evidence in claim.evidence:
        if evidence.url not in seen_urls:
            seen_urls.add(evidence.url)
            unique_evidence.append(evidence)
    claim.evidence = unique_evidence
    
    # Phase 5: Aggregate Panel Results
    summary = aggregate_panel(panel_models)
    
    if session_id:
        verdict_str = summary.verdict.value if summary.verdict else "mixed"
        await emit_agent_update(
            session_id,
            "Agentic Panel Coordinator",
            f"Panel evaluation complete: {verdict_str}",
            f"Final verdict: {verdict_str} with {summary.support_confidence:.2f} support / {summary.refute_confidence:.2f} refute confidence from {summary.model_count} independent agents",
            "complete",
            []
        )
    
    return PanelResult(prompt=prompt, models=panel_models, summary=summary)


async def run_panel_evaluation(
    claim: Claim,
    models: Sequence[str],
    time_window: Optional[TimeWindow] = None,
    session_id: Optional[str] = None,
    enable_agentic_research: bool = True,
    mcp_server_url: Optional[str] = None,
) -> PanelResult:
    """
    Run panel evaluation with optional agentic research.
    
    Args:
        claim: The claim to evaluate
        models: List of model names to use as panel agents
        time_window: Optional time window for evaluation
        session_id: Optional session ID for progress updates
        enable_agentic_research: Whether to enable agentic research mode
        mcp_server_url: URL of the FastMCP Brave Search server
    
    Returns:
        PanelResult with verdicts and evidence
    """
    if enable_agentic_research:
        return await run_agentic_panel_evaluation(
            claim, models, time_window, session_id, mcp_server_url
        )
    else:
        # Original panel evaluation (requires existing evidence)
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
    """
    Aggregate per-model verdicts by normalizing and averaging confidences.
    
    Each model provides approval and refusal confidence scores that are normalized
    to sum to 1.0 before aggregation, ensuring logical consistency.
    
    Failed models are excluded from aggregation.
    """
    if not models:
        return PanelSummary(
            support_confidence=0.0,
            refute_confidence=0.0,
            model_count=0,
            verdict=PanelVerdict.UNKNOWN,
        )

    # Filter out failed models from aggregation
    successful_models = [m for m in models if not m.failed]
    
    if not successful_models:
        return PanelSummary(
            support_confidence=0.0,
            refute_confidence=0.0,
            model_count=0,
            verdict=PanelVerdict.UNKNOWN,
        )

    # Normalize each model's confidences to sum to 1.0, then average
    normalized_support_total = 0.0
    normalized_refute_total = 0.0
    
    for model in successful_models:
        approval_conf = model.approval_argument.confidence
        refusal_conf = model.refusal_argument.confidence
        
        # Normalize so they sum to 1.0
        total = approval_conf + refusal_conf
        if total > 0:
            normalized_approval = approval_conf / total
            normalized_refusal = refusal_conf / total
        else:
            # If both are 0, split evenly
            normalized_approval = 0.5
            normalized_refusal = 0.5
        
        normalized_support_total += normalized_approval
        normalized_refute_total += normalized_refusal
    
    support_confidence = normalized_support_total / len(successful_models)
    refute_confidence = normalized_refute_total / len(successful_models)
    
    # Determine verdict based on which confidence is higher
    confidence_diff = abs(support_confidence - refute_confidence)
    
    if support_confidence > refute_confidence:
        if confidence_diff >= 0.3:  # Strong support (>65% vs <35%)
            verdict = PanelVerdict.TRUE
        elif confidence_diff >= 0.1:  # Moderate support (>55% vs <45%)
            verdict = PanelVerdict.MIXED
        else:
            verdict = PanelVerdict.UNKNOWN
    elif refute_confidence > support_confidence:
        if confidence_diff >= 0.3:  # Strong refute
            verdict = PanelVerdict.FALSE
        elif confidence_diff >= 0.1:  # Moderate refute
            verdict = PanelVerdict.MIXED
        else:
            verdict = PanelVerdict.UNKNOWN
    else:
        verdict = PanelVerdict.MIXED

    return PanelSummary(
        support_confidence=round(support_confidence, 4),
        refute_confidence=round(refute_confidence, 4),
        model_count=len(successful_models),  # Only count successful models
        verdict=verdict,
    )


def panel_result_to_assessments(panel: PanelResult) -> List[ModelAssessment]:
    """Convert panel verdicts into legacy ModelAssessment structures."""
    assessments: List[ModelAssessment] = []
    
    for model in panel.models:
        # Use the stronger argument (higher confidence) as the primary verdict
        if model.approval_argument.confidence > model.refusal_argument.confidence:
            verdict = VerdictType.SUPPORTS
            confidence = model.approval_argument.confidence
            rationale = f"Approval: {model.approval_argument.argument}"
            citations = model.approval_argument.evidence_ids
        elif model.refusal_argument.confidence > model.approval_argument.confidence:
            verdict = VerdictType.REFUTES
            confidence = model.refusal_argument.confidence
            rationale = f"Refusal: {model.refusal_argument.argument}"
            citations = model.refusal_argument.evidence_ids
        else:
            verdict = VerdictType.MIXED
            confidence = (model.approval_argument.confidence + model.refusal_argument.confidence) / 2
            rationale = f"Mixed: Approval ({model.approval_argument.confidence:.2f}) - {model.approval_argument.argument[:100]}... Refusal ({model.refusal_argument.confidence:.2f}) - {model.refusal_argument.argument[:100]}..."
            citations = list(set(model.approval_argument.evidence_ids + model.refusal_argument.evidence_ids))
        
        assessments.append(
            ModelAssessment(
                model_name=model.model,
                verdict=verdict,
                confidence=confidence,
                citations=citations,
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
        
        # Remove markdown code blocks if present
        text = _strip_markdown_fences(text)
        
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Initial JSON parse failed: {e}")
            
            # Try to repair the text directly first
            repaired_text = _repair_json(text)
            try:
                result = json.loads(repaired_text)
                print(f"✓ JSON repaired successfully")
                return result
            except json.JSONDecodeError:
                pass  # Continue to extraction
            
            # Try to extract JSON block from potentially wrapped response
            block = _extract_json_block(text)
            if block:
                # Try to repair common JSON issues
                repaired = _repair_json(block)
                try:
                    result = json.loads(repaired)
                    print(f"✓ JSON extracted and repaired successfully")
                    return result
                except json.JSONDecodeError as inner_e:
                    # Log detailed error information
                    print(f"❌ JSON parse error after repair: {inner_e}")
                    print(f"📄 Original response length: {len(text)}")
                    print(f"📄 Original response preview: {text[:500]}")
                    print(f"🔧 Repaired block preview: {repaired[:500]}")
                    
                    # Show the specific problem area
                    try:
                        error_pos = inner_e.pos if hasattr(inner_e, 'pos') else 0
                        context_start = max(0, error_pos - 50)
                        context_end = min(len(repaired), error_pos + 50)
                        print(f"❌ Error near position {error_pos}:")
                        print(f"   ...{repaired[context_start:context_end]}...")
                    except:
                        pass
                    
                    raise ValueError(f"Could not parse provider payload: {inner_e}")
            
            print(f"❌ JSON parse error (no block found): {e}")
            print(f"📄 Response preview: {text[:500]}")
            raise ValueError(f"Could not parse provider payload: {e}")
    raise ValueError("Could not parse provider payload")


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code block fences like ```json ... ```"""
    # Remove ```json at start and ``` at end
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```\s*$', '', text)
    return text.strip()


def _extract_json_block(text: str) -> Optional[str]:
    """Extract JSON object from text, handling nested braces."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else None


def _repair_json(text: str) -> str:
    """
    Attempt to repair common JSON formatting issues.
    
    This function handles multiple common LLM JSON generation errors:
    - Trailing commas before closing braces/brackets
    - Multiple consecutive commas
    - Comments (both // and /* */ style)
    - Leading/trailing whitespace
    """
    # Remove comments (// style) - do this first
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    
    # Remove comments (/* */ style)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # Remove trailing commas before closing braces/brackets (most common issue)
    # Handle multiple cases:
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Remove multiple consecutive commas
    text = re.sub(r',\s*,+', ',', text)
    
    # Fix missing commas between string values and next key (common LLM error)
    # "value1" "key2" -> "value1", "key2"
    text = re.sub(r'"\s+(?=")', '", ', text)
    
    # Fix missing commas between } and {
    text = re.sub(r'}\s*{', '}, {', text)
    
    # Fix missing commas between ] and [
    text = re.sub(r']\s*\[', '], [', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


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


def _parse_confidence(value: Any, default: float = 0.5) -> float:
    """Parse confidence value ensuring it's within 0-1 range."""
    if value is None:
        return default
    try:
        conf = float(value)
        return max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        return default


def _fallback_argument(
    provider_id: str,
    model: str,
    prompt: Dict[str, Any],
    argument_type: str,
) -> str:
    """Generate fallback argument when provider response is incomplete."""
    claim_text = prompt.get("claim", {}).get("text", "the claim")
    evidence_count = prompt.get("evidence_count", 0)
    
    if argument_type == "approval":
        return (
            f"{provider_id} ({model}) fallback approval argument. "
            f"Analyzing {evidence_count} evidence item(s) for potential support of: {claim_text}. "
            "This argument is generated locally due to incomplete provider response."
        )
    else:
        return (
            f"{provider_id} ({model}) fallback refusal argument. "
            f"Analyzing {evidence_count} evidence item(s) for potential refutation of: {claim_text}. "
            "This argument is generated locally due to incomplete provider response."
        )


def _pad_argument(text: str, argument_type: str) -> str:
    """Pad short arguments to meet minimum length requirements."""
    if len(text) >= 50:
        # If already long enough, just ensure it's not too long
        return text[:1000] if len(text) > 1000 else text
    
    filler = (
        f" This {argument_type} argument includes analysis of available evidence "
        "with explicit citation of source identifiers for transparency."
    )
    combined = (text or f"No {argument_type} argument provided.") + filler
    # Ensure we don't exceed max length
    return combined[:1000] if len(combined) > 1000 else (combined if len(combined) >= 50 else combined.ljust(50, " "))


def _generate_stub_payload(
    provider_id: str,
    model: str,
    prompt: Dict[str, Any],
    error: str = "",
) -> Dict[str, Any]:
    evidence = prompt.get("evidence", [])
    evidence_ids = [ev["id"] for ev in evidence[:3]] if evidence else []
    profile = _stub_profile(provider_id)
    
    # Build evidence sources text
    evidence_sources = []
    for ev in evidence[:3]:
        publisher = ev.get("publisher", "Unknown")
        evidence_sources.append(publisher)
    sources_text = ", ".join(evidence_sources) if evidence_sources else "no sources"
    
    approval_arg = (
        f"{provider_id} ({model}) stub approval analysis. "
        f"Reviewed {len(evidence)} evidence items from {sources_text}. "
        "This is a deterministic offline assessment for testing."
    )
    
    refusal_arg = (
        f"{provider_id} ({model}) stub refusal analysis. "
        f"Reviewed {len(evidence)} evidence items from {sources_text}. "
        "This is a deterministic offline assessment for testing."
    )
    
    if error:
        approval_arg += f" Note: {error}."
        refusal_arg += f" Note: {error}."

    payload: Dict[str, Any] = {
        "provider_id": provider_id,
        "approval_argument": {
            "argument": _pad_argument(approval_arg, "approval"),
            "evidence_ids": evidence_ids,
            "confidence": profile["approval_confidence"],
        },
        "refusal_argument": {
            "argument": _pad_argument(refusal_arg, "refusal"),
            "evidence_ids": evidence_ids,
            "confidence": profile["refusal_confidence"],
        },
    }
    return payload


def _create_failed_verdict(model_name: str, error: str, prompt: Dict[str, Any]) -> PanelModelVerdict:
    """
    Create a failed verdict for a model that couldn't complete evaluation.
    
    This verdict will be marked as failed and excluded from aggregation,
    but included in the results for transparency.
    """
    from ..models import ArgumentWithEvidence, PanelModelVerdict
    
    # Determine provider_id from model name
    if "gpt" in model_name.lower() or "o1" in model_name.lower():
        provider_id = f"openai:{model_name}"
    elif "grok" in model_name.lower():
        provider_id = f"xai:{model_name}"
    elif "gemini" in model_name.lower():
        provider_id = f"google:{model_name}"
    elif "claude" in model_name.lower() or "sonnet" in model_name.lower():
        provider_id = f"anthropic:{model_name}"
    else:
        provider_id = f"unknown:{model_name}"
    
    # Create placeholder arguments with 0 confidence
    placeholder_arg = ArgumentWithEvidence(
        argument=f"Model evaluation failed: {error}",
        evidence_ids=[],
        confidence=0.0,
    )
    
    # Extract more details for error_details field
    evidence_count = prompt.get("evidence_count", 0)
    error_details = f"Failed to evaluate {evidence_count} evidence items. Error: {error}"
    
    return PanelModelVerdict(
        provider_id=provider_id,
        model=model_name,
        approval_argument=placeholder_arg,
        refusal_argument=placeholder_arg,
        raw={"error": error},
        failed=True,
        error=error,
        error_details=error_details,
    )


def _stub_profile(provider_id: str) -> Dict[str, Any]:
    """Generate stub confidence profiles for testing."""
    if provider_id.startswith("openai"):
        return {"approval_confidence": 0.75, "refusal_confidence": 0.25}
    if provider_id.startswith("xai"):
        return {"approval_confidence": 0.30, "refusal_confidence": 0.70}
    if provider_id.startswith("google"):
        return {"approval_confidence": 0.55, "refusal_confidence": 0.45}
    if provider_id.startswith("anthropic"):
        return {"approval_confidence": 0.65, "refusal_confidence": 0.35}
    return {"approval_confidence": 0.60, "refusal_confidence": 0.40}


