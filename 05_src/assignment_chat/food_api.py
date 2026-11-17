
import json
from urllib.parse import quote
from urllib.request import Request, urlopen


def search_food_protein(food_name):
    """Retrieve protein information from Open Food Facts."""

    query = quote(food_name)
    url = (
        "https://world.openfoodfacts.org/cgi/search.pl"
        f"?search_terms={query}&search_simple=1"
        "&action=process&json=1&page_size=5"
    )

    request = Request(
        url,
        headers={"User-Agent": "ProtinGPT/1.0 (educational project)"}
    )

    try:
        with urlopen(request, timeout=15) as response:
            data = json.load(response)

        products = data.get("products", [])

        for product in products:
            protein = product.get("nutriments", {}).get("proteins_100g")

            if protein is not None:
                name = product.get("product_name") or food_name
                brand = product.get("brands", "Unknown brand")

                return (
                    f"Food: {name}\n"
                    f"Brand: {brand}\n"
                    f"Protein: {protein} grams per 100 grams\n"
                    "Source: Open Food Facts\n"
                    "Note: These are product-label values."
                )

        return f"No protein information was found for '{food_name}'."

    except Exception as error:
        return f"The food database request failed: {type(error).__name__}: {error}"
