#!/usr/bin/env python3
"""
Script to delete all custom tools and re-import them from example_tools folder with proper main functions.
"""

import os
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, '/app/src')

from server.server.config import get_tool_store


def get_calculator_code():
    """Calculator tool with main function."""
    return '''
def main(**kwargs):
    """
    Perform basic mathematical calculations.
    Args: expression (str)
    """
    expression = kwargs.get('expression', '')
    
    try:
        # Split the expression into parts
        expression = expression.replace(" ", "")

        # Handle power operation first
        if "**" in expression:
            parts = expression.split("**", 1)
            if len(parts) == 2:
                base = float(parts[0])
                exponent = float(parts[1])
                result = base ** exponent
                return str(result)

        # Handle basic operations
        operations = [
            ("*", lambda a, b: a * b),
            ("/", lambda a, b: a / b),
            ("+", lambda a, b: a + b),
            ("-", lambda a, b: a - b),
        ]

        for op_symbol, op_func in operations:
            if op_symbol in expression:
                parts = expression.split(op_symbol, 1)
                if len(parts) == 2:
                    try:
                        a = float(parts[0])
                        b = float(parts[1])
                        result = op_func(a, b)
                        return str(result)
                    except ValueError:
                        pass

        return "Error: Unsupported expression format. Use format like '2 + 3' or '10 * 5'"

    except Exception as e:
        return f"Error: {str(e)}. Please provide a valid mathematical expression."
'''


def get_text_analyzer_code():
    """Text analyzer tool with main function."""
    return '''
def main(**kwargs):
    """
    Analyze text and return statistics.
    Args: text (str)
    """
    text = kwargs.get('text', '')
    
    if not text or not text.strip():
        return "Error: Please provide some text to analyze."

    # Clean the text
    cleaned_text = text.strip()

    # Count characters (including spaces)
    char_count = len(cleaned_text)

    # Count characters without spaces
    char_no_spaces = len(cleaned_text.replace(" ", ""))

    # Count words
    words = cleaned_text.split()
    word_count = len(words)

    # Count sentences
    sentences = cleaned_text.replace('!', '.').replace('?', '.').split('.')
    sentence_count = len([s for s in sentences if s.strip()])

    # Average word length
    avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0

    # Most common words (excluding common stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
    filtered_words = [word.lower() for word in words if word.lower() not in stop_words]
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1

    most_common = max(word_freq.items(), key=lambda x: x[1]) if word_freq else ("N/A", 0)

    result = f"""Text Analysis:
• Characters (with spaces): {char_count}
• Characters (no spaces): {char_no_spaces}
• Words: {word_count}
• Sentences: {sentence_count}
• Average word length: {avg_word_length:.1f}
• Most common word: '{most_common[0]}' (appears {most_common[1]} times)"""

    return result
'''


