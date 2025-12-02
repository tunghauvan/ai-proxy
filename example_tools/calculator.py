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