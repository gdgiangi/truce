"""Test StatCan WDS API implementation"""

import asyncio
import os
from datetime import datetime

from truce_adjudicator.statcan.fetch_csi import StatCanWDSClient, fetch_crime_severity_data
from truce_adjudicator.statcan.utils import cansim_to_pid, get_table_url, parse_wds_response


async def test_wds_client():
    """Test the StatCan WDS API client with real endpoints"""
    
    print("🧪 Testing StatCan WDS API Client")
    print("=" * 50)
    
    client = StatCanWDSClient()
    
    # Test CANSIM to PID conversion
    print("\n1. Testing CANSIM to PID conversion:")
    test_cansim = "35-10-0026-01"
    pid = cansim_to_pid(test_cansim)
    print(f"   CANSIM {test_cansim} -> PID {pid}")
    if pid:
        print(f"   Table URL: {get_table_url(pid)}")
    else:
        print("   ❌ Failed to convert CANSIM to PID")
    
    # Test basic API connectivity
    print("\n2. Testing API connectivity:")
    try:
        # Test a simple endpoint that should work
        print("   Testing getCodeSets endpoint...")
        codesets = await client.get_codesets()
        if codesets:
            print("   ✅ Successfully connected to StatCan WDS API")
            print(f"   Available code sets: {list(codesets.keys())}")
        else:
            print("   ❌ Failed to retrieve codesets")
            
    except Exception as e:
        print(f"   ❌ API connection failed: {e}")
    
    # Test metadata retrieval
    print("\n3. Testing metadata retrieval:")
    try:
        if pid:
            print(f"   Fetching metadata for PID {pid}...")
            metadata = await client.get_cube_metadata(pid)
            
            parsed = parse_wds_response(metadata)
            if parsed['status'] == 'SUCCESS':
                cube_info = parsed['data']
                print("   ✅ Successfully retrieved cube metadata")
                print(f"   Title (EN): {cube_info.get('cubeTitleEn', 'N/A')}")
                print(f"   Start Date: {cube_info.get('cubeStartDate', 'N/A')}")
                print(f"   End Date: {cube_info.get('cubeEndDate', 'N/A')}")
                print(f"   Number of Series: {cube_info.get('nbSeriesCube', 'N/A')}")
            else:
                print(f"   ❌ Failed to retrieve metadata: {parsed.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"   ❌ Metadata retrieval failed: {e}")
    
    # Test CSV download URL
    print("\n4. Testing CSV download URL:")
    try:
        if pid:
            print(f"   Getting CSV download URL for PID {pid}...")
            csv_url = await client.get_full_table_download_csv(pid, "en")
            if csv_url:
                print("   ✅ Successfully retrieved CSV download URL")
                print(f"   URL: {csv_url}")
            else:
                print("   ❌ Failed to retrieve CSV download URL")
                
    except Exception as e:
        print(f"   ❌ CSV URL retrieval failed: {e}")
    
    # Test changed series list
    print("\n5. Testing changed series list:")
    try:
        print("   Getting today's changed series...")
        changed_series = await client.get_changed_series_list()
        if changed_series:
            print(f"   ✅ Successfully retrieved changed series list")
            print(f"   Number of changed series today: {len(changed_series)}")
            if len(changed_series) > 0:
                print(f"   Example series: Vector {changed_series[0].get('vectorId', 'N/A')}")
        else:
            print("   ⚠️  No changed series today (or endpoint not working)")
            
    except Exception as e:
        print(f"   ❌ Changed series retrieval failed: {e}")


async def test_crime_data_fetch():
    """Test the complete crime severity data fetching process"""
    
    print("\n🔍 Testing Crime Severity Data Fetching")
    print("=" * 50)
    
    try:
        evidence_list = await fetch_crime_severity_data()
        
        print(f"✅ Successfully fetched {len(evidence_list)} evidence items")
        
        for i, evidence in enumerate(evidence_list, 1):
            print(f"\n{i}. Evidence Item:")
            print(f"   Publisher: {evidence.publisher}")
            print(f"   URL: {evidence.url}")
            print(f"   Published: {evidence.published_at}")
            print(f"   Snippet: {evidence.snippet[:100]}...")
            print(f"   Provenance: {evidence.provenance}")
            
    except Exception as e:
        print(f"❌ Crime data fetching failed: {e}")


async def main():
    """Run all tests"""
    print("🏁 Starting StatCan WDS API Tests")
    print("=" * 60)
    
    # Check environment
    base_url = os.getenv("STATCAN_WDS_BASE")
    print(f"📍 Base URL: {base_url}")
    
    # Run tests
    await test_wds_client()
    await test_crime_data_fetch()
    
    print("\n" + "=" * 60)
    print("🏁 Tests completed")


if __name__ == "__main__":
    asyncio.run(main())
