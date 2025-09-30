"""StatCan WDS API utilities and helpers"""

import re
from typing import Any, Dict, Optional


def cansim_to_pid(cansim_table: str) -> Optional[int]:
    """Convert CANSIM table number to Product ID (PID)

    Args:
        cansim_table: CANSIM table format (e.g., "35-10-0026-01")

    Returns:
        PID as integer (e.g., 35100026) or None if invalid format
    """
    # Remove hyphens and convert to standard format
    clean_table = cansim_table.replace("-", "")

    # CANSIM format: XX-YY-ZZZZ-VV -> PID format: XXYYZZZZ
    # where XX=subject, YY=product type, ZZZZ=sequential, VV=view (optional)
    match = re.match(r"^(\d{2})(\d{2})(\d{4})(\d{2})?$", clean_table)

    if match:
        subject = match.group(1)  # First 2 digits
        product_type = match.group(2)  # Next 2 digits
        sequential = match.group(3)  # Next 4 digits
        # View (last 2 digits) is optional and not included in base PID

        pid_str = f"{subject}{product_type}{sequential}"
        try:
            return int(pid_str)
        except ValueError:
            return None

    return None


def format_pid(pid: int) -> str:
    """Format PID as 8-digit string with leading zeros if needed"""
    return f"{pid:08d}"


def get_table_url(pid: int) -> str:
    """Get the Statistics Canada table URL for a given PID"""
    return f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={format_pid(pid)}"


def parse_wds_response(response: Any) -> Dict[str, Any]:
    """Parse WDS API response and extract data/status

    Args:
        response: Raw response from WDS API

    Returns:
        Dict with 'status', 'data', and 'error' keys
    """
    result = {"status": "UNKNOWN", "data": None, "error": None}

    try:
        if isinstance(response, dict):
            result["status"] = response.get("status", "UNKNOWN")
            result["data"] = response.get("object")

        elif isinstance(response, list):
            # Some endpoints return arrays directly
            if len(response) > 0:
                first_item = response[0]
                if isinstance(first_item, dict):
                    result["status"] = first_item.get("status", "SUCCESS")
                    result["data"] = first_item.get("object", response)
                else:
                    result["status"] = "SUCCESS"
                    result["data"] = response
            else:
                result["status"] = "SUCCESS"
                result["data"] = []
        else:
            result["status"] = "SUCCESS"
            result["data"] = response

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


# Common Crime Severity Index mappings
CRIME_SEVERITY_MAPPINGS = {
    "35-10-0026-01": 35100026,  # Crime severity index and weighted clearance rates
    "35-10-0027-01": 35100027,  # Crime severity index by type of violation
}

# Known vector IDs for common crime statistics (these would need to be looked up)
CRIME_VECTORS = {
    "canada_total_crime_severity": None,  # Would need to look this up via API
    "canada_violent_crime_severity": None,  # Would need to look this up via API
    "canada_nonviolent_crime_severity": None,  # Would need to look this up via API
}

# Frequency codes from WDS API documentation
FREQUENCY_CODES = {
    1: "Daily",
    2: "Weekly",
    3: "Bi-weekly",
    4: "Semi-monthly",
    5: "Monthly",
    6: "Bi-monthly",
    7: "Quarterly",
    8: "Semi-annual",
    9: "Annual",
    10: "Irregular",
    11: "Occasional",
    12: "Annual, fiscal year",
    13: "Annual, ending March 31",
}

# Status codes from WDS API documentation
STATUS_CODES = {0: "Published", 1: "Preliminary", 2: "Revised", 3: "Terminated"}

# Symbol codes from WDS API documentation
SYMBOL_CODES = {
    0: "No symbol",
    1: "..",  # not available for any reference period
    2: "...",  # not available for a specific reference period
    3: "x",  # suppressed to meet the confidentiality requirements
    4: "F",  # forecast
    5: "A",  # actual
    6: "p",  # preliminary
    7: "r",  # revised
    8: "e",  # estimated
}
