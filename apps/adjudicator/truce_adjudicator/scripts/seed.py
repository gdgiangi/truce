#!/usr/bin/env python3
"""Seed script to create the Canadian violent crime demo"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

# Change to the correct directory for imports
os.chdir(str(current_dir.parent))

from truce_adjudicator.models import Claim, ConsensusStatement
from truce_adjudicator.main import claims_db, statements_db
from truce_adjudicator.statcan.fetch_csi import fetch_crime_severity_data
from truce_adjudicator.panel.run_panel import create_mock_assessments


async def seed_canadian_crime_claim():
    """Create the Canadian violent crime claim with evidence and assessments"""
    
    print("🌱 Seeding Canadian violent crime claim...")
    
    # Create the main claim
    claim = Claim(
        text="Violent crime in Canada is rising.",
        topic="canada-crime",
        entities=["Q16"]  # Canada on Wikidata
    )
    
    # Fetch Statistics Canada evidence
    try:
        print("📊 Fetching StatCan crime severity data...")
        evidence_list = await fetch_crime_severity_data()
        claim.evidence.extend(evidence_list)
        print(f"✅ Added {len(evidence_list)} evidence items")
    except Exception as e:
        print(f"❌ Failed to fetch StatCan data: {e}")
        return None
    
    # Create mock model assessments
    try:
        print("🤖 Creating model assessments...")
        assessments = await create_mock_assessments(claim)
        claim.model_assessments.extend(assessments)
        print(f"✅ Added {len(assessments)} model assessments")
    except Exception as e:
        print(f"❌ Failed to create assessments: {e}")
    
    # Store claim with slug
    claim_slug = "violent-crime-canada"
    claims_db[claim_slug] = claim
    
    print(f"✅ Created claim: {claim.text}")
    print(f"   Slug: {claim_slug}")
    print(f"   Evidence: {len(claim.evidence)} items")
    print(f"   Assessments: {len(claim.model_assessments)} models")
    
    return claim


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
        "Transparency in crime data helps inform public understanding"
    ]
    
    statements = []
    for statement_text in statements_data:
        statement = ConsensusStatement(
            text=statement_text,
            topic=topic
        )
        statements.append(statement)
    
    # Store statements
    statements_db[topic] = statements
    
    print(f"✅ Created {len(statements)} consensus statements for topic: {topic}")
    
    return statements


async def main():
    """Main seeding function"""
    print("🚀 Starting Truce demo seeding process...\n")
    
    # Seed the main claim
    claim = await seed_canadian_crime_claim()
    if not claim:
        print("❌ Failed to seed claim")
        return
    
    print()
    
    # Seed consensus statements  
    statements = await seed_consensus_statements()
    
    print()
    print("🎉 Seeding completed successfully!")
    print()
    print("Demo URLs:")
    print(f"  Claim Card: http://localhost:3000/claim/violent-crime-canada")
    print(f"  Consensus Board: http://localhost:3000/consensus/canada-crime")
    print(f"  API: http://localhost:8000/claims/violent-crime-canada")


if __name__ == "__main__":
    asyncio.run(main())
