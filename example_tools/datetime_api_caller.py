"""
Simple tool to call the datetime API and demonstrate header propagation.
This tool calls the mock API's datetime endpoint.
"""


def get_current_datetime() -> str:
    """
    Get the current datetime from the mock API service.
    
    This tool calls the mock API's datetime endpoint and returns the current datetime.
    
    Returns:
        Current datetime as a string
        
    Examples:
        get_current_datetime() -> "2025-12-04T15:00:00"
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
            f"{mock_api_url}/datetime",
            headers=headers_to_forward,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Return just the datetime string
        datetime_str = result.get("datetime", "N/A")
        return datetime_str
        
    except Exception as e:
        return f"Error calling datetime API: {str(e)}"