def get_unit_converter_code():
    """Unit converter tool with main function."""
    return '''
def main(**kwargs):
    """
    Convert between different units of measurement.
    Args: value (float), from_unit (str), to_unit (str)
    """
    value = float(kwargs.get('value', 0))
    from_unit = kwargs.get('from_unit', '')
    to_unit = kwargs.get('to_unit', '')
    
    try:
        # Temperature conversions
        if from_unit.lower() in ['celsius', 'c'] and to_unit.lower() in ['fahrenheit', 'f']:
            result = (value * 9/5) + 32
            return f"{value}°C = {result:.2f}°F"

        elif from_unit.lower() in ['fahrenheit', 'f'] and to_unit.lower() in ['celsius', 'c']:
            result = (value - 32) * 5/9
            return f"{value}°F = {result:.2f}°C"

        elif from_unit.lower() in ['celsius', 'c'] and to_unit.lower() in ['kelvin', 'k']:
            result = value + 273.15
            return f"{value}°C = {result:.2f}°K"

        elif from_unit.lower() in ['kelvin', 'k'] and to_unit.lower() in ['celsius', 'c']:
            result = value - 273.15
            return f"{value}°K = {result:.2f}°C"

        elif from_unit.lower() in ['fahrenheit', 'f'] and to_unit.lower() in ['kelvin', 'k']:
            celsius = (value - 32) * 5/9
            result = celsius + 273.15
            return f"{value}°F = {result:.2f}°K"

        elif from_unit.lower() in ['kelvin', 'k'] and to_unit.lower() in ['fahrenheit', 'f']:
            celsius = value - 273.15
            result = (celsius * 9/5) + 32
            return f"{value}°K = {result:.2f}°F"

        # Length conversions
        length_to_meters = {
            'meters': 1, 'm': 1,
            'feet': 0.3048, 'ft': 0.3048,
            'inches': 0.0254, 'in': 0.0254,
            'centimeters': 0.01, 'cm': 0.01,
            'kilometers': 1000, 'km': 1000,
            'miles': 1609.344, 'mi': 1609.344
        }

        if from_unit.lower() in length_to_meters and to_unit.lower() in length_to_meters:
            meters = value * length_to_meters[from_unit.lower()]
            result = meters / length_to_meters[to_unit.lower()]
            return f"{value} {from_unit} = {result:.2f} {to_unit}"

        # Weight conversions
        weight_to_kg = {
            'kg': 1, 'kilograms': 1,
            'pounds': 0.453592, 'lbs': 0.453592, 'lb': 0.453592,
            'grams': 0.001, 'g': 0.001,
            'ounces': 0.0283495, 'oz': 0.0283495
        }

        if from_unit.lower() in weight_to_kg and to_unit.lower() in weight_to_kg:
            kg = value * weight_to_kg[from_unit.lower()]
            result = kg / weight_to_kg[to_unit.lower()]
            return f"{value} {from_unit} = {result:.2f} {to_unit}"

        return f"Error: Unsupported conversion from {from_unit} to {to_unit}. Supported categories: temperature (celsius/fahrenheit/kelvin), length (meters/feet/inches/centimeters/kilometers/miles), weight (kg/pounds/grams/ounces)"

    except Exception as e:
        return f"Error: {str(e)}. Please check your input values and units."
'''


def get_weather_code():
    """Weather tool with main function."""
    return '''
def main(**kwargs):
    """
    Get weather information for a city (mock data for demonstration).
    Args: city (str)
    """
    city = kwargs.get('city', '')
    
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
'''


def get_location_code():
    """Location tool with main function."""
    return '''
def main(**kwargs):
    """
    Get current location information from API.
    Args: user_id (str, optional) - User identifier for location lookup
    """
    import requests
    
    user_id = kwargs.get('user_id', 'anonymous')
    
    # Mock API URL (hardcoded for security)
    mock_api_url = "http://mock-api:8080"
    
    # Build headers to forward
    headers_to_forward = {
        "Content-Type": "application/json",
        "x-user-id": user_id
    }
    
    try:
        # Make the request to mock API
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
        
        return f"Current location: {city}, {country} (Lat: {lat}, Lon: {lon}, Timezone: {timezone})"
        
    except Exception as e:
        # Fallback to mock data if API fails
        import random
        
        locations = [
            {"city": "Ho Chi Minh City", "country": "Vietnam", "lat": 10.8231, "lon": 106.6297, "timezone": "Asia/Ho_Chi_Minh"},
            {"city": "Hanoi", "country": "Vietnam", "lat": 21.0285, "lon": 105.8542, "timezone": "Asia/Ho_Chi_Minh"},
            {"city": "New York", "country": "USA", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
            {"city": "London", "country": "UK", "lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London"},
            {"city": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
        ]
        
        location = random.choice(locations)
        city = location["city"]
        country = location["country"]
        lat = location["lat"]
        lon = location["lon"]
        timezone = location["timezone"]
        
        return f"Current location (fallback): {city}, {country} (Lat: {lat}, Lon: {lon}, Timezone: {timezone}) - API Error: {str(e)}"
'''


