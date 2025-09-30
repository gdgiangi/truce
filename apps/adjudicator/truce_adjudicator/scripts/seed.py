#!/usr/bin/env python3
"""Seed script to create the Canadian violent crime demo"""

import asyncio
import json
import os
import random
import sys
from pathlib import Path

import httpx

# Add project root to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

# Change to the correct directory for imports
os.chdir(str(current_dir.parent))

from truce_adjudicator.models import Claim, ConsensusStatement
from truce_adjudicator.statcan.fetch_csi import fetch_crime_severity_data

API_BASE = "http://localhost:8000"


async def seed_canadian_crime_claim():
    """Create the Canadian violent crime claim with evidence and assessments"""

    print("🌱 Seeding Canadian violent crime claim...")

    # Create the main claim via API
    claim_data = {
        "text": "Violent crime in Canada is rising.",
        "topic": "canada-crime",
        "entities": ["Q16"],  # Canada on Wikidata
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Create claim
            response = await client.post(f"{API_BASE}/claims", json=claim_data)
            response.raise_for_status()
            claim_response = response.json()

            # Get the actual slug from the API response
            slug = claim_response.get("slug")
            if not slug:
                print("❌ API did not return a slug")
                return None

            print(f"✅ Created claim: {claim_data['text']}")
            print(f"   Slug: {slug}")

            # Add Statistics Canada evidence
            try:
                print("📊 Fetching StatCan crime severity data...")
                evidence_request = {"source_type": "statcan", "params": {}}

                evidence_response = await client.post(
                    f"{API_BASE}/claims/{slug}/evidence:statcan", json=evidence_request
                )
                if evidence_response.status_code == 200:
                    evidence_result = evidence_response.json()
                    print(
                        f"✅ Added {evidence_result.get('evidence_count', 0)} evidence items via API"
                    )
                else:
                    print(
                        f"⚠️  Evidence API call returned {evidence_response.status_code}: {evidence_response.text}"
                    )

            except Exception as e:
                print(f"❌ Failed to fetch StatCan data: {e}")

            # Run model panel
            try:
                print("🤖 Creating model assessments...")
                panel_response = await client.post(
                    f"{API_BASE}/claims/{slug}/panel/run",
                    json={"models": ["gpt-5", "claude-sonnet-4-20250514"]},
                )
                if panel_response.status_code == 200:
                    panel_result = panel_response.json()
                    assessment_count = len(panel_result.get("assessments", []))
                    print(f"✅ Added {assessment_count} model assessments")
                else:
                    print(
                        f"⚠️  Panel API call returned {panel_response.status_code}: {panel_response.text}"
                    )

            except Exception as e:
                print(f"❌ Failed to create assessments: {e}")

            return claim_response

        except Exception as e:
            print(f"❌ Failed to create claim: {e}")
            return None


async def seed_consensus_statements():
    """Create initial consensus statements for the Canada crime topic"""

    print("💭 Seeding consensus statements...")

    topic = "canada-crime"

    # Evidence-based neutral statements
    statements_data = [
        "Violent crime severity index decreased by approximately 1% in 2024 compared to 2023",
        "The violent crime severity index increased cumulatively over the 2021-2023 period",
        "Crime statistics reflect police-reported incidents and may not capture all crimes",
        "Different provinces may experience different crime trends than the national average",
        "Both crime prevention and victim support deserve policy attention",
        "Crime data should be interpreted with awareness of reporting limitations",
        "Social and economic factors influence crime rates",
        "Evidence-based approaches should guide crime policy decisions",
        "Community safety involves multiple factors beyond crime statistics",
        "Transparency in crime data helps inform public understanding",
    ]

    created_statements = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            for statement_text in statements_data:
                statement_data = {"text": statement_text, "evidence_links": []}

                response = await client.post(
                    f"{API_BASE}/consensus/{topic}/statements", json=statement_data
                )

                if response.status_code == 200:
                    statement_response = response.json()
                    created_statements.append(statement_response)
                else:
                    print(f"⚠️  Failed to create statement: {statement_text[:50]}...")

        except Exception as e:
            print(f"❌ Failed to create consensus statements: {e}")
            return []

    print(
        f"✅ Created {len(created_statements)} consensus statements for topic: {topic}"
    )
    return created_statements


async def simulate_votes_on_statements(statements):
    """Simulate diverse voting patterns to demonstrate clustering"""

    print("🗳️  Simulating diverse votes...")

    topic = "canada-crime"

    # Define different user personas with distinct voting patterns
    user_personas = {
        # Evidence-focused users (tend to agree with factual statements)
        "evidence_focused": {
            "users": ["analyst_001", "researcher_002", "stats_003", "academic_004"],
            "voting_patterns": {
                # More likely to agree with evidence-based statements
                "decreased by approximately 1%": {
                    "agree": 0.8,
                    "disagree": 0.1,
                    "pass": 0.1,
                },
                "increased cumulatively": {"agree": 0.8, "disagree": 0.1, "pass": 0.1},
                "police-reported incidents": {
                    "agree": 0.9,
                    "disagree": 0.0,
                    "pass": 0.1,
                },
                "reporting limitations": {"agree": 0.9, "disagree": 0.0, "pass": 0.1},
                "Evidence-based approaches": {
                    "agree": 0.9,
                    "disagree": 0.0,
                    "pass": 0.1,
                },
            },
        },
        # Policy-focused users (focus on solutions)
        "policy_focused": {
            "users": ["policy_001", "advocate_002", "planner_003", "official_004"],
            "voting_patterns": {
                "crime prevention": {"agree": 0.9, "disagree": 0.0, "pass": 0.1},
                "victim support": {"agree": 0.9, "disagree": 0.0, "pass": 0.1},
                "Social and economic factors": {
                    "agree": 0.8,
                    "disagree": 0.1,
                    "pass": 0.1,
                },
                "Community safety": {"agree": 0.8, "disagree": 0.1, "pass": 0.1},
                "Evidence-based approaches": {
                    "agree": 0.7,
                    "disagree": 0.1,
                    "pass": 0.2,
                },
            },
        },
        # Skeptical users (more critical of claims)
        "skeptical": {
            "users": ["critic_001", "skeptic_002", "analyst_003"],
            "voting_patterns": {
                "Different provinces": {"agree": 0.8, "disagree": 0.1, "pass": 0.1},
                "reporting limitations": {"agree": 0.7, "disagree": 0.2, "pass": 0.1},
                "may not capture all crimes": {
                    "agree": 0.8,
                    "disagree": 0.1,
                    "pass": 0.1,
                },
                "decreased by approximately 1%": {
                    "agree": 0.4,
                    "disagree": 0.4,
                    "pass": 0.2,
                },
                "increased cumulatively": {"agree": 0.4, "disagree": 0.4, "pass": 0.2},
            },
        },
    }

    votes_created = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            for statement in statements:
                statement_text = statement.get("text", "")
                statement_id = statement.get("id")

                if not statement_id:
                    continue

                # Generate votes from each persona
                for persona_name, persona_data in user_personas.items():
                    for user_id in persona_data["users"]:

                        # Find matching voting pattern for this statement
                        vote_probs = None
                        for pattern_key, probs in persona_data[
                            "voting_patterns"
                        ].items():
                            if pattern_key.lower() in statement_text.lower():
                                vote_probs = probs
                                break

                        # If no specific pattern, use default neutral pattern
                        if not vote_probs:
                            vote_probs = {"agree": 0.4, "disagree": 0.3, "pass": 0.3}

                        # Randomly determine vote based on probabilities
                        rand = random.random()
                        if rand < vote_probs["agree"]:
                            vote_type = "agree"
                        elif rand < vote_probs["agree"] + vote_probs["disagree"]:
                            vote_type = "disagree"
                        else:
                            vote_type = "pass"

                        # Submit vote
                        vote_data = {
                            "statement_id": statement_id,
                            "vote": vote_type,
                            "user_id": user_id,
                        }

                        response = await client.post(
                            f"{API_BASE}/consensus/{topic}/votes", json=vote_data
                        )

                        if response.status_code == 200:
                            votes_created += 1
                        else:
                            print(
                                f"⚠️  Failed to create vote for {user_id}: {response.text}"
                            )

        except Exception as e:
            print(f"❌ Failed to create votes: {e}")
            return 0

    print(
        f"✅ Created {votes_created} simulated votes from {sum(len(p['users']) for p in user_personas.values())} users"
    )
    return votes_created


async def main():
    """Main seeding function"""
    print("🚀 Starting Truce demo seeding process...\n")

    # Wait a moment for the API to be ready
    print("⏳ Waiting for API to be ready...")
    await asyncio.sleep(2)

    # Test API connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE}/")
            if response.status_code != 200:
                print("❌ API not ready, exiting...")
                return
            print("✅ API is ready")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return

    # Seed the main claim
    claim = await seed_canadian_crime_claim()
    if not claim:
        print("❌ Failed to seed claim")
        return

    print()

    # Seed consensus statements
    statements = await seed_consensus_statements()

    print()

    # Simulate votes on the statements
    if statements:
        votes_count = await simulate_votes_on_statements(statements)
        print(f"📊 Generated {votes_count} votes to demonstrate clustering")

    print()
    print("🎉 Seeding completed successfully!")
    print()
    print("Demo URLs:")
    print(
        f"  Claim Card: http://localhost:3000/claim/violent-crime-in-canada-is-rising"
    )
    print(f"  Consensus Board: http://localhost:3000/consensus/canada-crime")
    print(f"  API: http://localhost:8000/claims/violent-crime-in-canada-is-rising")
    print(f"  Consensus Summary: http://localhost:8000/consensus/canada-crime/summary")


if __name__ == "__main__":
    asyncio.run(main())
