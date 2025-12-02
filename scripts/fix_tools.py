#!/usr/bin/env python3
"""
Script to fix tools that are missing the main function required for testing.
"""

import os
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, '/app/src')

from server.server.config import get_tool_store

def fix_calculator():
    """Fix the calculator tool"""
    calculator_code = '''
def calculate(expression: str) -> str:
    """
    Perform basic mathematical calculations.

    Args:
        expression: A simple mathematical expression (e.g., "2 + 3", "10 * 5", "100 / 4")

    Returns:
        The result of the calculation as a string

    Supported operations: +, -, *, /, **
    Examples:
        calculate("2 + 3") -> "5"
        calculate("10 * 5") -> "50"
        calculate("100 / 4") -> "25.0"
        calculate("2 ** 3") -> "8"
    """
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

def main(args):
    """Main function for calculator tool."""
    expression = args.get('expression', '')
    return calculate(expression)
'''
    return calculator_code

def fix_greet_user():
    """Fix the greet_user tool"""
    greet_code = '''
def main(args):
    """Main function for greet_user tool."""
    name = args.get('name', 'User')
    return f"Hello, {name}! Welcome to our service."
'''
    return greet_code

def fix_random_tools():
    """Fix the random_tools"""
    random_code = '''
def roll_dice(sides: int = 6, count: int = 1) -> str:
    """
    Roll dice and return the results.
    """
    import random
    try:
        if sides < 2:
            return "Error: Dice must have at least 2 sides."
        if count < 1:
            return "Error: Must roll at least 1 die."
        if count > 100:
            return "Error: Cannot roll more than 100 dice at once."
        if sides > 1000:
            return "Error: Dice cannot have more than 1000 sides."

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        rolls_str = ", ".join(str(r) for r in rolls)
        result = f"Rolled {count}d{sides}: [{rolls_str}] = {total}"

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

def generate_random_number(min_val: int = 1, max_val: int = 100) -> str:
    """
    Generate a random number within a specified range.
    """
    import random
    try:
        if min_val >= max_val:
            return "Error: Minimum value must be less than maximum value."
        result = random.randint(min_val, max_val)
        return f"Random number ({min_val}-{max_val}): {result}"
    except Exception as e:
        return f"Error: {str(e)}. Please check your parameters."

def flip_coin(count: int = 1) -> str:
    """
    Flip coins and return the results.
    """
    import random
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

def main(args):
    """Main function for random_tools - supports multiple operations."""
    operation = args.get('operation', 'roll_dice')

    if operation == 'roll_dice':
        sides = int(args.get('sides', 6))
        count = int(args.get('count', 1))
        return roll_dice(sides, count)
    elif operation == 'random_number':
        min_val = int(args.get('min_val', 1))
        max_val = int(args.get('max_val', 100))
        return generate_random_number(min_val, max_val)
    elif operation == 'flip_coin':
        count = int(args.get('count', 1))
        return flip_coin(count)
    else:
        return f"Unknown operation: {operation}. Supported: roll_dice, random_number, flip_coin"
'''
    return random_code

def fix_text_analyzer():
    """Fix the text_analyzer tool"""
    text_analyzer_code = '''
def main(args):
    """Main function for text_analyzer tool."""
    text = args.get('text', '')
    
    if not text or not text.strip():
        return "Error: Please provide some text to analyze."

    cleaned_text = text.strip()
    char_count = len(cleaned_text)
    char_no_spaces = len(cleaned_text.replace(" ", ""))
    words = cleaned_text.split()
    word_count = len(words)

    sentences = cleaned_text.replace('!', '.').replace('?', '.').split('.')
    sentence_count = len([s for s in sentences if s.strip()])

    avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0

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
    return text_analyzer_code

def fix_unit_converter():
    """Fix the unit_converter tool"""
    unit_converter_code = '''
def main(args):
    """Main function for unit_converter tool."""
    value = float(args.get('value', 0))
    from_unit = args.get('from_unit', '')
    to_unit = args.get('to_unit', '')
    
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
    return unit_converter_code

def fix_weather():
    """Fix the weather tool"""
    weather_code = '''
def main(args):
    """Main function for weather tool."""
    city = args.get('city', '')
    
    weather_data = {
        "new york": {"temp": 72, "unit": "F", "condition": "Sunny", "humidity": 45},
        "london": {"temp": 15, "unit": "C", "condition": "Cloudy", "humidity": 70},
        "tokyo": {"temp": 25, "unit": "C", "condition": "Rainy", "humidity": 80},
        "paris": {"temp": 18, "unit": "C", "condition": "Partly Cloudy", "humidity": 55},
        "sydney": {"temp": 22, "unit": "C", "condition": "Clear", "humidity": 60},
    }

    city_lower = city.lower().strip()

    if city_lower in weather_data:
        data = weather_data[city_lower]
        return f"Weather in {city.title()}: {data['temp']}°{data['unit']}, {data['condition']}, Humidity: {data['humidity']}%" 
    else:
        import random
        temp = random.randint(10, 30)
        conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear"]
        condition = random.choice(conditions)
        humidity = random.randint(40, 90)
        return f"Weather in {city.title()}: {temp}°C, {condition}, Humidity: {humidity}% (Note: This is simulated data)"
'''
    return weather_code

def main():
    """Main script to fix all tools missing main functions"""
    print("Starting tool fixes...")

    # Tools to fix with their IDs
    tools_to_fix = {
        '7f510146': ('calculator', fix_calculator),
        '754e4008': ('greet_user', fix_greet_user),
        '864c61a0': ('random_tools', fix_random_tools),
        '49d11b52': ('text_analyzer', fix_text_analyzer),
        '6905e94f': ('unit_converter', fix_unit_converter),
        '36a74d1a': ('weather', fix_weather),
    }

    store = get_tool_store()

    for tool_id, (tool_name, fix_func) in tools_to_fix.items():
        try:
            tool = store.get_tool(tool_id)
            if not tool:
                print(f"⚠ Tool {tool_id} ({tool_name}) not found")
                continue

            if tool.is_builtin:
                print(f"✓ {tool_name} is builtin, skipping")
                continue

            # Check if it already has main function
            # if 'def main(' in tool.function_code:
            #     print(f"✓ {tool_name} already has main function")
            #     continue

            # Apply the fix (always update to ensure proper structure)
            new_code = fix_func()
            store.update_tool(tool_id=tool_id, function_code=new_code)
            print(f"✓ Fixed {tool_name}")

        except Exception as e:
            print(f"✗ Error fixing {tool_name}: {e}")

    print("All tools fixed!")

if __name__ == "__main__":
    main()