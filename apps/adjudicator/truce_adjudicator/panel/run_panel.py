"""Multi-model panel evaluation of claims"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

import openai
import anthropic
import httpx
from dotenv import load_dotenv

from ..models import Claim, ModelAssessment, VerdictType

# Load environment variables
load_dotenv()

# API clients
openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an objective fact-checking assistant. Your job is to evaluate claims based on provided evidence.

You must respond with a JSON object containing exactly these fields:
{
  "verdict": "supports|refutes|mixed|uncertain",
  "confidence": 0.85,
  "citations": ["evidence_id_1", "evidence_id_2"],
  "rationale": "A detailed explanation of your assessment, citing specific evidence and explaining your reasoning."
}

Guidelines:
1. VERDICT OPTIONS:
   - "supports": Evidence clearly supports the claim
   - "refutes": Evidence clearly contradicts the claim  
   - "mixed": Evidence both supports and contradicts aspects of the claim
   - "uncertain": Evidence is insufficient or unclear

2. CONFIDENCE: Scale 0.0-1.0 based on evidence quality and clarity

3. CITATIONS: Must reference specific evidence IDs that informed your assessment

4. RATIONALE: 
   - Must cite specific evidence with URLs when possible
   - Explain reasoning clearly
   - Note any limitations or caveats in the evidence
   - Minimum 50 words, maximum 500 words

Be thorough, objective, and transparent about limitations."""


async def run_panel_evaluation(claim: Claim, models: List[str]) -> List[ModelAssessment]:
    """Run multi-model evaluation of a claim"""
    
    if not claim.evidence:
        raise ValueError("Cannot run panel evaluation without evidence")
    
    # Prepare evidence context for models
    evidence_context = _prepare_evidence_context(claim)
    
    assessments = []
    
    for model_name in models:
        try:
            if model_name.startswith("gpt"):
                assessment = await _evaluate_with_openai(model_name, claim, evidence_context)
            elif model_name.startswith("claude"):
                assessment = await _evaluate_with_anthropic(model_name, claim, evidence_context)
            else:
                print(f"Unknown model: {model_name}, skipping")
                continue
                
            assessments.append(assessment)
            
        except Exception as e:
            print(f"Error evaluating with {model_name}: {e}")
            # Create error assessment for transparency
            assessments.append(ModelAssessment(
                model_name=model_name,
                verdict=VerdictType.UNCERTAIN,
                confidence=0.0,
                citations=[],
                rationale=f"Evaluation failed due to error: {str(e)}"
            ))
    
    return assessments


def _prepare_evidence_context(claim: Claim) -> str:
    """Prepare evidence context for model evaluation"""
    context = f"CLAIM: {claim.text}\n\nEVIDENCE:\n"
    
    for i, evidence in enumerate(claim.evidence):
        context += f"\nEvidence {i+1} (ID: {evidence.id}):\n"
        context += f"Source: {evidence.url}\n"
        context += f"Publisher: {evidence.publisher}\n"
        context += f"Published: {evidence.published_at}\n"
        context += f"Content: {evidence.snippet}\n"
        context += f"---\n"
    
    context += f"\nPlease evaluate the claim '{claim.text}' based on this evidence."
    
    return context


async def _evaluate_with_openai(model_name: str, claim: Claim, evidence_context: str) -> ModelAssessment:
    """Evaluate claim using OpenAI models"""
    
    try:
        # Handle different parameter requirements for different models
        request_params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": evidence_context}
            ]
        }
        
        # GPT-5 has different parameter requirements
        if model_name.startswith("gpt-5"):
            request_params["max_completion_tokens"] = 1000
            # GPT-5 only supports default temperature (1)
        else:
            request_params["max_tokens"] = 1000
            request_params["temperature"] = 0.1
        
        response = await openai_client.chat.completions.create(**request_params)
        
        response_text = response.choices[0].message.content
        if response_text is None:
            raise ValueError("OpenAI returned empty response")
        response_text = response_text.strip()
        
        # Parse JSON response with improved handling
        result = None
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try multiple extraction methods for different response formats
            import re
            
            # Method 1: Look for JSON block
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Method 2: Look for structured content and construct JSON
            if not result:
                verdict_match = re.search(r'"?verdict"?\s*:?\s*"?(supports|refutes|mixed|uncertain)"?', response_text, re.IGNORECASE)
                confidence_match = re.search(r'"?confidence"?\s*:?\s*([0-9.]+)', response_text, re.IGNORECASE)
                rationale_match = re.search(r'"?rationale"?\s*:?\s*"([^"]+)"', response_text, re.DOTALL)
                
                if verdict_match:
                    result = {
                        "verdict": verdict_match.group(1).lower(),
                        "confidence": float(confidence_match.group(1)) if confidence_match else 0.5,
                        "citations": [],  # Will be populated below
                        "rationale": rationale_match.group(1) if rationale_match else f"GPT-5 assessment: {response_text[:500]}..."
                    }
                else:
                    raise ValueError(f"Could not parse JSON response: {response_text[:200]}...")
            
            if not result:
                raise ValueError(f"Could not parse JSON response: {response_text[:200]}...")
        
        # Convert citation strings to UUIDs
        citation_ids = []
        for citation in result.get("citations", []):
            if isinstance(citation, str):
                # Find evidence with matching ID
                for evidence in claim.evidence:
                    if str(evidence.id) == citation or citation in str(evidence.id):
                        citation_ids.append(evidence.id)
                        break
        
        assessment = ModelAssessment(
            model_name=model_name,
            verdict=VerdictType(result["verdict"]),
            confidence=float(result["confidence"]),
            citations=citation_ids,
            rationale=result["rationale"]
        )
        
        return assessment
        
    except Exception as e:
        raise ValueError(f"OpenAI evaluation failed: {str(e)}")


