import requests
import json
from typing import Dict, Any, Optional, List

def analyze_domain_whois(domain_name: str, api_key: str) -> str:
    """
    Analyzes a domain using the WhoisFreaks API and returns specific details as JSON.

    Extracts domain registration status, key dates, registrar name,
    registrant contact details (name, company, address, email), and domain status.
    Handles cases where properties might be missing in the API response by returning None
    for those fields in the output JSON.

    Args:
        domain_name: The domain name to analyze (e.g., 'google.com', 'whoisfreaks.com').
        api_key: Your WhoisFreaks API key obtained from the billing dashboard.

    Returns:
        A JSON formatted string containing the extracted WHOIS information:
        {
            "domain_registered": "yes" | "no" | None,
            "create_date": "YYYY-MM-DD" | None,
            "update_date": "YYYY-MM-DD" | None,
            "expiry_date": "YYYY-MM-DD" | None,
            "domain_registrar_name": "Registrar Name" | None,
            "registrant_details": {
                "name": "Registrant Name" | None,
                "company": "Registrant Company" | None,
                "address": "Full Address String" | None,
                "email": "registrant@example.com" | None
            },
            "domain_status": ["status1", "status2"] | None
        }
        or a JSON string with an error message if the API request fails or returns an error status.
    """
    api_url = "https://api.whoisfreaks.com/v1.0/whois"
    params = {
        "apiKey": api_key,
        "whois": "live",            # As specified in the documentation for live data
        "domainName": domain_name,
        "format": "json"            # Explicitly request JSON format
    }

    # Timeout in seconds for the request
    request_timeout = 15

    try:
        response = requests.get(api_url, params=params, timeout=request_timeout)

        # Check for HTTP errors (4xx or 5xx)
        # The API uses specific 4xx codes for various issues (invalid key, limits, etc.)
        # and 5xx for server-side problems.
        response.raise_for_status()

        # --- Successful Response (Status Code 200 OK, 206 Partial, 210 Cached) ---
        try:
            data = response.json()

            # Initialize the result dictionary with default None values
            result: Dict[str, Any] = {
                "domain_registered": None,
                "create_date": None,
                "update_date": None,
                "expiry_date": None,
                "domain_registrar_name": None,
                "registrant_details": {
                    "name": None,
                    "company": None,
                    "address": None,
                    "email": None
                },
                "domain_status": None
            }

            # Extract data safely using .get() to handle missing keys
            result["domain_registered"] = data.get("domain_registered")
            result["create_date"] = data.get("create_date")
            result["update_date"] = data.get("update_date")
            result["expiry_date"] = data.get("expiry_date")

            # Safely extract registrar name (nested dictionary)
            # Use an empty dict `{}` as default if 'domain_registrar' key is missing
            registrar_info = data.get("domain_registrar", {})
            result["domain_registrar_name"] = registrar_info.get("registrar_name")

            # Safely extract registrant details (nested dictionary)
            registrant_info = data.get("registrant_contact", {})
            result["registrant_details"]["name"] = registrant_info.get("name")
            result["registrant_details"]["company"] = registrant_info.get("company")
            # Use "email_address" key as shown in the example response
            result["registrant_details"]["email"] = registrant_info.get("email_address")

            # Construct the full address string from available parts, handling missing components
            address_parts: List[Optional[str]] = [
                registrant_info.get("street"),
                registrant_info.get("city"),
                registrant_info.get("state"),
                registrant_info.get("zip_code"),
                registrant_info.get("country_name")
            ]
            # Filter out None or empty string values and join with ", "
            # Use mailing_address if available and specific address parts are missing/redacted
            full_address = ", ".join(filter(None, address_parts))
            if not full_address and registrant_info.get("mailing_address") != "N/A":
                 full_address = registrant_info.get("mailing_address")

            result["registrant_details"]["address"] = full_address if full_address else None


            # Extract domain status (which is expected to be a list)
            result["domain_status"] = data.get("domain_status") # Will be None if key is missing, or the list

            # Return the result as a JSON string with indentation for readability
            return json.dumps(result, indent=4)

        except json.JSONDecodeError:
            # Handle cases where the response body is not valid JSON
            error_result = {
                "error": "Failed to decode JSON response from API.",
                "status_code": response.status_code,
                "response_text": response.text[:500] # Include partial text for debugging
            }
            return json.dumps(error_result, indent=4)
        except Exception as e:
            # Catch any other unexpected errors during data processing
            error_result = {
                "error": f"An unexpected error occurred while processing the API response: {e}",
                "status_code": response.status_code,
            }
            return json.dumps(error_result, indent=4)

    # --- Handle HTTP Errors (4xx, 5xx) ---
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        error_details = None
        # Try to parse the error response body from the API if available
        try:
             # API likely returns JSON errors for 4xx codes
             error_details = response.json()
        except (json.JSONDecodeError, AttributeError):
             # Fallback to raw text if not JSON or response object missing
             error_details = response.text[:500] if response else "No response body available."

        error_result = {
            "error": error_message,
            "status_code": response.status_code if response else "N/A",
            "api_error_details": error_details # Include specific API error if parsed
        }
        return json.dumps(error_result, indent=4)

    # --- Handle other Request Errors (Connection, Timeout, etc.) ---
    except requests.exceptions.RequestException as req_err:
        # Network-level errors or DNS resolution issues
        error_result = {
            "error": f"API request failed: {req_err}"
        }
        return json.dumps(error_result, indent=4)

# Example Usage:
if __name__ == "__main__":
    # IMPORTANT: Replace 'YOUR_API_KEY' with your actual WhoisFreaks API key.
    # Keep your API key secure. Consider using environment variables or a config file
    # instead of hardcoding it, especially in production environments.
    my_api_key = "YOUR_API_KEY"  # <--- REPLACE THIS WITH YOUR ACTUAL KEY

    test_domain = "whoisfreaks.com" # Domain from the example
    # test_domain = "google.com"  # Another example
    # test_domain = "domainthatdoesnotexist12345xyz.com" # Example of a non-existent domain

    if my_api_key == "YOUR_API_KEY":
        print("Please replace 'YOUR_API_KEY' with your actual WhoisFreaks API key in the script.")
    else:
        print(f"Analyzing domain: {test_domain}")
        json_output = analyze_domain_whois(test_domain, my_api_key)
        print("\nAPI Response Analysis:")
        print(json_output)

        # Example with a potentially non-existent domain
        # print("\nAnalyzing potentially non-existent domain:")
        # non_existent_domain = "thisshouldprobablynotexist123789.com"
        # json_output_nonexistent = analyze_domain_whois(non_existent_domain, my_api_key)
        # print(json_output_nonexistent)