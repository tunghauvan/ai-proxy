def roll_dice(sides: int = 6, count: int = 1) -> str:
    """
    Roll dice and return the results.

    Args:
        sides: Number of sides on each die (default: 6)
        count: Number of dice to roll (default: 1)

    Returns:
        Dice roll results as a formatted string

    Examples:
        roll_dice() -> "Rolled 1d6: [4] = 4"
        roll_dice(20, 2) -> "Rolled 2d20: [15, 7] = 22"
        roll_dice(12, 3) -> "Rolled 3d12: [8, 11, 3] = 22"
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
            elif total == count:  # All 1s
                result += " 😞 Epic failure!"

        return result

    except Exception as e:
        return f"Error: {str(e)}. Please check your parameters."


def generate_random_number(min_val: int = 1, max_val: int = 100) -> str:
    """
    Generate a random number within a specified range.

    Args:
        min_val: Minimum value (inclusive, default: 1)
        max_val: Maximum value (inclusive, default: 100)

    Returns:
        Random number as a formatted string

    Examples:
        generate_random_number() -> "Random number (1-100): 42"
        generate_random_number(1, 10) -> "Random number (1-10): 7"
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

    Args:
        count: Number of coins to flip (default: 1)

    Returns:
        Coin flip results as a formatted string

    Examples:
        flip_coin() -> "Flipped 1 coin: Heads"
        flip_coin(3) -> "Flipped 3 coins: Heads, Tails, Heads (2H, 1T)"
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