async def _evaluate_with_anthropic(model_name: str, claim: Claim, evidence_context: str) -> ModelAssessment:
    """Evaluate claim using Anthropic Claude models"""
    
    try:
        # Map model names to Anthropic API names
        model_mapping = {
            "claude-3": "claude-3-sonnet-20240229",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku": "claude-3-5-haiku-20241022",
            "claude-sonnet-4": "claude-sonnet-4-20250514",
            "claude-opus-4": "claude-opus-4-20250514",
            "claude-opus-4-1": "claude-opus-4-1-20250805",
            "claude-3-7-sonnet": "claude-3-7-sonnet-20250219"
        }
        
        api_model_name = model_mapping.get(model_name, model_name)
        
        response = await anthropic_client.messages.create(
            model=api_model_name,
            max_tokens=1000,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": evidence_context}
            ]
        )
        
        # Handle different response content types - use getattr to avoid type issues
        response_text = ""
        for content_block in response.content:
            # Use getattr to safely access text attribute
            text = getattr(content_block, 'text', None)
            if text:
                response_text += text
        
        response_text = response_text.strip()
        if not response_text and response.content:
            # Fallback to string representation of first content block
            response_text = str(response.content[0])
        
        if not response_text:
            raise ValueError("No text content found in Anthropic response")
        
        # Parse JSON response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON response")
        
        # Convert citation strings to UUIDs
        citation_ids = []
        for citation in result.get("citations", []):
            if isinstance(citation, str):
                # Find evidence with matching ID
                for evidence in claim.evidence:
                    if str(evidence.id) == citation or citation in str(evidence.id):
                        citation_ids.append(evidence.id)
                        break
        
        assessment = ModelAssessment(
            model_name=model_name,
            verdict=VerdictType(result["verdict"]),
            confidence=float(result["confidence"]),
            citations=citation_ids,
            rationale=result["rationale"]
        )
        
        return assessment
        
    except Exception as e:
        raise ValueError(f"Anthropic evaluation failed: {str(e)}")


async def get_default_models() -> List[str]:
    """Get list of default models to use for evaluation - best from each provider"""
    models = []
    
    # OpenAI - Use GPT-5 (the most advanced model)
    if os.getenv("OPENAI_API_KEY"):
        models.append("gpt-5")  # Latest and most capable OpenAI model
    
    # Anthropic - Use the best Claude model
    if os.getenv("ANTHROPIC_API_KEY"):
        models.append("claude-sonnet-4-20250514")  # Best Claude model
    
    if not models:
        # Mock models for demo purposes when no API keys available
        models = ["gpt-4-demo", "claude-3-demo"]
    
    return models


async def create_mock_assessments(claim: Claim) -> List[ModelAssessment]:
    """Create mock assessments for demo purposes when APIs are unavailable"""
    
    mock_assessments = []
    
    # Mock GPT-4 assessment
    gpt_assessment = ModelAssessment(
        model_name="gpt-4-demo",
        verdict=VerdictType.MIXED,
        confidence=0.75,
        citations=[claim.evidence[0].id] if claim.evidence else [],
        rationale="The claim 'Violent crime in Canada is rising' requires temporal context. "
                 "Based on Statistics Canada data, violent crime severity decreased slightly in 2024 (~1%) "
                 "but had increased cumulatively by ~15% over the preceding 3-year period (2021-2023). "
                 "The claim is therefore both supported (recent 3-year trend) and contradicted (2024 data). "
                 "Important caveats: data reflects police-reported crimes only; actual rates may differ."
    )
    mock_assessments.append(gpt_assessment)
    
    # Mock Claude assessment
    claude_assessment = ModelAssessment(
        model_name="claude-3-demo",
        verdict=VerdictType.UNCERTAIN,
        confidence=0.65,
        citations=[claim.evidence[0].id] if claim.evidence else [],
        rationale="The statement lacks sufficient temporal specificity to evaluate definitively. "
                 "Crime Severity Index data shows mixed trends: a decrease in 2024 following increases in 2021-2023. "
                 "The claim could be accurate for the 2021-2023 period but inaccurate for 2024. "
                 "Additionally, police-reported statistics have known limitations regarding under-reporting, "
                 "which affects the reliability of any definitive assessment."
    )
    mock_assessments.append(claude_assessment)
    
    return mock_assessments
