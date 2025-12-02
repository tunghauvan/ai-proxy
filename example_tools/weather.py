def get_weather(city: str) -> str:
    """
    Get weather information for a city (mock data for demonstration).

    Args:
        city: Name of the city to get weather for

    Returns:
        Weather information as a formatted string

    Examples:
        get_weather("New York") -> "Weather in New York: 72°F, Sunny, Humidity: 45%"
        get_weather("London") -> "Weather in London: 15°C, Cloudy, Humidity: 70%"
    """
    # Mock weather data for demonstration
    weather_data = {
        "new york": {"temp": 72, "unit": "F", "condition": "Sunny", "humidity": 45},
        "london": {"temp": 15, "unit": "C", "condition": "Cloudy", "humidity": 70},
        "tokyo": {"temp": 25, "unit": "C", "condition": "Rainy", "humidity": 80},
        "paris": {"temp": 18, "unit": "C", "condition": "Partly Cloudy", "humidity": 55},
        "sydney": {"temp": 22, "unit": "C", "condition": "Clear", "humidity": 60},
    }

    # Normalize city name
    city_lower = city.lower().strip()

    if city_lower in weather_data:
        data = weather_data[city_lower]
        return f"Weather in {city.title()}: {data['temp']}°{data['unit']}, {data['condition']}, Humidity: {data['humidity']}%"
    else:
        # Return mock data for unknown cities
        import random
        temp = random.randint(10, 30)
        conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear"]
        condition = random.choice(conditions)
        humidity = random.randint(40, 90)

        return f"Weather in {city.title()}: {temp}°C, {condition}, Humidity: {humidity}% (Note: This is simulated data)"