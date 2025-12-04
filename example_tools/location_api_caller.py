"""
Tool to get the current location from the mock API.
This tool calls the mock API's location endpoint and returns location data.
"""


def get_current_location() -> str:
    """
    Get the current location from the location API service.
    
    This tool calls the location API endpoint and returns location information
    including city, country, coordinates, and timezone.
    
    Returns:
        Location information as a string
        
    Examples:
        get_current_location() -> "Ho Chi Minh City, Vietnam (10.8231, 106.6297)"
    """
    
    # Mock API URL (hardcoded for security)
    mock_api_url = "http://mock-api:8080"
    
    # Build headers to forward
    headers_to_forward = {
        "Content-Type": "application/json",
    }
    
    # Get headers from request context
    try:
        request_headers = get_request_headers()
    except NameError:
        request_headers = {}
    
    # Forward specific headers from the original request
    for header_name in ["x-user-id", "x-request-id", "authorization"]:
        if header_name in request_headers:
            headers_to_forward[header_name] = request_headers[header_name]
    
    try:
        # Make the request to mock API (requests is available in safe context)
        response = requests.get(
            f"{mock_api_url}/location",
            headers=headers_to_forward,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract location data
        location = result.get("location", {})
        city = location.get("city", "Unknown")
        country = location.get("country", "Unknown")
        lat = location.get("lat", 0)
        lon = location.get("lon", 0)
        timezone = location.get("timezone", "Unknown")
        
        return f"{city}, {country} (Lat: {lat}, Lon: {lon}, Timezone: {timezone})"
        
    except Exception as e:
        return f"Error calling location API: {str(e)}"
