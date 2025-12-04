"""Mock API Service that prints request headers for testing header propagation."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock API Service", description="Mock API to test header propagation")


@app.get("/datetime")
async def get_datetime(request: Request):
    """
    Simple datetime API endpoint that returns current datetime and received headers.
    This is a simple endpoint for testing header propagation.
    """
    from datetime import datetime
    
    headers_dict = dict(request.headers)
    
    # Log headers with clear formatting
    logger.info("=" * 60)
    logger.info(f"[{datetime.now().isoformat()}] Datetime API Request")
    logger.info("-" * 40)
    logger.info("HEADERS RECEIVED:")
    for key, value in headers_dict.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)
    
    current_time = datetime.now().isoformat()
    
    return JSONResponse(content={
        "datetime": current_time,
        # "message": "Current datetime retrieved successfully",
        # "x_user_id": headers_dict.get("x-user-id", "NOT PROVIDED"),
        # "headers_received": headers_dict,
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "mock-api"}


@app.get("/location")
async def get_location(request: Request):
    """
    Get current location API endpoint.
    Returns a mock location based on user-id header or default location.
    This endpoint demonstrates header propagation for location services.
    """
    headers_dict = dict(request.headers)
    
    # Log headers with clear formatting
    logger.info("=" * 60)
    logger.info(f"[{datetime.now().isoformat()}] Location API Request")
    logger.info("-" * 40)
    logger.info("HEADERS RECEIVED:")
    for key, value in headers_dict.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)
    
    # Mock location data based on user-id or default
    user_id = headers_dict.get("x-user-id", "anonymous")
    
    # Different mock locations based on user
    locations = {
        "user-us": {"city": "New York", "country": "USA", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
        "user-uk": {"city": "London", "country": "UK", "lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London"},
        "user-jp": {"city": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
        "user-vn": {"city": "Ho Chi Minh City", "country": "Vietnam", "lat": 10.8231, "lon": 106.6297, "timezone": "Asia/Ho_Chi_Minh"},
    }
    
    # Default location (Vietnam)
    location = locations.get(user_id, {
        "city": "Ho Chi Minh City",
        "country": "Vietnam", 
        "lat": 10.8231,
        "lon": 106.6297,
        "timezone": "Asia/Ho_Chi_Minh"
    })
    
    return JSONResponse(content={
        "location": location,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    })


@app.api_route("/echo", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def echo_headers(request: Request):
    """
    Echo all request headers back in the response.
    This endpoint logs and returns all headers for verification.
    """
    headers_dict = dict(request.headers)
    
    # Log headers with clear formatting
    logger.info("=" * 60)
    logger.info(f"[{datetime.now().isoformat()}] Request received: {request.method} {request.url.path}")
    logger.info("-" * 40)
    logger.info("HEADERS RECEIVED:")
    for key, value in headers_dict.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)
    
    # Get request body if present
    body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                body = body_bytes.decode("utf-8")
    except Exception:
        pass
    
    # Build response with header details
    response_data = {
        "message": "Headers received successfully",
        "method": request.method,
        "path": str(request.url.path),
        "timestamp": datetime.now().isoformat(),
        "headers": headers_dict,
        "body": body,
        "important_headers": {
            "x-user-id": headers_dict.get("x-user-id"),
            "x-request-id": headers_dict.get("x-request-id"),
            "authorization": headers_dict.get("authorization"),
            "content-type": headers_dict.get("content-type"),
        }
    }
    
    return JSONResponse(content=response_data)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(request: Request, path: str):
    """
    Catch-all endpoint for any /api/* path.
    Logs all headers and returns them in response.
    """
    headers_dict = dict(request.headers)
    
    # Log headers with clear formatting
    logger.info("=" * 60)
    logger.info(f"[{datetime.now().isoformat()}] API Request: {request.method} /api/{path}")
    logger.info("-" * 40)
    logger.info("HEADERS RECEIVED:")
    for key, value in headers_dict.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)
    
    # Get request body if present
    body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                body = body_bytes.decode("utf-8")
    except Exception:
        pass
    
    return JSONResponse(content={
        "message": f"Mock API response for /api/{path}",
        "method": request.method,
        "path": f"/api/{path}",
        "timestamp": datetime.now().isoformat(),
        "headers_received": headers_dict,
        "body_received": body,
        "x_user_id": headers_dict.get("x-user-id", "NOT PROVIDED"),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
