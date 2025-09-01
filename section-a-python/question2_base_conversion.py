"""
Question 2: Base-N String to Base-10 Number

Function to convert a string of arbitrary length, including fractional values,
from any base to base-10 number. Handles edge cases and validates inputs.

Examples:
- ("101.11", "binary") → 5.75
- ("17.4", "octal") → 15.5
- ("1G.F", "hex") → ValueError
- ("123.456", "decimal") → 123.456
"""

import re


def base_n_to_decimal(number_str: str, base_name: str) -> float:
    """
    Convert a string representation of a number in any base to base-10 decimal.
    
    Args:
        number_str (str): String representation of the number (e.g., "101.11", "1A.5F")
        base_name (str): Name of the base system ("binary", "octal", "decimal", "hex")
    
    Returns:
        float: The decimal equivalent of the input number
    
    Raises:
        ValueError: If input is invalid or contains invalid characters for the base
        TypeError: If inputs are not strings
    
    Assumptions:
    - Negative numbers are supported with '-' prefix
    - Empty strings are invalid
    - Base names are case-insensitive
    - Fractional part is optional
    - Leading/trailing whitespace is stripped
    """
    
    # Input validation
    if not isinstance(number_str, str) or not isinstance(base_name, str):
        raise TypeError("Both number_str and base_name must be strings")
    
    # Clean input
    number_str = number_str.strip()
    base_name = base_name.lower().strip()
    
    if not number_str:
        raise ValueError("Number string cannot be empty")
    
    # Base mapping
    base_map = {
        'binary': 2,
        'bin': 2,
        'octal': 8,
        'oct': 8,
        'decimal': 10,
        'dec': 10,
        'hexadecimal': 16,
        'hex': 16
    }
    
    if base_name not in base_map:
        raise ValueError(f"Unsupported base: {base_name}. "
                        f"Supported bases: {list(base_map.keys())}")
    
    base = base_map[base_name]
    
    # Handle negative numbers
    is_negative = number_str.startswith('-')
    if is_negative:
        number_str = number_str[1:]
    
    # Validate format (only digits, letters, and one decimal point allowed)
    if not re.match(r'^[0-9A-Fa-f]*\.?[0-9A-Fa-f]*$', number_str):
        raise ValueError(f"Invalid characters in number string: {number_str}")
    
    # Check for multiple decimal points
    if number_str.count('.') > 1:
        raise ValueError("Number cannot contain multiple decimal points")
    
    # Split into integer and fractional parts
    if '.' in number_str:
        integer_part, fractional_part = number_str.split('.')
    else:
        integer_part = number_str
        fractional_part = ""
    
    # Handle empty parts
    if not integer_part and not fractional_part:
        raise ValueError("Number string cannot be empty or contain only a decimal point")
    
    if not integer_part:
        integer_part = "0"
    
    # Convert integer part
    decimal_value = 0.0
    
    if integer_part:
        try:
            decimal_value += _convert_integer_part(integer_part, base)
        except ValueError as e:
            raise ValueError(f"Invalid integer part '{integer_part}': {e}")
    
    # Convert fractional part
    if fractional_part:
        try:
            decimal_value += _convert_fractional_part(fractional_part, base)
        except ValueError as e:
            raise ValueError(f"Invalid fractional part '{fractional_part}': {e}")
    
    return -decimal_value if is_negative else decimal_value


def _convert_integer_part(integer_str: str, base: int) -> float:
    """Convert the integer part of a number from given base to decimal."""
    decimal_value = 0
    
    for i, digit in enumerate(reversed(integer_str)):
        digit_value = _get_digit_value(digit, base)
        decimal_value += digit_value * (base ** i)
    
    return float(decimal_value)


def _convert_fractional_part(fractional_str: str, base: int) -> float:
    """Convert the fractional part of a number from given base to decimal."""
    decimal_value = 0.0
    
    for i, digit in enumerate(fractional_str):
        digit_value = _get_digit_value(digit, base)
        decimal_value += digit_value * (base ** -(i + 1))
    
    return decimal_value