def get_roll_dice_code():
    """Roll dice tool with main function."""
    return '''
def main(**kwargs):
    """
    Roll dice and return the results.
    Args: sides (int, default 6), count (int, default 1)
    """
    import random
    
    sides = int(kwargs.get('sides', 6))
    count = int(kwargs.get('count', 1))
    
    try:
        if sides < 2:
            return "Error: Dice must have at least 2 sides."
        if count < 1:
            return "Error: Must roll at least 1 die."
        if count > 100:
            return "Error: Cannot roll more than 100 dice at once."
        if sides > 1000:
            return "Error: Dice cannot have more than 1000 sides."

        # Roll the dice
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)

        # Format the result
        rolls_str = ", ".join(str(r) for r in rolls)
        result = f"Rolled {count}d{sides}: [{rolls_str}] = {total}"

        # Add some fun commentary for special rolls
        if count == 1:
            if rolls[0] == sides:
                result += " 🎉 Critical success!"
            elif rolls[0] == 1 and sides > 1:
                result += " 😞 Critical failure!"
        elif count > 1:
            max_possible = count * sides
            if total == max_possible:
                result += " 🎉 Perfect roll!"
            elif total == count:
                result += " 😞 Epic failure!"

        return result

    except Exception as e:
        return f"Error: {str(e)}. Please check your parameters."
'''


def get_random_number_code():
    """Random number generator tool with main function."""
    return '''
def main(**kwargs):
    """
    Generate a random number within a specified range.
    Args: min_val (int, default 1), max_val (int, default 100)
    """
    import random
    
    min_val = int(kwargs.get('min_val', 1))
    max_val = int(kwargs.get('max_val', 100))
    
    try:
        if min_val >= max_val:
            return "Error: Minimum value must be less than maximum value."

        result = random.randint(min_val, max_val)
        return f"Random number ({min_val}-{max_val}): {result}"

    except Exception as e:
        return f"Error: {str(e)}. Please check your parameters."
'''


def get_flip_coin_code():
    """Flip coin tool with main function."""
    return '''
def main(**kwargs):
    """
    Flip coins and return the results.
    Args: count (int, default 1)
    """
    import random
    
    count = int(kwargs.get('count', 1))
    
    try:
        if count < 1:
            return "Error: Must flip at least 1 coin."
        if count > 100:
            return "Error: Cannot flip more than 100 coins at once."

        results = []
        heads_count = 0
        tails_count = 0

        for _ in range(count):
            result = random.choice(["Heads", "Tails"])
            results.append(result)
            if result == "Heads":
                heads_count += 1
            else:
                tails_count += 1

        results_str = ", ".join(results)
        summary = f"({heads_count}H, {tails_count}T)"

        return f"Flipped {count} coin{'s' if count > 1 else ''}: {results_str} {summary}"

    except Exception as e:
        return f"Error: {str(e)}. Please check your parameters."
'''


