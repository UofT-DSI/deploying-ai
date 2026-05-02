from langchain.tools import tool
from utils.logger import get_logger

_logs = get_logger(__name__)

@tool
def calculate(operation: str, a: float, b: float) -> str:
    """Performs basic math operations. Use operation='add', 'subtract', or 'multiply' with two numbers a and b."""
    if operation == "add":
        return f"The sum of {a} and {b} is {a + b}"
    elif operation == "subtract":
        return f"{a} minus {b} equals {a - b}"
    elif operation == "multiply":
        return f"{a} times {b} is {a * b}"
    else:
        return "I only support add, subtract, or multiply operations!"
