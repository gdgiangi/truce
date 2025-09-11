#!/usr/bin/env python3
"""Seed script to create the Canadian violent crime demo"""

import asyncio
import sys
import os
import httpx
import json
from pathlib import Path

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
        "entities": ["Q16"]  # Canada on Wikidata
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Create claim
            response = await client.post(f"{API_BASE}/claims", json=claim_data)
            response.raise_for_status()
            claim_response = response.json()
            
            # Calculate the correct slug the same way the API does
            slug = claim_data["text"].lower().replace(" ", "-").replace(".", "")[:50]
            slug = ''.join(c for c in slug if c.isalnum() or c == '-')
            
            print(f"✅ Created claim: {claim_data['text']}")
            print(f"   Slug: {slug}")
            
            # Add Statistics Canada evidence
            try:
                print("📊 Fetching StatCan crime severity data...")
                evidence_request = {
                    "source_type": "statcan", 
                    "params": {}
                }
                
                evidence_response = await client.post(
                    f"{API_BASE}/claims/{slug}/evidence:statcan",
                    json=evidence_request
                )
                if evidence_response.status_code == 200:
                    evidence_result = evidence_response.json()
                    print(f"✅ Added {evidence_result.get('evidence_count', 0)} evidence items via API")
                else:
                    print(f"⚠️  Evidence API call returned {evidence_response.status_code}: {evidence_response.text}")
                
            except Exception as e:
                print(f"❌ Failed to fetch StatCan data: {e}")
            
            # Run model panel
            try:
                print("🤖 Creating model assessments...")
                panel_response = await client.post(
                    f"{API_BASE}/claims/{slug}/panel/run",
                    json={"models": ["gpt-4", "claude-3"]}
                )
                if panel_response.status_code == 200:
                    panel_result = panel_response.json()
                    assessment_count = len(panel_result.get('assessments', []))
                    print(f"✅ Added {assessment_count} model assessments")
                else:
                    print(f"⚠️  Panel API call returned {panel_response.status_code}: {panel_response.text}")
                    
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
        "Transparency in crime data helps inform public understanding"
    ]
    
    created_count = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            for statement_text in statements_data:
                statement_data = {
                    "text": statement_text,
                    "evidence_links": []
                }
                
                response = await client.post(
                    f"{API_BASE}/consensus/{topic}/statements",
                    json=statement_data
                )
                
                if response.status_code == 200:
                    created_count += 1
                else:
                    print(f"⚠️  Failed to create statement: {statement_text[:50]}...")
                    
        except Exception as e:
            print(f"❌ Failed to create consensus statements: {e}")
            return 0
    
    print(f"✅ Created {created_count} consensus statements for topic: {topic}")
    return created_count


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
    statement_count = await seed_consensus_statements()
    
    print()
    print("🎉 Seeding completed successfully!")
    print()
    print("Demo URLs:")
    print(f"  Claim Card: http://localhost:3000/claim/violent-crime-in-canada-is-rising")
    print(f"  Consensus Board: http://localhost:3000/consensus/canada-crime")
    print(f"  API: http://localhost:8000/claims/violent-crime-in-canada-is-rising")


if __name__ == "__main__":
    asyncio.run(main())
