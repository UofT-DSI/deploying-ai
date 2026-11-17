def calculate_protein(protein_per_100g, serving_grams):
    """Calculate protein content in a food serving."""

    if protein_per_100g < 0 or serving_grams <= 0:
        return "Please provide valid positive values."

    protein_amount = (protein_per_100g * serving_grams) / 100

    return (
        f"A {serving_grams:g} g serving contains "
        f"approximately {protein_amount:.2f} g of protein."
    )
