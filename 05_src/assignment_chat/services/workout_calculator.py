
from langchain.tools import tool


@tool
def calculate_workout_volume(
    sets: int,
    reps: int,
    weight: float
) -> str:
    """
    Calculate total training volume using sets, repetitions,
    and weight in kilograms.
    """

    if sets <= 0 or reps <= 0 or weight < 0:
        return "Please provide valid positive sets and reps, and non-negative weight."

    volume = sets * reps * weight

    return (
        f"Workout volume: {volume} kg\n"
        f"Calculation: {sets} sets × {reps} reps × {weight} kg"
    )
