"""Create reproducibility bundles for claim evaluations"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from ..models import Claim, ReplayBundle


async def create_replay_bundle(claim: Claim) -> ReplayBundle:
    """Create a replay bundle for reproducing a claim evaluation"""

    # Collect input data
    inputs = {
        "claim_id": str(claim.id),
        "claim_text": claim.text,
        "topic": claim.topic,
        "entities": claim.entities,
        "created_at": claim.created_at.isoformat(),
        "evidence_sources": [
            {
                "id": str(evidence.id),
                "url": evidence.url,
                "publisher": evidence.publisher,
                "published_at": (
                    evidence.published_at.isoformat() if evidence.published_at else None
                ),
                "snippet": evidence.snippet,
                "provenance": evidence.provenance,
            }
            for evidence in claim.evidence
        ],
    }

    # Collect model prompts and responses
    model_prompts = []
    model_responses = []

    for assessment in claim.model_assessments:
        # Reconstruct the prompt that would have been used
        evidence_context = f"CLAIM: {claim.text}\n\nEVIDENCE:\n"
        for i, evidence in enumerate(claim.evidence):
            if evidence.id in assessment.citations:
                evidence_context += f"\nEvidence {i+1} (ID: {evidence.id}):\n"
                evidence_context += f"Source: {evidence.url}\n"
                evidence_context += f"Publisher: {evidence.publisher}\n"
                evidence_context += f"Content: {evidence.snippet}\n"
                evidence_context += f"---\n"

        model_prompts.append(
            {
                "model_name": assessment.model_name,
                "timestamp": assessment.created_at.isoformat(),
                "system_prompt": "Objective fact-checking evaluation system prompt",
                "user_prompt": evidence_context,
                "parameters": {"temperature": 0.1, "max_tokens": 1000},
            }
        )

        model_responses.append(
            {
                "model_name": assessment.model_name,
                "timestamp": assessment.created_at.isoformat(),
                "verdict": assessment.verdict.value,
                "confidence": assessment.confidence,
                "citations": [str(cid) for cid in assessment.citations],
                "rationale": assessment.rationale,
            }
        )

    # Create JSON-LD representation
    final_graph = await _create_jsonld_graph(claim)

    # Create replay bundle
    bundle = ReplayBundle(
        claim_id=claim.id,
        inputs=inputs,
        model_prompts=model_prompts,
        model_responses=model_responses,
        final_graph=final_graph,
    )

    return bundle


async def _create_jsonld_graph(claim: Claim) -> Dict[str, Any]:
    """Create JSON-LD representation of the claim and its evaluation"""

    # Define context
    context = {
        "@context": {
            "tr": "https://truce.dev/vocab#",
            "schema": "http://schema.org/",
            "wd": "http://www.wikidata.org/entity/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
    }

    # Main claim object
    claim_obj = {
        "@id": f"tr:claim/{claim.id}",
        "@type": "tr:Claim",
        "tr:text": claim.text,
        "tr:topic": claim.topic,
        "tr:createdAt": {
            "@type": "xsd:dateTime",
            "@value": claim.created_at.isoformat(),
        },
    }

    # Add entities if present
    if claim.entities:
        claim_obj["tr:entities"] = [
            {"@id": f"wd:{entity}"} for entity in claim.entities
        ]

    # Add evidence
    evidence_objects = []
    for evidence in claim.evidence:
        evidence_obj = {
            "@id": f"tr:evidence/{evidence.id}",
            "@type": "tr:Evidence",
            "schema:url": evidence.url,
            "tr:publisher": evidence.publisher,
            "tr:snippet": evidence.snippet,
            "tr:provenance": evidence.provenance,
        }

        if evidence.published_at:
            evidence_obj["tr:publishedAt"] = {
                "@type": "xsd:dateTime",
                "@value": evidence.published_at.isoformat(),
            }

        evidence_objects.append(evidence_obj)

    # Add model assessments
    assessment_objects = []
    for assessment in claim.model_assessments:
        assessment_obj = {
            "@id": f"tr:assessment/{assessment.id}",
            "@type": "tr:ModelAssessment",
            "tr:modelName": assessment.model_name,
            "tr:verdict": assessment.verdict.value,
            "tr:confidence": {"@type": "xsd:decimal", "@value": assessment.confidence},
            "tr:rationale": assessment.rationale,
            "tr:citations": [
                {"@id": f"tr:evidence/{cid}"} for cid in assessment.citations
            ],
        }

        assessment_objects.append(assessment_obj)

    # Add human reviews
    review_objects = []
    for review in claim.human_reviews:
        review_obj = {
            "@id": f"tr:review/{review.id}",
            "@type": "tr:HumanReview",
            "schema:author": review.author,
            "tr:verdict": review.verdict.value,
            "tr:notes": review.notes,
        }

        if review.signature_vc:
            review_obj["tr:signatureVC"] = review.signature_vc

        review_objects.append(review_obj)

    # Combine into graph
    graph = {
        "@graph": [claim_obj] + evidence_objects + assessment_objects + review_objects
    }

    # Add context
    graph.update(context)

    return graph


async def save_replay_bundle(
    bundle: ReplayBundle, output_dir: str = "data/replay"
) -> str:
    """Save replay bundle to disk as JSONL file"""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"claim_{bundle.claim_id}_{timestamp}.jsonl"
    filepath = os.path.join(output_dir, filename)

    # Write JSONL format (one JSON object per line)
    with open(filepath, "w", encoding="utf-8") as f:
        # Write bundle metadata
        f.write(
            json.dumps(
                {
                    "type": "bundle_metadata",
                    "id": str(bundle.id),
                    "claim_id": str(bundle.claim_id),
                    "created_at": bundle.created_at.isoformat(),
                }
            )
            + "\n"
        )

        # Write inputs
        f.write(json.dumps({"type": "inputs", "data": bundle.inputs}) + "\n")

        # Write model interactions
        for i, (prompt, response) in enumerate(
            zip(bundle.model_prompts, bundle.model_responses)
        ):
            f.write(
                json.dumps({"type": "model_prompt", "sequence": i, "data": prompt})
                + "\n"
            )

            f.write(
                json.dumps({"type": "model_response", "sequence": i, "data": response})
                + "\n"
            )

        # Write final graph
        f.write(json.dumps({"type": "final_graph", "data": bundle.final_graph}) + "\n")

    return filepath


async def verify_replay_bundle(bundle_path: str) -> bool:
    """Verify that a replay bundle is complete and valid"""

    try:
        required_types = {"bundle_metadata", "inputs", "final_graph"}
        found_types = set()

        with open(bundle_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    found_types.add(data.get("type", ""))

        # Check that all required types are present
        return required_types.issubset(found_types)

    except Exception as e:
        print(f"Bundle verification failed: {e}")
        return False