def _get_digit_value(digit: str, base: int) -> int:
    """
    Get the numeric value of a digit character for the given base.
    
    Args:
        digit (str): Single character representing a digit
        base (int): The base system (2, 8, 10, 16)
    
    Returns:
        int: Numeric value of the digit
    
    Raises:
        ValueError: If digit is invalid for the given base
    """
    digit = digit.upper()
    
    # Handle numeric digits (0-9)
    if digit.isdigit():
        value = int(digit)
    # Handle hexadecimal letters (A-F)
    elif digit.isalpha():
        if digit < 'A' or digit > 'F':
            raise ValueError(f"Invalid digit '{digit}' for any supported base")
        value = ord(digit) - ord('A') + 10
    else:
        raise ValueError(f"Invalid character '{digit}'")
    
    # Validate digit is within base range
    if value >= base:
        base_names = {2: 'binary', 8: 'octal', 10: 'decimal', 16: 'hexadecimal'}
        raise ValueError(f"Digit '{digit}' (value {value}) is invalid for "
                        f"{base_names.get(base, f'base-{base}')} system")
    
    return value


def demonstrate_conversion():
    """Demonstrate the base conversion function with various test cases."""
    
    test_cases = [
        # Format: (input_string, base_name, expected_result, should_raise_error)
        ("101.11", "binary", 5.75, False),
        ("17.4", "octal", 15.5, False),
        ("1G.F", "hex", None, True),  # Invalid hex digit G
        ("123.456", "decimal", 123.456, False),
        ("FF.8", "hex", 255.5, False),
        ("1010", "binary", 10.0, False),
        ("777", "octal", 511.0, False),
        ("-101.1", "binary", -5.5, False),
        ("0.1", "binary", 0.5, False),
        ("ABC", "hex", 2748.0, False),
        ("", "decimal", None, True),  # Empty string
        ("12.34.56", "decimal", None, True),  # Multiple decimal points
        ("18", "octal", None, True),  # Invalid octal digit 8
        ("102", "binary", None, True),  # Invalid binary digit 2
        ("-0", "decimal", 0.0, False),  # Negative zero
        ("0.0", "decimal", 0.0, False),  # Zero with decimal
        ("A.A", "hex", 10.625, False),  # 10 + 10/16
    ]
    
    print("Base-N to Decimal Conversion Demonstration:")
    print("=" * 60)
    
    for i, (input_str, base_name, expected, should_error) in enumerate(test_cases, 1):
        print(f"\nTest {i:2d}: ({input_str!r}, {base_name!r})")
        
        try:
            result = base_n_to_decimal(input_str, base_name)
            if should_error:
                print(f"   ❌ Expected error but got: {result}")
            else:
                if abs(result - expected) < 1e-10:  # Handle floating point precision
                    print(f"   ✅ Result: {result} (Expected: {expected})")
                else:
                    print(f"   ❌ Result: {result} (Expected: {expected})")
        except (ValueError, TypeError) as e:
            if should_error:
                print(f"   ✅ Correctly raised error: {e}")
            else:
                print(f"   ❌ Unexpected error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error type: {type(e).__name__}: {e}")


def performance_test():
    """Test performance with various input sizes."""
    import time
    
    print("\nPerformance Test:")
    print("-" * 30)
    
    # Test with different length numbers
    test_numbers = [
        ("1" * 10, "decimal"),      # 10 digits
        ("1" * 100, "decimal"),     # 100 digits
        ("A" * 10, "hex"),          # 10 hex digits
        ("1" * 50 + "." + "1" * 50, "decimal")  # 100 digits with decimal
    ]
    
    for number_str, base_name in test_numbers:
        start_time = time.time()
        base_n_to_decimal(number_str, base_name)
        end_time = time.time()
        
        print(f"Length {len(number_str):3d} ({base_name:7s}): "
              f"{(end_time - start_time) * 1000:.3f}ms")


if __name__ == "__main__":
    demonstrate_conversion()
    performance_test()