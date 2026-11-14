
import os
import requests
from dotenv import load_dotenv
from langchain.tools import tool

from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2]
load_dotenv(os.path.join(SRC_DIR, ".secrets"))


@tool
def get_food_nutrition(product_name: str) -> str:
    """
    Search USDA FoodData Central and return nutrition
    information per 100 grams.
    """

    if not product_name.strip():
        return "Please provide a food product name."

    api_key = os.getenv("USDA_API_KEY")

    if not api_key:
        return "The food information service is not configured."

    url = "https://api.nal.usda.gov/fdc/v1/foods/search"

    try:
        response = requests.post(
            url,
            params={"api_key": api_key},
            json={
                "query": product_name,
                "pageSize": 20,
                "dataType": ["Foundation", "SR Legacy"]
            },
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        foods = data.get("foods", [])

        search_words = set(product_name.lower().split())

        for food in foods:
            description = food.get("description", "")

            description_words = set(
                description.lower().replace(",", "").split()
            )

            if not search_words.issubset(description_words):
                continue

            nutrients = food.get("foodNutrients", [])

            nutrition = {}

            for nutrient in nutrients:
                name = nutrient.get("nutrientName", "").lower()

                if name.startswith("energy"):
                    nutrition["calories"] = nutrient.get("value")

                elif name == "protein":
                    nutrition["protein"] = nutrient.get("value")

                elif name == "carbohydrate, by difference":
                    nutrition["carbs"] = nutrient.get("value")

                elif name == "total lipid (fat)":
                    nutrition["fat"] = nutrient.get("value")

            if not nutrition:
                continue

            return f"""
Food: {description}

Nutrition per 100g:
- Calories: {nutrition.get('calories', 'Not available')} kcal
- Protein: {nutrition.get('protein', 'Not available')} g
- Carbohydrates: {nutrition.get('carbs', 'Not available')} g
- Fat: {nutrition.get('fat', 'Not available')} g

Source: USDA FoodData Central
"""

        return (
            f"No suitable USDA food result was found "
            f"for '{product_name}'."
        )

    except requests.RequestException:
        return "The USDA food information service is temporarily unavailable."

    except ValueError:
        return "The USDA service returned invalid data."
