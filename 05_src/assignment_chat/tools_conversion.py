"""A deterministic third service exposed through function calling."""

from langchain.tools import tool


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert Celsius/Fahrenheit or kilometres/miles."""
    source, target = from_unit.lower(), to_unit.lower()
    if (source, target) == ("celsius", "fahrenheit"):
        result = value * 9 / 5 + 32
    elif (source, target) == ("fahrenheit", "celsius"):
        result = (value - 32) * 5 / 9
    elif (source, target) == ("kilometres", "miles"):
        result = value * 0.621371
    elif (source, target) == ("miles", "kilometres"):
        result = value / 0.621371
    elif source == target and source in {"celsius", "fahrenheit", "kilometres", "miles"}:
        result = value
    else:
        return "Supported conversions are Celsius/Fahrenheit and kilometres/miles."
    return f"{value:g} {from_unit} is {result:.2f} {to_unit}."