def main():
    """Main script to delete all custom tools and re-import them."""
    print("=" * 60)
    print("RESET AND IMPORT TOOLS SCRIPT")
    print("=" * 60)
    
    store = get_tool_store()
    
    # Step 1: List all existing tools
    print("\n1. Listing existing tools...")
    tools = store.list_tools()
    print(f"   Found {len(tools)} tools in database")
    
    # Step 2: Delete all custom (non-builtin) tools
    print("\n2. Deleting all custom tools...")
    deleted_count = 0
    for tool in tools:
        if not tool.is_builtin:
            try:
                store.delete_tool(tool.id)
                print(f"   ✓ Deleted: {tool.name} (ID: {tool.id})")
                deleted_count += 1
            except Exception as e:
                print(f"   ✗ Error deleting {tool.name}: {e}")
    print(f"   Total deleted: {deleted_count}")
    
    # Step 3: Create new tools with proper main functions
    print("\n3. Creating new tools with proper main functions...")
    
    tools_to_create = [
        {
            "name": "calculator",
            "description": "Perform basic mathematical calculations (+, -, *, /, **)",
            "category": "math",
            "function_code": get_calculator_code(),
            "parameters": [
                {"name": "expression", "type": "string", "description": "Mathematical expression (e.g., '2 + 3', '10 * 5')", "required": True}
            ]
        },
        {
            "name": "text_analyzer",
            "description": "Analyze text and return statistics (characters, words, sentences)",
            "category": "text",
            "function_code": get_text_analyzer_code(),
            "parameters": [
                {"name": "text", "type": "string", "description": "The text to analyze", "required": True}
            ]
        },
        {
            "name": "unit_converter",
            "description": "Convert between units (temperature, length, weight)",
            "category": "conversion",
            "function_code": get_unit_converter_code(),
            "parameters": [
                {"name": "value", "type": "number", "description": "The value to convert", "required": True},
                {"name": "from_unit", "type": "string", "description": "The unit to convert from", "required": True},
                {"name": "to_unit", "type": "string", "description": "The unit to convert to", "required": True}
            ]
        },
        {
            "name": "weather",
            "description": "Get weather information for a city (mock data)",
            "category": "information",
            "function_code": get_weather_code(),
            "parameters": [
                {"name": "city", "type": "string", "description": "Name of the city", "required": True}
            ]
        },
        {
            "name": "location",
            "description": "Get current location information",
            "category": "information",
            "function_code": get_location_code(),
            "parameters": [
                {"name": "user_id", "type": "string", "description": "User identifier for location lookup (optional)", "required": False, "default": "anonymous"}
            ]
        },
        {
            "name": "roll_dice",
            "description": "Roll dice and return the results",
            "category": "random",
            "function_code": get_roll_dice_code(),
            "parameters": [
                {"name": "sides", "type": "number", "description": "Number of sides on each die (default: 6)", "required": False, "default": 6},
                {"name": "count", "type": "number", "description": "Number of dice to roll (default: 1)", "required": False, "default": 1}
            ]
        },
        {
            "name": "random_number",
            "description": "Generate a random number within a range",
            "category": "random",
            "function_code": get_random_number_code(),
            "parameters": [
                {"name": "min_val", "type": "number", "description": "Minimum value (default: 1)", "required": False, "default": 1},
                {"name": "max_val", "type": "number", "description": "Maximum value (default: 100)", "required": False, "default": 100}
            ]
        },
        {
            "name": "flip_coin",
            "description": "Flip coins and return the results",
            "category": "random",
            "function_code": get_flip_coin_code(),
            "parameters": [
                {"name": "count", "type": "number", "description": "Number of coins to flip (default: 1)", "required": False, "default": 1}
            ]
        }
    ]
    
    created_tools = []
    for tool_config in tools_to_create:
        try:
            tool = store.create_tool(
                name=tool_config["name"],
                description=tool_config["description"],
                category=tool_config["category"],
                enabled=True,
                function_code=tool_config["function_code"],
                parameters=tool_config["parameters"]
            )
            print(f"   ✓ Created: {tool.name} (ID: {tool.id})")
            created_tools.append(tool)
        except Exception as e:
            print(f"   ✗ Error creating {tool_config['name']}: {e}")
    
    print(f"\n   Total created: {len(created_tools)}")
    
    # Step 4: Verify all tools
    print("\n4. Verifying tools in database...")
    tools = store.list_tools()
    for tool in tools:
        has_main = 'def main(' in (tool.function_code or '')
        status = '✓' if (tool.is_builtin or has_main) else '✗'
        tool_type = "BUILTIN" if tool.is_builtin else ("HAS MAIN" if has_main else "MISSING MAIN")
        print(f"   {status} {tool.name} (ID: {tool.id}) - {tool_type}")
    
    print("\n" + "=" * 60)
    print("DONE! All tools have been reset and imported.")
    print("=" * 60)
    
    return created_tools


if __name__ == "__main__":
    main()
