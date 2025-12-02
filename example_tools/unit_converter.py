def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert between different units of measurement.

    Args:
        value: The numeric value to convert
        from_unit: The unit to convert from
        to_unit: The unit to convert to

    Returns:
        The converted value as a formatted string

    Supported conversions:
    - Temperature: celsius, fahrenheit, kelvin
    - Length: meters, feet, inches, centimeters, kilometers, miles
    - Weight: kg, pounds, grams, ounces

    Examples:
        convert_units(25, "celsius", "fahrenheit") -> "25°C = 77.0°F"
        convert_units(100, "meters", "feet") -> "100 meters = 328.08 feet"
        convert_units(5, "kg", "pounds") -> "5 kg = 11.02 pounds"
    """
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

        # Length conversions (to meters first, then to target)
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

        # Weight conversions (to kg first, then to target)
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